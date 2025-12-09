"""
Advanced test caching system for FastAPI-Easy.
Provides intelligent caching of test data, database states, and expensive operations.
"""

import json
import pickle
import hashlib
import time
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Callable, Union, TypeVar, Generic
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, asdict
import tempfile
import shutil

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    data: Any
    timestamp: float
    ttl: Optional[float] = None
    hit_count: int = 0
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def hit(self) -> None:
        """Increment hit count"""
        self.hit_count += 1


class TestCache(Generic[T]):
    """Thread-safe test cache with multiple backends"""

    def __init__(self, cache_dir: Optional[Path] = None,
                 redis_url: Optional[str] = None,
                 default_ttl: float = 3600):
        self.cache_dir = cache_dir or Path(tempfile.mkdtemp(prefix="fastapi_easy_cache_"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

        # Initialize Redis if available and URL provided
        self._redis_client = None
        if redis_url and REDIS_AVAILABLE:
            try:
                self._redis_client = redis.from_url(redis_url)
                self._redis_client.ping()  # Test connection
            except Exception:
                self._redis_client = None

        self._stats = {
            "hits": 0,
            "misses": 0,
            "memory_hits": 0,
            "disk_hits": 0,
            "redis_hits": 0,
            "sets": 0,
            "evictions": 0,
        }

    def _generate_key(self, key: Union[str, Callable, tuple]) -> str:
        """Generate cache key from various inputs"""
        if isinstance(key, str):
            return key
        elif callable(key):
            # Use function name and source for key
            func_source = f"{key.__module__}.{key.__name__}"
            return hashlib.md5(func_source.encode()).hexdigest()
        elif isinstance(key, tuple):
            # Generate key from tuple of values
            serialized = json.dumps(key, sort_keys=True, default=str)
            return hashlib.md5(serialized.encode()).hexdigest()
        else:
            # Convert to string and hash
            return hashlib.md5(str(key).encode()).hexdigest()

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for disk cache"""
        # Use first two characters as subdirectory for better organization
        subdir = key[:2]
        cache_subdir = self.cache_dir / subdir
        cache_subdir.mkdir(exist_ok=True)
        return cache_subdir / f"{key}.cache"

    def _serialize(self, data: Any) -> bytes:
        """Serialize data for storage"""
        return pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL)

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize data from storage"""
        return pickle.loads(data)

    def get(self, key: Union[str, Callable, tuple]) -> Optional[T]:
        """Get value from cache (tries memory, then disk, then Redis)"""
        cache_key = self._generate_key(key)

        with self._lock:
            # Try memory cache first
            if cache_key in self._memory_cache:
                entry = self._memory_cache[cache_key]
                if not entry.is_expired():
                    entry.hit()
                    self._stats["hits"] += 1
                    self._stats["memory_hits"] += 1
                    return entry.data
                else:
                    # Remove expired entry
                    del self._memory_cache[cache_key]
                    self._stats["evictions"] += 1

            # Try Redis cache next
            if self._redis_client:
                try:
                    cached_data = self._redis_client.get(cache_key)
                    if cached_data:
                        data = self._deserialize(cached_data)
                        # Store in memory cache for faster access
                        entry = CacheEntry(
                            data=data,
                            timestamp=time.time(),
                            ttl=self.default_ttl
                        )
                        self._memory_cache[cache_key] = entry
                        entry.hit()
                        self._stats["hits"] += 1
                        self._stats["redis_hits"] += 1
                        return data
                except Exception:
                    pass  # Redis failed, continue to disk cache

            # Try disk cache last
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                try:
                    with open(cache_path, "rb") as f:
                        entry_data = pickle.load(f)

                    if not entry_data.is_expired():
                        # Load into memory cache
                        self._memory_cache[cache_key] = entry_data
                        entry_data.hit()
                        self._stats["hits"] += 1
                        self._stats["disk_hits"] += 1
                        return entry_data.data
                    else:
                        # Remove expired file
                        cache_path.unlink()
                        self._stats["evictions"] += 1
                except Exception:
                    pass  # Cache file corrupted, ignore

            # Cache miss
            self._stats["misses"] += 1
            return None

    def set(self, key: Union[str, Callable, tuple], value: T,
            ttl: Optional[float] = None) -> None:
        """Set value in cache"""
        cache_key = self._generate_key(key)
        actual_ttl = ttl or self.default_ttl

        with self._lock:
            # Create cache entry
            data_bytes = self._serialize(value)
            entry = CacheEntry(
                data=value,
                timestamp=time.time(),
                ttl=actual_ttl,
                size_bytes=len(data_bytes)
            )

            # Store in memory cache
            self._memory_cache[cache_key] = entry

            # Store in Redis if available
            if self._redis_client:
                try:
                    redis_ttl = int(actual_ttl) if actual_ttl else 0
                    self._redis_client.setex(cache_key, redis_ttl, data_bytes)
                except Exception:
                    pass  # Redis failed, continue

            # Store on disk
            cache_path = self._get_cache_path(cache_key)
            try:
                with open(cache_path, "wb") as f:
                    pickle.dump(entry, f)
            except Exception:
                pass  # Disk write failed, but memory cache is sufficient

            self._stats["sets"] += 1

    def delete(self, key: Union[str, Callable, tuple]) -> bool:
        """Delete value from cache"""
        cache_key = self._generate_key(key)
        deleted = False

        with self._lock:
            # Delete from memory cache
            if cache_key in self._memory_cache:
                del self._memory_cache[cache_key]
                deleted = True

            # Delete from Redis
            if self._redis_client:
                try:
                    self._redis_client.delete(cache_key)
                    deleted = True
                except Exception:
                    pass

            # Delete from disk
            cache_path = self._get_cache_path(cache_key)
            if cache_path.exists():
                try:
                    cache_path.unlink()
                    deleted = True
                except Exception:
                    pass

            return deleted

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            # Clear memory cache
            self._memory_cache.clear()

            # Clear Redis
            if self._redis_client:
                try:
                    self._redis_client.flushdb()
                except Exception:
                    pass

            # Clear disk cache
            try:
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass

            # Reset stats
            self._stats = {
                "hits": 0,
                "misses": 0,
                "memory_hits": 0,
                "disk_hits": 0,
                "redis_hits": 0,
                "sets": 0,
                "evictions": 0,
            }

    def cleanup_expired(self) -> int:
        """Clean up expired cache entries"""
        cleaned = 0
        current_time = time.time()

        with self._lock:
            # Clean memory cache
            expired_keys = [
                key for key, entry in self._memory_cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._memory_cache[key]
                cleaned += 1

            # Clean disk cache
            for cache_file in self.cache_dir.rglob("*.cache"):
                try:
                    with open(cache_file, "rb") as f:
                        entry = pickle.load(f)

                    if entry.is_expired():
                        cache_file.unlink()
                        cleaned += 1
                except Exception:
                    # Remove corrupted files
                    try:
                        cache_file.unlink()
                        cleaned += 1
                    except Exception:
                        pass

        return cleaned

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

            return {
                **self._stats,
                "hit_rate": hit_rate,
                "memory_cache_size": len(self._memory_cache),
                "disk_cache_files": len(list(self.cache_dir.rglob("*.cache"))),
                "cache_dir_size_mb": sum(
                    f.stat().st_size for f in self.cache_dir.rglob("*")
                    if f.is_file()
                ) / 1024 / 1024,
            }

    def __contains__(self, key: Union[str, Callable, tuple]) -> bool:
        """Check if key exists in cache"""
        return self.get(key) is not None


# Global test cache instance
test_cache = TestCache()


def cached(ttl: Optional[float] = None, key_func: Optional[Callable] = None,
          cache_instance: Optional[TestCache] = None):
    """Decorator for caching function results"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = cache_instance or test_cache

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = (func, args, tuple(sorted(kwargs.items())))

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = cache_instance or test_cache

            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = (func, args, tuple(sorted(kwargs.items())))

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator


class DatabaseCache:
    """Specialized cache for database operations and test data"""

    def __init__(self, cache_instance: Optional[TestCache] = None):
        self.cache = cache_instance or test_cache
        self._setup_fixtures = {}

    def cache_database_state(self, db_name: str, setup_func: Callable):
        """Cache database state setup"""
        @cached(ttl=7200, cache_instance=self.cache)  # 2 hours TTL
        def cached_setup():
            return setup_func()

        self._setup_fixtures[db_name] = cached_setup
        return cached_setup

    def get_cached_setup(self, db_name: str):
        """Get cached database setup"""
        return self._setup_fixtures.get(db_name)

    def cache_query_result(self, query: str, params: tuple, result: Any,
                          ttl: float = 1800):  # 30 minutes TTL
        """Cache database query result"""
        cache_key = f"query:{hashlib.md5(f'{query}{params}'.encode()).hexdigest()}"
        self.cache.set(cache_key, result, ttl=ttl)

    def get_cached_query(self, query: str, params: tuple) -> Optional[Any]:
        """Get cached query result"""
        cache_key = f"query:{hashlib.md5(f'{query}{params}'.encode()).hexdigest()}"
        return self.cache.get(cache_key)


# Global database cache instance
db_cache = DatabaseCache()


@contextmanager
def cache_context(cache_name: str, ttl: Optional[float] = None):
    """Context manager for temporary caching within a test"""
    temp_cache = TestCache(default_ttl=ttl or 3600)

    try:
        yield temp_cache
    finally:
        temp_cache.clear()


# Convenience functions for common caching patterns
def cache_test_data(data_name: str, data_factory: Callable,
                   ttl: float = 7200) -> Callable:
    """Cache test data created by a factory function"""
    @cached(ttl=ttl, key_func=lambda: f"test_data:{data_name}")
    def get_data():
        return data_factory()
    return get_data


def cache_expensive_operation(operation_name: str, operation: Callable,
                            ttl: float = 3600) -> Callable:
    """Cache results of expensive operations"""
    @cached(ttl=ttl, key_func=lambda *args, **kwargs: f"operation:{operation_name}:{hash((args, tuple(sorted(kwargs.items()))))}")
    def run_operation(*args, **kwargs):
        return operation(*args, **kwargs)
    return run_operation


# Export public API
__all__ = [
    "TestCache",
    "CacheEntry",
    "DatabaseCache",
    "test_cache",
    "db_cache",
    "cached",
    "cache_context",
    "cache_test_data",
    "cache_expensive_operation",
]