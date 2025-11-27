"""Unit tests for caching"""

import pytest
import asyncio
from fastapi_easy.core.cache import (
    CacheEntry,
    MemoryCache,
    NoCache,
    CacheKey,
    CachedOperation,
    CacheConfig,
    create_cache,
    get_cache,
)


class TestCacheEntry:
    """Test CacheEntry"""
    
    def test_entry_initialization(self):
        """Test cache entry initialization"""
        entry = CacheEntry("value", ttl=10)
        
        assert entry.value == "value"
        assert entry.ttl == 10
    
    def test_entry_not_expired(self):
        """Test entry not expired"""
        entry = CacheEntry("value", ttl=10)
        
        assert entry.is_expired() is False
        assert entry.get() == "value"
    
    def test_entry_expired(self):
        """Test entry expired"""
        entry = CacheEntry("value", ttl=0)
        
        # Wait for expiration
        import time
        time.sleep(0.1)
        
        assert entry.is_expired() is True
        assert entry.get() is None
    
    def test_entry_no_ttl(self):
        """Test entry without TTL"""
        entry = CacheEntry("value", ttl=None)
        
        assert entry.is_expired() is False
        assert entry.get() == "value"


class TestMemoryCache:
    """Test MemoryCache"""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting value"""
        cache = MemoryCache()
        
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result == "value1"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """Test getting nonexistent key"""
        cache = MemoryCache()
        
        result = await cache.get("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting value"""
        cache = MemoryCache()
        
        await cache.set("key1", "value1")
        await cache.delete("key1")
        result = await cache.get("key1")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing cache"""
        cache = MemoryCache()
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        
        result1 = await cache.get("key1")
        result2 = await cache.get("key2")
        
        assert result1 is None
        assert result2 is None
    
    @pytest.mark.asyncio
    async def test_exists(self):
        """Test checking key existence"""
        cache = MemoryCache()
        
        await cache.set("key1", "value1")
        
        assert await cache.exists("key1") is True
        assert await cache.exists("nonexistent") is False
    
    @pytest.mark.asyncio
    async def test_ttl(self):
        """Test TTL functionality"""
        cache = MemoryCache()
        
        await cache.set("key1", "value1", ttl=1)
        result1 = await cache.get("key1")
        
        assert result1 == "value1"
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        result2 = await cache.get("key1")
        
        assert result2 is None
    
    @pytest.mark.asyncio
    async def test_max_size(self):
        """Test max size eviction"""
        cache = MemoryCache(max_size=2)
        
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # key1 should be evicted
        result1 = await cache.get("key1")
        result2 = await cache.get("key2")
        result3 = await cache.get("key3")
        
        assert result1 is None
        assert result2 == "value2"
        assert result3 == "value3"
    
    def test_get_stats(self):
        """Test getting cache statistics"""
        cache = MemoryCache()
        
        # Simulate some hits and misses
        cache.hits = 10
        cache.misses = 5
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 10
        assert stats["misses"] == 5
        assert stats["hit_rate"] == pytest.approx(66.67, rel=0.1)


class TestNoCache:
    """Test NoCache"""
    
    @pytest.mark.asyncio
    async def test_get_always_none(self):
        """Test get always returns None"""
        cache = NoCache()
        
        result = await cache.get("key1")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_noop(self):
        """Test set is no-op"""
        cache = NoCache()
        
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_noop(self):
        """Test delete is no-op"""
        cache = NoCache()
        
        await cache.delete("key1")
        
        # No error should occur
        assert True
    
    @pytest.mark.asyncio
    async def test_clear_noop(self):
        """Test clear is no-op"""
        cache = NoCache()
        
        await cache.clear()
        
        # No error should occur
        assert True
    
    @pytest.mark.asyncio
    async def test_exists_always_false(self):
        """Test exists always returns False"""
        cache = NoCache()
        
        result = await cache.exists("key1")
        
        assert result is False


class TestCacheKey:
    """Test CacheKey"""
    
    def test_build_with_args(self):
        """Test building key with args"""
        key = CacheKey.build("prefix", "arg1", "arg2")
        
        assert key == "prefix:arg1:arg2"
    
    def test_build_with_kwargs(self):
        """Test building key with kwargs"""
        key = CacheKey.build("prefix", id=1, name="test")
        
        assert "prefix" in key
        assert "id=1" in key
        assert "name=test" in key
    
    def test_build_with_mixed(self):
        """Test building key with mixed args and kwargs"""
        key = CacheKey.build("prefix", "arg1", id=1)
        
        assert "prefix" in key
        assert "arg1" in key
        assert "id=1" in key


class TestCachedOperation:
    """Test CachedOperation"""
    
    @pytest.mark.asyncio
    async def test_cached_function(self):
        """Test caching function results"""
        cache = MemoryCache()
        call_count = 0
        
        @CachedOperation(cache, ttl=10)
        async def get_data(id):
            nonlocal call_count
            call_count += 1
            return {"id": id, "name": "test"}
        
        # First call
        result1 = await get_data(1)
        assert call_count == 1
        
        # Second call (should be cached)
        result2 = await get_data(1)
        assert call_count == 1
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_cached_function_different_args(self):
        """Test caching with different arguments"""
        cache = MemoryCache()
        call_count = 0
        
        @CachedOperation(cache)
        async def get_data(id):
            nonlocal call_count
            call_count += 1
            return {"id": id}
        
        # Different arguments should not use cache
        await get_data(1)
        await get_data(2)
        
        assert call_count == 2


class TestCacheConfig:
    """Test CacheConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = CacheConfig()
        
        assert config.enabled is True
        assert config.backend == "memory"
        assert config.ttl == 3600
        assert config.max_size == 1000
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = CacheConfig(
            enabled=False,
            backend="redis",
            ttl=1800,
            max_size=500,
        )
        
        assert config.enabled is False
        assert config.backend == "redis"
        assert config.ttl == 1800
        assert config.max_size == 500


class TestCreateCache:
    """Test create_cache function"""
    
    def test_create_memory_cache(self):
        """Test creating memory cache"""
        config = CacheConfig(backend="memory")
        cache = create_cache(config)
        
        assert isinstance(cache, MemoryCache)
    
    def test_create_no_cache(self):
        """Test creating no-op cache when disabled"""
        config = CacheConfig(enabled=False)
        cache = create_cache(config)
        
        assert isinstance(cache, NoCache)


class TestGlobalCache:
    """Test global cache"""
    
    def test_get_global_cache(self):
        """Test getting global cache"""
        cache = get_cache()
        
        assert cache is not None
        assert isinstance(cache, MemoryCache)
    
    def test_global_cache_singleton(self):
        """Test global cache is singleton"""
        cache1 = get_cache()
        cache2 = get_cache()
        
        assert cache1 is cache2
