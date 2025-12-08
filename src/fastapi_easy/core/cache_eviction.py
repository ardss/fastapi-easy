"""Cache eviction strategies with LRU support

This module provides cache eviction mechanisms to prevent unbounded
memory growth while maintaining optimal hit rates.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class EvictionStrategy:
    """Base class for eviction strategies"""

    async def evict(self, cache_dict: Dict[str, Any], max_size: int) -> int:
        """Evict items from cache

        Args:
            cache_dict: Cache dictionary
            max_size: Maximum cache size

        Returns:
            Number of items evicted
        """
        raise NotImplementedError


class LRUEvictionStrategy(EvictionStrategy):
    """Least Recently Used (LRU) eviction strategy

    Evicts the least recently used items when cache reaches max size.
    """

    def __init__(self):
        """Initialize LRU strategy"""
        self.access_times: Dict[str, float] = {}

    async def evict(self, cache_dict: Dict[str, Any], max_size: int) -> int:
        """Evict LRU items

        Args:
            cache_dict: Cache dictionary
            max_size: Maximum cache size

        Returns:
            Number of items evicted
        """
        if len(cache_dict) < max_size:
            return 0

        # Calculate how many items to evict
        # Evict 20% of cache when limit is reached
        target_size = int(max_size * 0.8)
        items_to_evict = len(cache_dict) - target_size

        if items_to_evict <= 0:
            return 0

        # Find least recently used items
        lru_items = sorted(self.access_times.items(), key=lambda x: x[1])[:items_to_evict]

        # Evict items
        evicted = 0
        for key, _ in lru_items:
            if key in cache_dict:
                del cache_dict[key]
                del self.access_times[key]
                evicted += 1

        logger.debug(f"LRU eviction: evicted {evicted} items")
        return evicted

    def record_access(self, key: str) -> None:
        """Record access time for LRU tracking

        Args:
            key: Cache key
        """
        self.access_times[key] = time.time()

    def remove_key(self, key: str) -> None:
        """Remove key from tracking

        Args:
            key: Cache key
        """
        self.access_times.pop(key, None)


class LFUEvictionStrategy(EvictionStrategy):
    """Least Frequently Used (LFU) eviction strategy

    Evicts the least frequently used items when cache reaches max size.
    """

    def __init__(self):
        """Initialize LFU strategy"""
        self.access_counts: Dict[str, int] = {}

    async def evict(self, cache_dict: Dict[str, Any], max_size: int) -> int:
        """Evict LFU items

        Args:
            cache_dict: Cache dictionary
            max_size: Maximum cache size

        Returns:
            Number of items evicted
        """
        if len(cache_dict) < max_size:
            return 0

        # Calculate how many items to evict
        target_size = int(max_size * 0.8)
        items_to_evict = len(cache_dict) - target_size

        if items_to_evict <= 0:
            return 0

        # Find least frequently used items
        lfu_items = sorted(self.access_counts.items(), key=lambda x: x[1])[:items_to_evict]

        # Evict items
        evicted = 0
        for key, _ in lfu_items:
            if key in cache_dict:
                del cache_dict[key]
                del self.access_counts[key]
                evicted += 1

        logger.debug(f"LFU eviction: evicted {evicted} items")
        return evicted

    def record_access(self, key: str) -> None:
        """Record access count for LFU tracking

        Args:
            key: Cache key
        """
        self.access_counts[key] = self.access_counts.get(key, 0) + 1

    def remove_key(self, key: str) -> None:
        """Remove key from tracking

        Args:
            key: Cache key
        """
        self.access_counts.pop(key, None)


class FIFOEvictionStrategy(EvictionStrategy):
    """First In First Out (FIFO) eviction strategy

    Evicts the oldest items when cache reaches max size.
    """

    def __init__(self):
        """Initialize FIFO strategy"""
        self.insertion_times: Dict[str, float] = {}

    async def evict(self, cache_dict: Dict[str, Any], max_size: int) -> int:
        """Evict FIFO items

        Args:
            cache_dict: Cache dictionary
            max_size: Maximum cache size

        Returns:
            Number of items evicted
        """
        if len(cache_dict) < max_size:
            return 0

        # Calculate how many items to evict
        target_size = int(max_size * 0.8)
        items_to_evict = len(cache_dict) - target_size

        if items_to_evict <= 0:
            return 0

        # Find oldest items
        fifo_items = sorted(self.insertion_times.items(), key=lambda x: x[1])[:items_to_evict]

        # Evict items
        evicted = 0
        for key, _ in fifo_items:
            if key in cache_dict:
                del cache_dict[key]
                del self.insertion_times[key]
                evicted += 1

        logger.debug(f"FIFO eviction: evicted {evicted} items")
        return evicted

    def record_insertion(self, key: str) -> None:
        """Record insertion time for FIFO tracking

        Args:
            key: Cache key
        """
        self.insertion_times[key] = time.time()

    def remove_key(self, key: str) -> None:
        """Remove key from tracking

        Args:
            key: Cache key
        """
        self.insertion_times.pop(key, None)


class CacheEvictionManager:
    """Manage cache eviction with configurable strategies"""

    def __init__(self, strategy: str = "lru"):
        """Initialize eviction manager

        Args:
            strategy: Eviction strategy ('lru', 'lfu', 'fifo')
        """
        self.strategy_name = strategy

        if strategy == "lru":
            self.strategy = LRUEvictionStrategy()
        elif strategy == "lfu":
            self.strategy = LFUEvictionStrategy()
        elif strategy == "fifo":
            self.strategy = FIFOEvictionStrategy()
        else:
            raise ValueError(f"Unknown eviction strategy: {strategy}")

        self.eviction_stats = {
            "total_evictions": 0,
            "items_evicted": 0,
        }

    async def check_and_evict(self, cache_dict: Dict[str, Any], max_size: int) -> int:
        """Check cache size and evict if necessary

        Args:
            cache_dict: Cache dictionary
            max_size: Maximum cache size

        Returns:
            Number of items evicted
        """
        if len(cache_dict) >= max_size:
            evicted = await self.strategy.evict(cache_dict, max_size)
            self.eviction_stats["total_evictions"] += 1
            self.eviction_stats["items_evicted"] += evicted
            return evicted

        return 0

    def record_access(self, key: str) -> None:
        """Record access for eviction tracking

        Args:
            key: Cache key
        """
        if hasattr(self.strategy, "record_access"):
            self.strategy.record_access(key)
        elif hasattr(self.strategy, "record_insertion"):
            # For FIFO, only record on insertion
            pass

    def record_insertion(self, key: str) -> None:
        """Record insertion for eviction tracking

        Args:
            key: Cache key
        """
        if hasattr(self.strategy, "record_insertion"):
            self.strategy.record_insertion(key)
        elif hasattr(self.strategy, "record_access"):
            self.strategy.record_access(key)

    def remove_key(self, key: str) -> None:
        """Remove key from eviction tracking

        Args:
            key: Cache key
        """
        if hasattr(self.strategy, "remove_key"):
            self.strategy.remove_key(key)

    def get_stats(self) -> Dict[str, Any]:
        """Get eviction statistics

        Returns:
            Statistics dictionary
        """
        return {"strategy": self.strategy_name, **self.eviction_stats}
