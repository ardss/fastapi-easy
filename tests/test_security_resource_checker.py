"""Tests for resource checker"""

import pytest

from fastapi_easy.security.resource_checker import (
    CachedResourceChecker,
    DatabaseResourceChecker,
    StaticResourceChecker,
)


class TestStaticResourceChecker:
    """Test static resource checker"""

    def test_init_valid(self):
        """Test initialization with valid resources map"""
        resources_map = {
            "resource1": {"owner_id": "user1", "permissions": {"user2": ["read"]}},
            "resource2": {"owner_id": "user2", "permissions": {}},
        }
        checker = StaticResourceChecker(resources_map)
        assert checker.resources_map == resources_map

    def test_init_invalid_type(self):
        """Test initialization with invalid type"""
        with pytest.raises(TypeError):
            StaticResourceChecker("invalid")

    @pytest.mark.asyncio
    async def test_check_owner_true(self):
        """Test owner check returns true"""
        resources_map = {"resource1": {"owner_id": "user1", "permissions": {}}}
        checker = StaticResourceChecker(resources_map)

        is_owner = await checker.check_owner("user1", "resource1")
        assert is_owner is True

    @pytest.mark.asyncio
    async def test_check_owner_false(self):
        """Test owner check returns false"""
        resources_map = {"resource1": {"owner_id": "user1", "permissions": {}}}
        checker = StaticResourceChecker(resources_map)

        is_owner = await checker.check_owner("user2", "resource1")
        assert is_owner is False

    @pytest.mark.asyncio
    async def test_check_owner_resource_not_found(self):
        """Test owner check with non-existing resource"""
        checker = StaticResourceChecker({})

        is_owner = await checker.check_owner("user1", "resource1")
        assert is_owner is False

    @pytest.mark.asyncio
    async def test_check_owner_invalid_types(self):
        """Test owner check with invalid types"""
        checker = StaticResourceChecker({})

        with pytest.raises(TypeError):
            await checker.check_owner(123, "resource1")

        with pytest.raises(TypeError):
            await checker.check_owner("user1", 123)

    @pytest.mark.asyncio
    async def test_check_permission_owner(self):
        """Test permission check for owner"""
        resources_map = {"resource1": {"owner_id": "user1", "permissions": {}}}
        checker = StaticResourceChecker(resources_map)

        has_permission = await checker.check_permission("user1", "resource1", "write")
        assert has_permission is True

    @pytest.mark.asyncio
    async def test_check_permission_explicit(self):
        """Test permission check with explicit permission"""
        resources_map = {
            "resource1": {
                "owner_id": "user1",
                "permissions": {"user2": ["read", "write"]},
            }
        }
        checker = StaticResourceChecker(resources_map)

        has_permission = await checker.check_permission("user2", "resource1", "read")
        assert has_permission is True

    @pytest.mark.asyncio
    async def test_check_permission_denied(self):
        """Test permission check denied"""
        resources_map = {
            "resource1": {
                "owner_id": "user1",
                "permissions": {"user2": ["read"]},
            }
        }
        checker = StaticResourceChecker(resources_map)

        has_permission = await checker.check_permission("user2", "resource1", "write")
        assert has_permission is False

    @pytest.mark.asyncio
    async def test_check_permission_resource_not_found(self):
        """Test permission check with non-existing resource"""
        checker = StaticResourceChecker({})

        has_permission = await checker.check_permission("user1", "resource1", "read")
        assert has_permission is False

    @pytest.mark.asyncio
    async def test_check_permission_invalid_types(self):
        """Test permission check with invalid types"""
        checker = StaticResourceChecker({})

        with pytest.raises(TypeError):
            await checker.check_permission(123, "resource1", "read")

        with pytest.raises(TypeError):
            await checker.check_permission("user1", 123, "read")

        with pytest.raises(TypeError):
            await checker.check_permission("user1", "resource1", 123)


class TestDatabaseResourceChecker:
    """Test database resource checker"""

    def test_init(self):
        """Test initialization"""
        checker = DatabaseResourceChecker()
        assert checker.db_session is None

    def test_init_with_session(self):
        """Test initialization with session"""
        session = object()
        checker = DatabaseResourceChecker(session)
        assert checker.db_session is session

    @pytest.mark.asyncio
    async def test_check_owner(self):
        """Test owner check"""
        checker = DatabaseResourceChecker()

        is_owner = await checker.check_owner("user1", "resource1")
        assert is_owner is False

    @pytest.mark.asyncio
    async def test_check_permission(self):
        """Test permission check"""
        checker = DatabaseResourceChecker()

        has_permission = await checker.check_permission("user1", "resource1", "read")
        assert has_permission is False

    @pytest.mark.asyncio
    async def test_check_owner_invalid_types(self):
        """Test owner check with invalid types"""
        checker = DatabaseResourceChecker()

        with pytest.raises(TypeError):
            await checker.check_owner(123, "resource1")

    @pytest.mark.asyncio
    async def test_check_permission_invalid_types(self):
        """Test permission check with invalid types"""
        checker = DatabaseResourceChecker()

        with pytest.raises(TypeError):
            await checker.check_permission(123, "resource1", "read")


