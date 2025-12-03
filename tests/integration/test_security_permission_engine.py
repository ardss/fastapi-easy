"""Tests for permission engine"""

import pytest

from fastapi_easy.security.permission_engine import PermissionEngine
from fastapi_easy.security.permission_loader import StaticPermissionLoader
from fastapi_easy.security.resource_checker import StaticResourceChecker


class TestPermissionEngine:
    """Test permission engine"""

    def test_init_valid(self):
        """Test initialization with valid parameters"""
        loader = StaticPermissionLoader({"user1": ["read", "write"]})
        engine = PermissionEngine(permission_loader=loader)

        assert engine.permission_loader is not None
        assert engine.resource_checker is None
        assert engine.enable_cache is True
        assert engine.cache_ttl == 300

    def test_init_with_resource_checker(self):
        """Test initialization with resource checker"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        checker = StaticResourceChecker({})
        engine = PermissionEngine(permission_loader=loader, resource_checker=checker)

        assert engine.permission_loader is not None
        assert engine.resource_checker is not None

    def test_init_without_cache(self):
        """Test initialization without cache"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        engine = PermissionEngine(permission_loader=loader, enable_cache=False)

        assert engine.enable_cache is False

    def test_init_custom_ttl(self):
        """Test initialization with custom TTL"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        engine = PermissionEngine(permission_loader=loader, cache_ttl=600)

        assert engine.cache_ttl == 600

    def test_init_invalid_loader(self):
        """Test initialization with invalid loader"""
        with pytest.raises(TypeError):
            PermissionEngine(permission_loader="invalid")

    def test_init_invalid_checker(self):
        """Test initialization with invalid checker"""
        loader = StaticPermissionLoader({"user1": ["read"]})

        with pytest.raises(TypeError):
            PermissionEngine(permission_loader=loader, resource_checker="invalid")

    @pytest.mark.asyncio
    async def test_check_permission_true(self):
        """Test permission check returns true"""
        loader = StaticPermissionLoader({"user1": ["read", "write"]})
        engine = PermissionEngine(permission_loader=loader)

        has_permission = await engine.check_permission("user1", "read")
        assert has_permission is True

    @pytest.mark.asyncio
    async def test_check_permission_false(self):
        """Test permission check returns false"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        engine = PermissionEngine(permission_loader=loader)

        has_permission = await engine.check_permission("user1", "write")
        assert has_permission is False

    @pytest.mark.asyncio
    async def test_check_permission_invalid_user_id_type(self):
        """Test permission check with invalid user_id type"""
        loader = StaticPermissionLoader({})
        engine = PermissionEngine(permission_loader=loader)

        with pytest.raises(TypeError):
            await engine.check_permission(123, "read")

    @pytest.mark.asyncio
    async def test_check_permission_invalid_permission_type(self):
        """Test permission check with invalid permission type"""
        loader = StaticPermissionLoader({})
        engine = PermissionEngine(permission_loader=loader)

        with pytest.raises(TypeError):
            await engine.check_permission("user1", 123)

    @pytest.mark.asyncio
    async def test_check_permission_empty_user_id(self):
        """Test permission check with empty user_id"""
        loader = StaticPermissionLoader({})
        engine = PermissionEngine(permission_loader=loader)

        with pytest.raises(ValueError):
            await engine.check_permission("", "read")

    @pytest.mark.asyncio
    async def test_check_permission_empty_permission(self):
        """Test permission check with empty permission"""
        loader = StaticPermissionLoader({})
        engine = PermissionEngine(permission_loader=loader)

        with pytest.raises(ValueError):
            await engine.check_permission("user1", "")

    @pytest.mark.asyncio
    async def test_check_resource_permission_true(self):
        """Test resource permission check returns true"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        checker = StaticResourceChecker({"resource1": {"owner_id": "user1", "permissions": {}}})
        engine = PermissionEngine(permission_loader=loader, resource_checker=checker)

        has_permission = await engine.check_permission("user1", "read", "resource1")
        assert has_permission is True

    @pytest.mark.asyncio
    async def test_check_resource_permission_false(self):
        """Test resource permission check returns false"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        checker = StaticResourceChecker({"resource1": {"owner_id": "user2", "permissions": {}}})
        engine = PermissionEngine(permission_loader=loader, resource_checker=checker)

        has_permission = await engine.check_permission("user1", "write", "resource1")
        assert has_permission is False

    @pytest.mark.asyncio
    async def test_check_all_permissions_true(self):
        """Test check all permissions returns true"""
        loader = StaticPermissionLoader({"user1": ["read", "write", "delete"]})
        engine = PermissionEngine(permission_loader=loader)

        has_all = await engine.check_all_permissions("user1", ["read", "write"])
        assert has_all is True

    @pytest.mark.asyncio
    async def test_check_all_permissions_false(self):
        """Test check all permissions returns false"""
        loader = StaticPermissionLoader({"user1": ["read", "write"]})
        engine = PermissionEngine(permission_loader=loader)

        has_all = await engine.check_all_permissions("user1", ["read", "write", "delete"])
        assert has_all is False

    @pytest.mark.asyncio
    async def test_check_all_permissions_invalid_type(self):
        """Test check all permissions with invalid type"""
        loader = StaticPermissionLoader({})
        engine = PermissionEngine(permission_loader=loader)

        with pytest.raises(TypeError):
            await engine.check_all_permissions("user1", "invalid")

    @pytest.mark.asyncio
    async def test_check_any_permission_true(self):
        """Test check any permission returns true"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        engine = PermissionEngine(permission_loader=loader)

        has_any = await engine.check_any_permission("user1", ["read", "write"])
        assert has_any is True

    @pytest.mark.asyncio
    async def test_check_any_permission_false(self):
        """Test check any permission returns false"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        engine = PermissionEngine(permission_loader=loader)

        has_any = await engine.check_any_permission("user1", ["write", "delete"])
        assert has_any is False

    @pytest.mark.asyncio
    async def test_check_any_permission_invalid_type(self):
        """Test check any permission with invalid type"""
        loader = StaticPermissionLoader({})
        engine = PermissionEngine(permission_loader=loader)

        with pytest.raises(TypeError):
            await engine.check_any_permission("user1", "invalid")

    def test_clear_cache(self):
        """Test clearing cache"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        engine = PermissionEngine(permission_loader=loader)

        # Should not raise
        engine.clear_cache("user1")

    def test_clear_cache_all(self):
        """Test clearing all cache"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        engine = PermissionEngine(permission_loader=loader)

        # Should not raise
        engine.clear_cache()

    def test_repr(self):
        """Test string representation"""
        loader = StaticPermissionLoader({"user1": ["read"]})
        engine = PermissionEngine(permission_loader=loader)

        repr_str = repr(engine)
        assert "PermissionEngine" in repr_str
        assert "CachedPermissionLoader" in repr_str
