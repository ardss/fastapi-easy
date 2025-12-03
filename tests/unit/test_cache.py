"""Tests for query cache module"""

import pytest
from fastapi_easy.core.cache import QueryCache, CacheEntry, get_query_cache, create_query_cache


class TestCacheEntry:
    """Test CacheEntry class"""

    def test_cache_entry_creation(self):
        """Test creating a cache entry"""
        entry = CacheEntry("test_value", ttl=300)
        assert entry.value == "test_value"
        assert entry.ttl == 300
        assert not entry.is_expired()

    def test_cache_entry_expiration(self):
        """Test cache entry expiration"""
        entry = CacheEntry("test_value", ttl=0)
        assert entry.is_expired()


class TestQueryCache:
    """Test QueryCache class"""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test setting and getting cache values"""
        cache = QueryCache()
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_cache_get_nonexistent(self):
        """Test getting non-existent cache key"""
        cache = QueryCache()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_delete(self):
        """Test deleting cache entry"""
        cache = QueryCache()
        await cache.set("key1", "value1")
        await cache.delete("key1")
        result = await cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_clear(self):
        """Test clearing all cache entries"""
        cache = QueryCache()
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    @pytest.mark.asyncio
    async def test_cache_max_size(self):
        """Test cache max size enforcement"""
        cache = QueryCache(max_size=3)
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        await cache.set("key4", "value4")

        # Cache should have at most 3 entries
        stats = cache.get_stats()
        assert stats["size"] <= 3

    @pytest.mark.asyncio
    async def test_cache_generate_key(self):
        """Test cache key generation"""
        cache = QueryCache()
        key1 = cache._generate_key("test", field="name", value="test")
        key2 = cache._generate_key("test", field="name", value="test")
        key3 = cache._generate_key("test", field="name", value="other")

        # Same parameters should generate same key
        assert key1 == key2
        # Different parameters should generate different key
        assert key1 != key3

    @pytest.mark.asyncio
    async def test_cache_cleanup_expired(self):
        """Test cleaning up expired entries"""
        import asyncio

        cache = QueryCache()
        await cache.set("key1", "value1", ttl=1)
        await cache.set("key2", "value2", ttl=300)

        # Wait for first entry to expire
        await asyncio.sleep(1.1)

        removed = await cache.cleanup_expired()
        assert removed >= 1
        assert await cache.get("key2") == "value2"

    def test_cache_stats(self):
        """Test cache statistics"""
        cache = QueryCache(max_size=100, default_ttl=300)
        stats = cache.get_stats()

        assert stats["max_size"] == 100
        assert stats["default_ttl"] == 300
        assert stats["size"] == 0
        assert stats["usage_percent"] == 0


class TestGlobalCache:
    """Test global cache instance"""

    @pytest.mark.asyncio
    async def test_get_query_cache(self):
        """Test getting global query cache"""
        cache1 = get_query_cache()
        cache2 = get_query_cache()

        # Should return same instance
        assert cache1 is cache2

    @pytest.mark.asyncio
    async def test_create_query_cache(self):
        """Test creating new query cache"""
        cache1 = create_query_cache(max_size=500, default_ttl=600)
        cache2 = create_query_cache(max_size=500, default_ttl=600)

        # Should create different instances
        assert cache1 is not cache2

        stats1 = cache1.get_stats()
        assert stats1["max_size"] == 500
        assert stats1["default_ttl"] == 600
