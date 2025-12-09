"""Caching utilities for security module"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class LRUCache:
    """LRU (Least Recently Used) cache implementation"""

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """Initialize LRU cache

        Args:
            max_size: Maximum cache size (default: 1000)
            ttl: Time to live in seconds (default: 300)

        Raises:
            ValueError: If max_size or ttl is invalid
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        if ttl <= 0:
            raise ValueError("ttl must be positive")

        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.cache_times: Dict[str, float] = {}
        self.hits = 0
        self.misses = 0

        logger.debug(f"LRUCache initialized with max_size={max_size}, ttl={ttl}s")

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found or expired
        """
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        if key not in self.cache:
            self.misses += 1
            return None

        # Check if expired
        now = time.time()
        cache_time = self.cache_times.get(key, 0)
        if now - cache_time >= self.ttl:
            # Remove expired entry
            self.cache.pop(key, None)
            self.cache_times.pop(key, None)
            self.misses += 1
            logger.debug(f"Cache expired for key: {key}")
            return None

        # Move to end (most recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        logger.debug(f"Cache hit for key: {key}")
        return self.cache[key]

    def set(self, key: str, value: Any) -> None:
        """Set value in cache

        Args:
            key: Cache key
            value: Value to cache
        """
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        now = time.time()

        # Update existing key
        if key in self.cache:
            self.cache[key] = value
            self.cache_times[key] = now
            self.cache.move_to_end(key)
            logger.debug(f"Cache updated for key: {key}")
            return

        # Add new key
        self.cache[key] = value
        self.cache_times[key] = now

        # Remove oldest if exceeds max size
        if len(self.cache) > self.max_size:
            oldest_key = next(iter(self.cache))
            self.cache.pop(oldest_key)
            self.cache_times.pop(oldest_key, None)
            logger.debug(f"Cache evicted oldest key: {oldest_key}")

        logger.debug(f"Cache set for key: {key}")

    def clear(self, pattern: Optional[str] = None) -> None:
        """Clear cache

        Args:
            pattern: Pattern to match keys (None to clear all)
        """
        if pattern is None:
            self.cache.clear()
            self.cache_times.clear()
            logger.debug("Cache cleared completely")
        else:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                self.cache.pop(key, None)
                self.cache_times.pop(key, None)
            logger.debug(f"Cache cleared {len(keys_to_delete)} entries matching pattern: {pattern}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": f"{hit_rate:.2f}%",
            "ttl": self.ttl,
        }

    def reset_stats(self) -> None:
        """Reset cache statistics"""
        self.hits = 0
        self.misses = 0
        logger.debug("Cache statistics reset")
