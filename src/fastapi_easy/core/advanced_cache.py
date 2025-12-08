"""
Advanced Multi-Layer Caching System

This module provides a comprehensive caching solution with:
- L1 (Memory) and L2 (Redis) cache layers
- Intelligent cache warming and invalidation
- Cache performance analytics
- Adaptive cache sizing
- Distributed cache coordination
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import pickle
import time
from abc import ABC, abstractmethod
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level enumeration"""

    L1_MEMORY = "L1"
    L2_REDIS = "L2"
    DISTRIBUTED = "DISTRIBUTED"


@dataclass
class CacheEntry:
    """Cache entry with metadata"""

    value: Any
    ttl: int
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    tags: Set[str] = field(default_factory=set)
    level: CacheLevel = CacheLevel.L1_MEMORY
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)

    @property
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds"""
        return (datetime.now() - self.created_at).total_seconds()

    def touch(self):
        """Update last accessed time"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class CacheStats:
    """Cache performance statistics"""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    errors: int = 0
    total_size_bytes: int = 0
    total_entries: int = 0
    memory_usage_mb: float = 0.0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate"""
        return 100.0 - self.hit_rate


@dataclass
class CacheMetrics:
    """Comprehensive cache metrics"""

    l1_stats: CacheStats = field(default_factory=CacheStats)
    l2_stats: CacheStats = field(default_factory=CacheStats)
    operation_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    tag_usage: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    size_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))


class EvictionPolicy(ABC):
    """Abstract base class for cache eviction policies"""

    @abstractmethod
    def should_evict(
        self, entries: List[CacheEntry], new_entry_size: int, max_size: int
    ) -> Optional[str]:
        """Determine which entry to evict"""
        pass

    @abstractmethod
    def get_victims(self, entries: List[CacheEntry], evict_count: int) -> List[str]:
        """Get list of keys to evict"""
        pass


class LRUEvictionPolicy(EvictionPolicy):
    """Least Recently Used eviction policy"""

    def should_evict(
        self, entries: List[CacheEntry], new_entry_size: int, max_size: int
    ) -> Optional[str]:
        if len(entries) < max_size:
            return None

        # Find least recently used entry
        lru_entry = min(entries, key=lambda e: e.last_accessed)
        return self._get_key_for_entry(lru_entry, entries)

    def get_victims(self, entries: List[CacheEntry], evict_count: int) -> List[str]:
        # Sort by last accessed time
        sorted_entries = sorted(entries, key=lambda e: e.last_accessed)
        return [self._get_key_for_entry(entry, entries) for entry in sorted_entries[:evict_count]]

    def _get_key_for_entry(self, target_entry: CacheEntry, entries: List[CacheEntry]) -> str:
        """Find key for given entry (implementation specific)"""
        # This would be implemented differently based on cache storage
        raise NotImplementedError


class LFUEvictionPolicy(EvictionPolicy):
    """Least Frequently Used eviction policy"""

    def should_evict(
        self, entries: List[CacheEntry], new_entry_size: int, max_size: int
    ) -> Optional[str]:
        if len(entries) < max_size:
            return None

        # Find least frequently used entry
        lfu_entry = min(entries, key=lambda e: (e.access_count, e.last_accessed))
        return self._get_key_for_entry(lfu_entry, entries)

    def get_victims(self, entries: List[CacheEntry], evict_count: int) -> List[str]:
        # Sort by access count, then by last accessed time
        sorted_entries = sorted(entries, key=lambda e: (e.access_count, e.last_accessed))
        return [self._get_key_for_entry(entry, entries) for entry in sorted_entries[:evict_count]]

    def _get_key_for_entry(self, target_entry: CacheEntry, entries: List[CacheEntry]) -> str:
        raise NotImplementedError


class TTLEvictionPolicy(EvictionPolicy):
    """Time-based eviction policy"""

    def should_evict(
        self, entries: List[CacheEntry], new_entry_size: int, max_size: int
    ) -> Optional[str]:
        # Find expired entries first
        now = datetime.now()
        for entry in entries:
            if entry.is_expired:
                return self._get_key_for_entry(entry, entries)

        # If no expired entries, use LRU
        if len(entries) >= max_size:
            lru_entry = min(entries, key=lambda e: e.last_accessed)
            return self._get_key_for_entry(lru_entry, entries)

        return None

    def get_victims(self, entries: List[CacheEntry], evict_count: int) -> List[str]:
        # First, remove expired entries
        now = datetime.now()
        expired = [e for e in entries if e.is_expired]
        victims = [self._get_key_for_entry(entry, entries) for entry in expired[:evict_count]]

        # If need more victims, use LRU
        if len(victims) < evict_count:
            remaining = evict_count - len(victims)
            non_expired = [e for e in entries if not e.is_expired]
            sorted_entries = sorted(non_expired, key=lambda e: e.last_accessed)
            victims.extend(
                [self._get_key_for_entry(entry, entries) for entry in sorted_entries[:remaining]]
            )

        return victims

    def _get_key_for_entry(self, target_entry: CacheEntry, entries: List[CacheEntry]) -> str:
        raise NotImplementedError


class L1MemoryCache:
    """Level 1 in-memory cache with advanced features"""

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,
        eviction_policy: EvictionPolicy = None,
        enable_stats: bool = True,
        enable_compression: bool = False,
    ):
        """
        Initialize L1 memory cache

        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
            eviction_policy: Eviction policy to use
            enable_stats: Enable statistics tracking
            enable_compression: Enable value compression
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats
        self.enable_compression = enable_compression

        # Storage
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._key_to_entry: Dict[str, CacheEntry] = {}

        # Eviction policy
        self.eviction_policy = eviction_policy or LRUEvictionPolicy()

        # Statistics
        self.stats = CacheStats()
        self.metrics = CacheMetrics()

        # Locks
        self._lock = asyncio.Lock()

        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None

        # Start background tasks
        self._start_background_tasks()

    def _start_background_tasks(self):
        """Start background maintenance tasks"""
        self._cleanup_task = asyncio.create_task(self._cleanup_expired())
        self._stats_task = asyncio.create_task(self._update_stats())

    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters"""
        # Sort kwargs for consistent key generation
        sorted_items = sorted(kwargs.items())
        key_str = f"{prefix}:{json.dumps(sorted_items, sort_keys=True, default=str)}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _serialize_value(self, value: Any) -> bytes:
        """Serialize value for storage"""
        try:
            data = pickle.dumps(value)
            if self.enable_compression:
                import gzip

                data = gzip.compress(data)
            return data
        except Exception as e:
            logger.error(f"Value serialization failed: {e}")
            raise

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        try:
            if self.enable_compression:
                import gzip

                data = gzip.decompress(data)
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"Value deserialization failed: {e}")
            raise

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        start_time = time.perf_counter()

        async with self._lock:
            if key not in self._cache:
                self.stats.misses += 1
                self.metrics.operation_times["get"].append(time.perf_counter() - start_time)
                return None

            entry = self._cache[key]

            # Check expiration
            if entry.is_expired:
                del self._cache[key]
                self.stats.misses += 1
                self.stats.evictions += 1
                self.metrics.operation_times["get"].append(time.perf_counter() - start_time)
                return None

            # Update access
            entry.touch()

            # Move to end (for LRU)
            self._cache.move_to_end(key)

            self.stats.hits += 1
            self.metrics.operation_times["get"].append(time.perf_counter() - start_time)

            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Set value in cache"""
        start_time = time.perf_counter()
        ttl = ttl or self.default_ttl

        try:
            # Serialize value and calculate size
            serialized_value = self._serialize_value(value)
            value_size = len(serialized_value)

            async with self._lock:
                # Check if eviction is needed
                if key not in self._cache:
                    victim_key = self.eviction_policy.should_evict(
                        list(self._cache.values()), value_size, self.max_size
                    )
                    if victim_key:
                        del self._cache[victim_key]
                        self.stats.evictions += 1

                # Create cache entry
                now = datetime.now()
                entry = CacheEntry(
                    value=value,
                    ttl=ttl,
                    created_at=now,
                    last_accessed=now,
                    size_bytes=value_size,
                    tags=tags or set(),
                    level=CacheLevel.L1_MEMORY,
                    metadata=metadata or {},
                )

                self._cache[key] = entry
                self._cache.move_to_end(key)

                self.stats.sets += 1
                self.metrics.operation_times["set"].append(time.perf_counter() - start_time)

                # Update tag usage
                for tag in entry.tags:
                    self.metrics.tag_usage[tag] += 1

                # Update size distribution
                size_category = self._categorize_size(value_size)
                self.metrics.size_distribution[size_category] += 1

                return True

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        start_time = time.perf_counter()

        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self.stats.deletes += 1
                self.metrics.operation_times["delete"].append(time.perf_counter() - start_time)
                return True
            return False

    async def clear(self) -> bool:
        """Clear all cache entries"""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self.stats.deletes += count
            return True

    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """Invalidate entries by tags"""
        async with self._lock:
            keys_to_delete = []
            for key, entry in self._cache.items():
                if entry.tags & tags:  # Intersection
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self._cache[key]

            self.stats.deletes += len(keys_to_delete)
            return len(keys_to_delete)

    async def warm_cache(self, entries: Dict[str, Tuple[Any, int, Set[str]]]):
        """Warm cache with multiple entries"""
        tasks = []
        for key, (value, ttl, tags) in entries.items():
            tasks.append(self.set(key, value, ttl, tags))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if r is True)
        logger.info(f"Cache warming completed: {successful}/{len(entries)} entries loaded")

    def _categorize_size(self, size_bytes: int) -> str:
        """Categorize entry size"""
        if size_bytes < 1024:
            return "small (<1KB)"
        elif size_bytes < 10240:
            return "medium (1-10KB)"
        elif size_bytes < 102400:
            return "large (10-100KB)"
        else:
            return "xlarge (>100KB)"

    async def _cleanup_expired(self):
        """Background task to clean up expired entries"""
        while True:
            try:
                async with self._lock:
                    expired_keys = [key for key, entry in self._cache.items() if entry.is_expired]

                    for key in expired_keys:
                        del self._cache[key]
                        self.stats.evictions += 1

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(60)

    async def _update_stats(self):
        """Background task to update statistics"""
        while True:
            try:
                async with self._lock:
                    # Update basic stats
                    self.stats.total_entries = len(self._cache)
                    self.stats.total_size_bytes = sum(
                        entry.size_bytes for entry in self._cache.values()
                    )
                    self.stats.memory_usage_mb = self.stats.total_size_bytes / 1024 / 1024

                await asyncio.sleep(30)  # Update every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stats update error: {e}")
                await asyncio.sleep(30)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "hit_rate": self.stats.hit_rate,
            "miss_rate": self.stats.miss_rate,
            "total_entries": self.stats.total_entries,
            "memory_usage_mb": self.stats.memory_usage_mb,
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "sets": self.stats.sets,
            "deletes": self.stats.deletes,
            "evictions": self.stats.evictions,
            "errors": self.stats.errors,
            "tag_usage": dict(self.metrics.tag_usage),
            "size_distribution": dict(self.metrics.size_distribution),
        }

    async def close(self):
        """Close cache and cleanup resources"""
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._stats_task:
            self._stats_task.cancel()
            try:
                await self._stats_task
            except asyncio.CancelledError:
                pass

        # Clear cache
        await self.clear()


