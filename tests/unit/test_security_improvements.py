"""Tests for security module improvements"""

import pytest
from pydantic import ValidationError

from fastapi_easy.security import (
    BatchPermissionCheckRequest,
    LRUCache,
    LRUCachedPermissionLoader,
    MonitoredPermissionEngine,
    PermissionCheckRequest,
    PermissionEngine,
    ResourceOwnershipCheckRequest,
    StaticPermissionLoader,
)

# ============================================================================
# LRUCache Tests
# ============================================================================


class TestLRUCache:
    """Test LRU cache implementation"""

    def test_lru_cache_init(self):
        """Test LRU cache initialization"""
        cache = LRUCache(max_size=100, ttl=300)
        assert cache.max_size == 100
        assert cache.ttl == 300
        assert cache.hits == 0
        assert cache.misses == 0

    def test_lru_cache_init_invalid_size(self):
        """Test LRU cache with invalid size"""
        with pytest.raises(ValueError):
            LRUCache(max_size=0)

    def test_lru_cache_init_invalid_ttl(self):
        """Test LRU cache with invalid TTL"""
        with pytest.raises(ValueError):
            LRUCache(ttl=0)

    def test_lru_cache_set_and_get(self):
        """Test LRU cache set and get"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.hits == 1
        assert cache.misses == 0

    def test_lru_cache_miss(self):
        """Test LRU cache miss"""
        cache = LRUCache(max_size=10)
        assert cache.get("nonexistent") is None
        assert cache.misses == 1

    def test_lru_cache_eviction(self):
        """Test LRU cache eviction"""
        cache = LRUCache(max_size=2)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # key1 should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_lru_cache_clear_all(self):
        """Test LRU cache clear all"""
        cache = LRUCache(max_size=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_lru_cache_clear_pattern(self):
        """Test LRU cache clear with pattern"""
        cache = LRUCache(max_size=10)
        cache.set("user:1", "data1")
        cache.set("user:2", "data2")
        cache.set("post:1", "data3")

        cache.clear(pattern="user:")
        assert cache.get("user:1") is None
        assert cache.get("user:2") is None
        assert cache.get("post:1") == "data3"

    def test_lru_cache_stats(self):
        """Test LRU cache statistics"""
        cache = LRUCache(max_size=10, ttl=300)
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total"] == 2
        assert "50.00%" in stats["hit_rate"]


# ============================================================================
# LRUCachedPermissionLoader Tests
# ============================================================================


class TestLRUCachedPermissionLoader:
    """Test LRU cached permission loader"""

    @pytest.mark.asyncio
    async def test_lru_cached_loader_init(self):
        """Test LRU cached loader initialization"""
        base_loader = StaticPermissionLoader({"user1": ["read"]})
        loader = LRUCachedPermissionLoader(base_loader, cache_ttl=300, max_size=100)

        assert loader.base_loader == base_loader
        assert loader.cache.max_size == 100
        assert loader.cache.ttl == 300

    @pytest.mark.asyncio
    async def test_lru_cached_loader_load(self):
        """Test LRU cached loader load"""
        base_loader = StaticPermissionLoader({"user1": ["read", "write"]})
        loader = LRUCachedPermissionLoader(base_loader)

        permissions = await loader.load_permissions("user1")
        assert permissions == ["read", "write"]

    @pytest.mark.asyncio
    async def test_lru_cached_loader_cache_hit(self):
        """Test LRU cached loader cache hit"""
        base_loader = StaticPermissionLoader({"user1": ["read"]})
        loader = LRUCachedPermissionLoader(base_loader)

        # First load
        await loader.load_permissions("user1")
        assert loader.cache.misses == 1

        # Second load (cache hit)
        await loader.load_permissions("user1")
        assert loader.cache.hits == 1

    @pytest.mark.asyncio
    async def test_lru_cached_loader_eviction(self):
        """Test LRU cached loader eviction"""
        base_loader = StaticPermissionLoader(
            {"user1": ["read"], "user2": ["write"], "user3": ["delete"]}
        )
        loader = LRUCachedPermissionLoader(base_loader, max_size=2)

        await loader.load_permissions("user1")
        await loader.load_permissions("user2")
        await loader.load_permissions("user3")

        # user1 should be evicted
        stats = loader.get_cache_stats()
        assert stats["size"] == 2

    @pytest.mark.asyncio
    async def test_lru_cached_loader_clear(self):
        """Test LRU cached loader clear"""
        base_loader = StaticPermissionLoader({"user1": ["read"]})
        loader = LRUCachedPermissionLoader(base_loader)

        await loader.load_permissions("user1")
        loader.clear_cache()

        stats = loader.get_cache_stats()
        assert stats["size"] == 0


# ============================================================================
# Input Validation Tests
# ============================================================================


class TestPermissionCheckRequest:
    """Test permission check request validation"""

    def test_valid_request(self):
        """Test valid permission check request"""
        req = PermissionCheckRequest(user_id="user1", permission="read")
        assert req.user_id == "user1"
        assert req.permission == "read"

    def test_empty_user_id(self):
        """Test empty user_id"""
        with pytest.raises(ValidationError):
            PermissionCheckRequest(user_id="", permission="read")

    def test_empty_permission(self):
        """Test empty permission"""
        with pytest.raises(ValidationError):
            PermissionCheckRequest(user_id="user1", permission="")

    def test_user_id_too_long(self):
        """Test user_id too long"""
        with pytest.raises(ValidationError):
            PermissionCheckRequest(user_id="x" * 256, permission="read")

    def test_permission_too_long(self):
        """Test permission too long"""
        with pytest.raises(ValidationError):
            PermissionCheckRequest(user_id="user1", permission="x" * 101)

    def test_invalid_user_id_chars(self):
        """Test invalid user_id characters"""
        with pytest.raises(ValidationError):
            PermissionCheckRequest(user_id="user@#$", permission="read")

    def test_invalid_permission_chars(self):
        """Test invalid permission characters"""
        with pytest.raises(ValidationError):
            PermissionCheckRequest(user_id="user1", permission="READ")

    def test_valid_resource_id(self):
        """Test valid resource_id"""
        req = PermissionCheckRequest(user_id="user1", permission="read", resource_id="post:123")
        assert req.resource_id == "post:123"


class TestResourceOwnershipCheckRequest:
    """Test resource ownership check request validation"""

    def test_valid_request(self):
        """Test valid resource ownership check request"""
        req = ResourceOwnershipCheckRequest(user_id="user1", resource_id="post:123")
        assert req.user_id == "user1"
        assert req.resource_id == "post:123"

    def test_empty_user_id(self):
        """Test empty user_id"""
        with pytest.raises(ValidationError):
            ResourceOwnershipCheckRequest(user_id="", resource_id="post:123")

    def test_empty_resource_id(self):
        """Test empty resource_id"""
        with pytest.raises(ValidationError):
            ResourceOwnershipCheckRequest(user_id="user1", resource_id="")


class TestBatchPermissionCheckRequest:
    """Test batch permission check request validation"""

    def test_valid_request(self):
        """Test valid batch permission check request"""
        req = BatchPermissionCheckRequest(user_id="user1", permissions=["read", "write"])
        assert req.user_id == "user1"
        assert req.permissions == ["read", "write"]

    def test_empty_permissions(self):
        """Test empty permissions list"""
        with pytest.raises(ValidationError):
            BatchPermissionCheckRequest(user_id="user1", permissions=[])

    def test_permissions_too_long(self):
        """Test permissions list too long"""
        with pytest.raises(ValidationError):
            BatchPermissionCheckRequest(user_id="user1", permissions=["perm"] * 101)

    def test_invalid_permission_in_list(self):
        """Test invalid permission in list"""
        with pytest.raises(ValidationError):
            BatchPermissionCheckRequest(user_id="user1", permissions=["read", "WRITE"])


# ============================================================================
# Monitoring Tests
# ============================================================================


@pytest.mark.asyncio
async def test_monitored_permission_engine():
    """Test monitored permission engine"""
    base_loader = StaticPermissionLoader({"user1": ["read"]})
    base_engine = PermissionEngine(permission_loader=base_loader)
    monitored_engine = MonitoredPermissionEngine(base_engine)

    # Check permission
    result = await monitored_engine.check_permission("user1", "read")
    assert result is True

    # Get metrics
    metrics = monitored_engine.get_metrics()
    assert metrics["total_checks"] == 1
    assert metrics["successful_checks"] == 1

    # Reset metrics
    monitored_engine.reset_metrics()
    metrics = monitored_engine.get_metrics()
    assert metrics["total_checks"] == 0
