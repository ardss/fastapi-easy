"""Tests for permission loader"""

import pytest

from fastapi_easy.security.permission_loader import (
    CachedPermissionLoader,
    DatabasePermissionLoader,
    StaticPermissionLoader,
)


class TestStaticPermissionLoader:
    """Test static permission loader"""

    def test_init_valid(self):
        """Test initialization with valid permissions map"""
        permissions_map = {"user1": ["read", "write"], "user2": ["read"]}
        loader = StaticPermissionLoader(permissions_map)
        assert loader.permissions_map == permissions_map

    def test_init_invalid_type(self):
        """Test initialization with invalid type"""
        with pytest.raises(TypeError):
            StaticPermissionLoader("invalid")

    @pytest.mark.asyncio
    async def test_load_permissions_existing_user(self):
        """Test loading permissions for existing user"""
        permissions_map = {"user1": ["read", "write"], "user2": ["read"]}
        loader = StaticPermissionLoader(permissions_map)

        permissions = await loader.load_permissions("user1")
        assert permissions == ["read", "write"]

    @pytest.mark.asyncio
    async def test_load_permissions_non_existing_user(self):
        """Test loading permissions for non-existing user"""
        permissions_map = {"user1": ["read", "write"]}
        loader = StaticPermissionLoader(permissions_map)

        permissions = await loader.load_permissions("user2")
        assert permissions == []

    @pytest.mark.asyncio
    async def test_load_permissions_invalid_user_id_type(self):
        """Test loading permissions with invalid user_id type"""
        loader = StaticPermissionLoader({})

        with pytest.raises(TypeError):
            await loader.load_permissions(123)

    @pytest.mark.asyncio
    async def test_load_permissions_empty_user_id(self):
        """Test loading permissions with empty user_id"""
        loader = StaticPermissionLoader({})

        with pytest.raises(ValueError):
            await loader.load_permissions("")


class TestDatabasePermissionLoader:
    """Test database permission loader"""

    def test_init(self):
        """Test initialization"""
        loader = DatabasePermissionLoader()
        assert loader.db_session is None

    def test_init_with_session(self):
        """Test initialization with session"""
        session = object()
        loader = DatabasePermissionLoader(session)
        assert loader.db_session is session

    @pytest.mark.asyncio
    async def test_load_permissions(self):
        """Test loading permissions"""
        loader = DatabasePermissionLoader()

        permissions = await loader.load_permissions("user1")
        assert permissions == []

    @pytest.mark.asyncio
    async def test_load_permissions_invalid_user_id_type(self):
        """Test loading permissions with invalid user_id type"""
        loader = DatabasePermissionLoader()

        with pytest.raises(TypeError):
            await loader.load_permissions(123)

    @pytest.mark.asyncio
    async def test_load_permissions_empty_user_id(self):
        """Test loading permissions with empty user_id"""
        loader = DatabasePermissionLoader()

        with pytest.raises(ValueError):
            await loader.load_permissions("")


class TestCachedPermissionLoader:
    """Test cached permission loader"""

    def test_init_valid(self):
        """Test initialization with valid loader"""
        base_loader = StaticPermissionLoader({"user1": ["read"]})
        cached_loader = CachedPermissionLoader(base_loader)
        assert cached_loader.base_loader is base_loader
        assert cached_loader.cache_ttl == 300

    def test_init_custom_ttl(self):
        """Test initialization with custom TTL"""
        base_loader = StaticPermissionLoader({"user1": ["read"]})
        cached_loader = CachedPermissionLoader(base_loader, cache_ttl=600)
        assert cached_loader.cache_ttl == 600

    def test_init_invalid_loader(self):
        """Test initialization with invalid loader"""
        with pytest.raises(TypeError):
            CachedPermissionLoader("invalid")

    @pytest.mark.asyncio
    async def test_load_permissions_cache_miss(self):
        """Test loading permissions with cache miss"""
        base_loader = StaticPermissionLoader({"user1": ["read", "write"]})
        cached_loader = CachedPermissionLoader(base_loader)

        permissions = await cached_loader.load_permissions("user1")
        assert permissions == ["read", "write"]
        assert "user1" in cached_loader.cache

    @pytest.mark.asyncio
    async def test_load_permissions_cache_hit(self):
        """Test loading permissions with cache hit"""
        base_loader = StaticPermissionLoader({"user1": ["read", "write"]})
        cached_loader = CachedPermissionLoader(base_loader)

        # First call
        permissions1 = await cached_loader.load_permissions("user1")

        # Modify base loader (should not affect cached result)
        base_loader.permissions_map["user1"] = ["read"]

        # Second call should return cached result
        permissions2 = await cached_loader.load_permissions("user1")
        assert permissions2 == ["read", "write"]

    @pytest.mark.asyncio
    async def test_load_permissions_invalid_user_id_type(self):
        """Test loading permissions with invalid user_id type"""
        base_loader = StaticPermissionLoader({})
        cached_loader = CachedPermissionLoader(base_loader)

        with pytest.raises(TypeError):
            await cached_loader.load_permissions(123)

    def test_clear_cache_all(self):
        """Test clearing all cache"""
        base_loader = StaticPermissionLoader({"user1": ["read"], "user2": ["write"]})
        cached_loader = CachedPermissionLoader(base_loader)

        cached_loader.cache["user1"] = ["read"]
        cached_loader.cache["user2"] = ["write"]

        cached_loader.clear_cache()
        assert len(cached_loader.cache) == 0

    def test_clear_cache_specific_user(self):
        """Test clearing cache for specific user"""
        base_loader = StaticPermissionLoader({"user1": ["read"], "user2": ["write"]})
        cached_loader = CachedPermissionLoader(base_loader)

        cached_loader.cache["user1"] = ["read"]
        cached_loader.cache["user2"] = ["write"]

        cached_loader.clear_cache("user1")
        assert "user1" not in cached_loader.cache
        assert "user2" in cached_loader.cache