class L2RedisCache:
    """Level 2 Redis cache implementation"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 3600,
        key_prefix: str = "fastapi_easy:",
        enable_stats: bool = True,
    ):
        """
        Initialize L2 Redis cache

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
            key_prefix: Key prefix for Redis
            enable_stats: Enable statistics tracking
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis package is required for L2 cache")

        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.enable_stats = enable_stats

        # Redis client
        self._redis: Optional[redis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None

        # Statistics
        self.stats = CacheStats()

        # Locks
        self._lock = asyncio.Lock()

    async def connect(self):
        """Connect to Redis"""
        if self._redis is None:
            self._connection_pool = redis.ConnectionPool.from_url(self.redis_url)
            self._redis = redis.Redis(connection_pool=self._connection_pool)

            # Test connection
            await self._redis.ping()
            logger.info("Connected to Redis L2 cache")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            self._redis = None

        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None

    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix"""
        return f"{self.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        if self._redis is None:
            await self.connect()

        start_time = time.perf_counter()

        try:
            redis_key = self._make_key(key)
            data = await self._redis.get(redis_key)

            if data is None:
                self.stats.misses += 1
                return None

            # Deserialize value
            value = pickle.loads(data)
            self.stats.hits += 1

            return value

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Redis get failed for key {key}: {e}")
            return None

        finally:
            self.metrics.operation_times["get"].append(time.perf_counter() - start_time)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Set value in Redis"""
        if self._redis is None:
            await self.connect()

        start_time = time.perf_counter()
        ttl = ttl or self.default_ttl

        try:
            redis_key = self._make_key(key)
            data = pickle.dumps(value)

            # Store with tags in metadata
            if tags or metadata:
                cache_meta = {"tags": list(tags or []), **(metadata or {})}
                # Store metadata separately or as part of value
                # For simplicity, we'll store as part of the pickled value

            await self._redis.setex(redis_key, ttl, data)
            self.stats.sets += 1
            return True

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Redis set failed for key {key}: {e}")
            return False

        finally:
            self.metrics.operation_times["set"].append(time.perf_counter() - start_time)

    async def delete(self, key: str) -> bool:
        """Delete value from Redis"""
        if self._redis is None:
            await self.connect()

        start_time = time.perf_counter()

        try:
            redis_key = self._make_key(key)
            result = await self._redis.delete(redis_key)
            self.stats.deletes += result
            return result > 0

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Redis delete failed for key {key}: {e}")
            return False

        finally:
            self.metrics.operation_times["delete"].append(time.perf_counter() - start_time)


class AdvancedCacheManager:
    """Advanced multi-layer cache manager"""

    def __init__(
        self,
        l1_config: Optional[Dict[str, Any]] = None,
        l2_config: Optional[Dict[str, Any]] = None,
        enable_l2: bool = REDIS_AVAILABLE,
    ):
        """
        Initialize advanced cache manager

        Args:
            l1_config: L1 cache configuration
            l2_config: L2 cache configuration
            enable_l2: Enable L2 Redis cache
        """
        l1_config = l1_config or {}
        l2_config = l2_config or {}

        # Initialize L1 cache
        self.l1_cache = L1MemoryCache(**l1_config)

        # Initialize L2 cache if enabled
        self.l2_cache = None
        if enable_l2:
            try:
                self.l2_cache = L2RedisCache(**l2_config)
            except ImportError:
                logger.warning("Redis not available, L2 cache disabled")

        # Cache policies
        self.cache_warmup_policies: Dict[str, Callable] = {}
        self.invalidation_policies: Dict[str, Callable] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 first, then L2)"""
        # Try L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            return value

        # Try L2 cache if available
        if self.l2_cache:
            value = await self.l2_cache.get(key)
            if value is not None:
                # Promote to L1 cache
                await self.l1_cache.set(key, value)
                return value

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        store_in_l2: bool = True,
    ) -> bool:
        """Set value in cache (both L1 and optionally L2)"""
        # Always store in L1
        l1_success = await self.l1_cache.set(key, value, ttl, tags)

        # Store in L2 if enabled and requested
        l2_success = True
        if self.l2_cache and store_in_l2:
            l2_success = await self.l2_cache.set(key, value, ttl, tags)

        return l1_success and l2_success

    async def delete(self, key: str) -> bool:
        """Delete value from both cache layers"""
        l1_success = await self.l1_cache.delete(key)
        l2_success = True

        if self.l2_cache:
            l2_success = await self.l2_cache.delete(key)

        return l1_success or l2_success

    async def invalidate_by_tags(self, tags: Set[str]) -> int:
        """Invalidate entries by tags across all layers"""
        l1_count = await self.l1_cache.invalidate_by_tags(tags)
        # L2 tag invalidation would require additional metadata storage
        return l1_count

    async def warm_cache(self, cache_name: str):
        """Warm cache using predefined policies"""
        if cache_name in self.cache_warmup_policies:
            entries = await self.cache_warmup_policies[cache_name]()
            await self.l1_cache.warm_cache(entries)

    def register_warmup_policy(self, name: str, policy: Callable):
        """Register cache warmup policy"""
        self.cache_warmup_policies[name] = policy

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        stats = {"l1": self.l1_cache.get_stats(), "l2": None}

        if self.l2_cache:
            stats["l2"] = {
                "hits": self.l2_cache.stats.hits,
                "misses": self.l2_cache.stats.misses,
                "hit_rate": self.l2_cache.stats.hit_rate,
                "sets": self.l2_cache.stats.sets,
                "deletes": self.l2_cache.stats.deletes,
                "errors": self.l2_cache.stats.errors,
            }

        return stats

    async def close(self):
        """Close cache manager and cleanup resources"""
        await self.l1_cache.close()
        if self.l2_cache:
            await self.l2_cache.disconnect()


# Global cache manager instance
_global_cache_manager: Optional[AdvancedCacheManager] = None


def get_cache_manager() -> AdvancedCacheManager:
    """Get or create global cache manager"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = AdvancedCacheManager()
    return _global_cache_manager


def create_cache_manager(**kwargs) -> AdvancedCacheManager:
    """Create new cache manager instance"""
    return AdvancedCacheManager(**kwargs)
