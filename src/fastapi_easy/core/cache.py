"""Simple in-memory cache for query results"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class CacheEntry:
    """Cache entry with TTL support"""

    def __init__(self, value: Any, ttl: int = 300):
        """Initialize cache entry

        Args:
            value: Cached value
            ttl: Time to live in seconds (default: 5 minutes)
        """
        self.value = value
        self.ttl = ttl
        self.created_at = datetime.now()

    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        return datetime.now() - self.created_at > timedelta(seconds=self.ttl)


class QueryCache:
    """Simple query result cache with TTL support"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """Initialize query cache

        Args:
            max_size: Maximum number of cached entries
            default_ttl: Default time to live in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters

        Args:
            prefix: Cache key prefix
            **kwargs: Parameters to include in key

        Returns:
            Cache key
        """
        # Sort kwargs for consistent key generation
        sorted_items = sorted(kwargs.items())
        key_str = f"{prefix}:{json.dumps(sorted_items, sort_keys=True, default=str)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return None

            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
        """
        async with self._lock:
            # Evict oldest entry if cache is full
            if len(self._cache) >= self._max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
                del self._cache[oldest_key]

            self._cache[key] = CacheEntry(value, ttl or self._default_ttl)

    async def delete(self, key: str) -> None:
        """Delete value from cache

        Args:
            key: Cache key
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()

    async def cleanup_expired(self) -> int:
        """Remove expired entries from cache

        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics

        Returns:
            Cache statistics
        """
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "usage_percent": (len(self._cache) / self._max_size) * 100,
            "default_ttl": self._default_ttl,
        }


# Global cache instance
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> QueryCache:
    """Get or create global query cache instance"""
    global _query_cache
    if _query_cache is None:
        _query_cache = QueryCache()
    return _query_cache


def create_query_cache(max_size: int = 1000, default_ttl: int = 300) -> QueryCache:
    """Create a new query cache instance

    Args:
        max_size: Maximum number of cached entries
        default_ttl: Default time to live in seconds

    Returns:
        Query cache instance
    """
    return QueryCache(max_size, default_ttl)
