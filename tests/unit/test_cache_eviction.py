"""Tests for cache eviction"""

import pytest
from fastapi_easy.core.cache_eviction import (
    LRUEvictionStrategy,
    LFUEvictionStrategy,
    FIFOEvictionStrategy,
    CacheEvictionManager,
)


class TestLRUEvictionStrategy:
    """Test LRU eviction strategy"""

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction"""
        strategy = LRUEvictionStrategy()
        cache = {f"key_{i}": f"value_{i}" for i in range(100)}

        # Record access times
        for i in range(100):
            strategy.record_access(f"key_{i}")

        # Evict when reaching max size
        evicted = await strategy.evict(cache, max_size=50)

        assert evicted > 0
        assert len(cache) <= 50

    def test_lru_access_tracking(self):
        """Test LRU access tracking"""
        strategy = LRUEvictionStrategy()

        strategy.record_access("key1")
        strategy.record_access("key2")

        assert "key1" in strategy.access_times
        assert "key2" in strategy.access_times

    def test_lru_remove_key(self):
        """Test removing key from LRU tracking"""
        strategy = LRUEvictionStrategy()

        strategy.record_access("key1")
        strategy.remove_key("key1")

        assert "key1" not in strategy.access_times


class TestLFUEvictionStrategy:
    """Test LFU eviction strategy"""

    @pytest.mark.asyncio
    async def test_lfu_eviction(self):
        """Test LFU eviction"""
        strategy = LFUEvictionStrategy()
        cache = {f"key_{i}": f"value_{i}" for i in range(100)}

        # Record access counts
        for i in range(100):
            for _ in range(i % 10 + 1):
                strategy.record_access(f"key_{i}")

        # Evict when reaching max size
        evicted = await strategy.evict(cache, max_size=50)

        assert evicted > 0
        assert len(cache) <= 50


class TestFIFOEvictionStrategy:
    """Test FIFO eviction strategy"""

    @pytest.mark.asyncio
    async def test_fifo_eviction(self):
        """Test FIFO eviction"""
        strategy = FIFOEvictionStrategy()
        cache = {f"key_{i}": f"value_{i}" for i in range(100)}

        # Record insertion times
        for i in range(100):
            strategy.record_insertion(f"key_{i}")

        # Evict when reaching max size
        evicted = await strategy.evict(cache, max_size=50)

        assert evicted > 0
        assert len(cache) <= 50


class TestCacheEvictionManager:
    """Test cache eviction manager"""

    def test_lru_manager(self):
        """Test LRU eviction manager"""
        manager = CacheEvictionManager(strategy="lru")

        assert manager.strategy_name == "lru"
        assert isinstance(manager.strategy, LRUEvictionStrategy)

    def test_lfu_manager(self):
        """Test LFU eviction manager"""
        manager = CacheEvictionManager(strategy="lfu")

        assert manager.strategy_name == "lfu"
        assert isinstance(manager.strategy, LFUEvictionStrategy)

    def test_fifo_manager(self):
        """Test FIFO eviction manager"""
        manager = CacheEvictionManager(strategy="fifo")

        assert manager.strategy_name == "fifo"
        assert isinstance(manager.strategy, FIFOEvictionStrategy)

    def test_invalid_strategy(self):
        """Test invalid strategy"""
        with pytest.raises(ValueError):
            CacheEvictionManager(strategy="invalid")

    @pytest.mark.asyncio
    async def test_check_and_evict(self):
        """Test check and evict"""
        manager = CacheEvictionManager(strategy="lru")
        cache = {f"key_{i}": f"value_{i}" for i in range(100)}

        # Record access
        for i in range(100):
            manager.record_access(f"key_{i}")

        # Check and evict
        evicted = await manager.check_and_evict(cache, max_size=50)

        assert evicted > 0
        assert len(cache) <= 50

    def test_get_stats(self):
        """Test getting statistics"""
        manager = CacheEvictionManager(strategy="lru")

        stats = manager.get_stats()

        assert "strategy" in stats
        assert "total_evictions" in stats
        assert "items_evicted" in stats
