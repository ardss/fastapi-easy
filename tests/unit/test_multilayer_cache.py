"""Tests for multi-layer cache module"""

import pytest
from fastapi_easy.core.multilayer_cache import MultiLayerCache, create_multilayer_cache


class TestMultiLayerCache:
    """Test MultiLayerCache class"""

    @pytest.mark.asyncio
    async def test_l1_cache_hit(self):
        """Test L1 cache hit"""
        cache = MultiLayerCache()
        await cache.set("key1", "value1", tier="l1")

        result = await cache.get("key1")
        assert result == "value1"
        assert cache.l1_hits == 1
        assert cache.l2_hits == 0

    @pytest.mark.asyncio
    async def test_l2_cache_hit_and_promotion(self):
        """Test L2 cache hit and promotion to L1"""
        cache = MultiLayerCache()
        await cache.set("key1", "value1", tier="l2")

        # First access: L2 hit
        result = await cache.get("key1")
        assert result == "value1"
        assert cache.l2_hits == 1

        # Second access: L1 hit (promoted)
        result = await cache.get("key1")
        assert result == "value1"
        assert cache.l1_hits == 1

    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss"""
        cache = MultiLayerCache()

        result = await cache.get("nonexistent")
        assert result is None
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_set_both_tiers(self):
        """Test setting value in both tiers"""
        cache = MultiLayerCache()
        await cache.set("key1", "value1")

        # Should be in both L1 and L2
        result = await cache.get("key1")
        assert result == "value1"
        assert cache.l1_hits == 1

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting from both caches"""
        cache = MultiLayerCache()
        await cache.set("key1", "value1")
        await cache.delete("key1")

        result = await cache.get("key1")
        assert result is None
        assert cache.misses == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing all caches"""
        cache = MultiLayerCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()

        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    def test_get_stats(self):
        """Test cache statistics"""
        cache = MultiLayerCache()
        stats = cache.get_stats()

        assert stats["l1_hits"] == 0
        assert stats["l2_hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0
        assert stats["hit_rate"] == "0.0%"

    @pytest.mark.asyncio
    async def test_hit_rate_calculation(self):
        """Test hit rate calculation"""
        cache = MultiLayerCache()
        await cache.set("key1", "value1")

        # 2 hits
        await cache.get("key1")
        await cache.get("key1")

        # 1 miss
        await cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["l1_hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_requests"] == 3
        assert "66" in stats["hit_rate"]  # ~66.7%


class TestFactoryFunction:
    """Test factory function"""

    def test_create_multilayer_cache(self):
        """Test creating multi-layer cache"""
        cache = create_multilayer_cache(
            l1_size=500,
            l1_ttl=30,
            l2_size=5000,
            l2_ttl=300,
        )

        assert cache.l1_cache.get_stats()["max_size"] == 500
        assert cache.l2_cache.get_stats()["max_size"] == 5000