class TestCachedResourceChecker:
    """Test cached resource checker"""

    def test_init_valid(self):
        """Test initialization with valid checker"""
        base_checker = StaticResourceChecker(
            {"resource1": {"owner_id": "user1", "permissions": {}}}
        )
        cached_checker = CachedResourceChecker(base_checker)
        assert cached_checker.base_checker is base_checker
        assert cached_checker.cache_ttl == 300

    def test_init_custom_ttl(self):
        """Test initialization with custom TTL"""
        base_checker = StaticResourceChecker({})
        cached_checker = CachedResourceChecker(base_checker, cache_ttl=600)
        assert cached_checker.cache_ttl == 600

    def test_init_invalid_checker(self):
        """Test initialization with invalid checker"""
        with pytest.raises(TypeError):
            CachedResourceChecker("invalid")

    @pytest.mark.asyncio
    async def test_check_owner_cache_miss(self):
        """Test owner check with cache miss"""
        base_checker = StaticResourceChecker(
            {"resource1": {"owner_id": "user1", "permissions": {}}}
        )
        cached_checker = CachedResourceChecker(base_checker)

        is_owner = await cached_checker.check_owner("user1", "resource1")
        assert is_owner is True
        assert "owner:user1:resource1" in cached_checker.cache

    @pytest.mark.asyncio
    async def test_check_owner_cache_hit(self):
        """Test owner check with cache hit"""
        base_checker = StaticResourceChecker(
            {"resource1": {"owner_id": "user1", "permissions": {}}}
        )
        cached_checker = CachedResourceChecker(base_checker)

        # First call
        is_owner1 = await cached_checker.check_owner("user1", "resource1")

        # Modify base checker (should not affect cached result)
        base_checker.resources_map["resource1"]["owner_id"] = "user2"

        # Second call should return cached result
        is_owner2 = await cached_checker.check_owner("user1", "resource1")
        assert is_owner2 is True

    @pytest.mark.asyncio
    async def test_check_permission_cache_miss(self):
        """Test permission check with cache miss"""
        base_checker = StaticResourceChecker(
            {"resource1": {"owner_id": "user1", "permissions": {}}}
        )
        cached_checker = CachedResourceChecker(base_checker)

        has_permission = await cached_checker.check_permission("user1", "resource1", "read")
        assert has_permission is True
        assert "perm:user1:resource1:read" in cached_checker.cache

    @pytest.mark.asyncio
    async def test_check_permission_cache_hit(self):
        """Test permission check with cache hit"""
        base_checker = StaticResourceChecker(
            {"resource1": {"owner_id": "user1", "permissions": {}}}
        )
        cached_checker = CachedResourceChecker(base_checker)

        # First call
        has_permission1 = await cached_checker.check_permission("user1", "resource1", "read")

        # Modify base checker (should not affect cached result)
        base_checker.resources_map["resource1"]["owner_id"] = "user2"

        # Second call should return cached result
        has_permission2 = await cached_checker.check_permission("user1", "resource1", "read")
        assert has_permission2 is True

    def test_clear_cache_all(self):
        """Test clearing all cache"""
        base_checker = StaticResourceChecker({})
        cached_checker = CachedResourceChecker(base_checker)

        cached_checker.cache["owner:user1:resource1"] = True
        cached_checker.cache["perm:user1:resource1:read"] = True

        cached_checker.clear_cache()
        assert len(cached_checker.cache) == 0

    def test_clear_cache_pattern(self):
        """Test clearing cache by pattern"""
        base_checker = StaticResourceChecker({})
        cached_checker = CachedResourceChecker(base_checker)

        cached_checker.cache["owner:user1:resource1"] = True
        cached_checker.cache["perm:user1:resource1:read"] = True
        cached_checker.cache["owner:user2:resource2"] = True

        cached_checker.clear_cache("user1")
        assert "owner:user1:resource1" not in cached_checker.cache
        assert "perm:user1:resource1:read" not in cached_checker.cache
        assert "owner:user2:resource2" in cached_checker.cache
