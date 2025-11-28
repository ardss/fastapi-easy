"""Tests for multi-tenant support"""

import pytest

from fastapi_easy.security.multi_tenant import (
    MultiTenantPermissionLoader,
    MultiTenantResourceChecker,
    TenantContext,
)
from fastapi_easy.security.permission_loader import StaticPermissionLoader
from fastapi_easy.security.resource_checker import StaticResourceChecker


class TestTenantContext:
    """Test tenant context"""

    def test_init_valid(self):
        """Test initialization with valid tenant_id"""
        context = TenantContext("tenant1")
        assert context.tenant_id == "tenant1"

    def test_init_invalid_type(self):
        """Test initialization with invalid type"""
        with pytest.raises(TypeError):
            TenantContext(123)

    def test_init_empty_tenant_id(self):
        """Test initialization with empty tenant_id"""
        with pytest.raises(ValueError):
            TenantContext("")

    def test_repr(self):
        """Test string representation"""
        context = TenantContext("tenant1")
        assert "tenant1" in repr(context)


class TestMultiTenantPermissionLoader:
    """Test multi-tenant permission loader"""

    def test_init_valid(self):
        """Test initialization with valid loader"""
        base_loader = StaticPermissionLoader({"user1": ["read"]})
        loader = MultiTenantPermissionLoader(base_loader)
        assert loader.base_loader is base_loader

    def test_init_invalid_loader(self):
        """Test initialization with invalid loader"""
        with pytest.raises(TypeError):
            MultiTenantPermissionLoader("invalid")

    def test_set_tenant(self):
        """Test setting tenant"""
        base_loader = StaticPermissionLoader({})
        loader = MultiTenantPermissionLoader(base_loader)

        loader.set_tenant("tenant1")
        assert loader.get_tenant() == "tenant1"

    def test_set_tenant_invalid(self):
        """Test setting invalid tenant"""
        base_loader = StaticPermissionLoader({})
        loader = MultiTenantPermissionLoader(base_loader)

        with pytest.raises(ValueError):
            loader.set_tenant("")

    @pytest.mark.asyncio
    async def test_load_permissions_without_tenant(self):
        """Test loading permissions without tenant set"""
        base_loader = StaticPermissionLoader({"user1": ["read"]})
        loader = MultiTenantPermissionLoader(base_loader)

        with pytest.raises(ValueError):
            await loader.load_permissions("user1")

    @pytest.mark.asyncio
    async def test_load_permissions_with_tenant(self):
        """Test loading permissions with tenant set"""
        base_loader = StaticPermissionLoader({"user1": ["read", "write"]})
        loader = MultiTenantPermissionLoader(base_loader)

        loader.set_tenant("tenant1")
        permissions = await loader.load_permissions("user1")

        assert permissions == ["read", "write"]

    def test_clear_tenant(self):
        """Test clearing tenant"""
        base_loader = StaticPermissionLoader({})
        loader = MultiTenantPermissionLoader(base_loader)

        loader.set_tenant("tenant1")
        loader.clear_tenant()

        assert loader.get_tenant() is None


class TestMultiTenantResourceChecker:
    """Test multi-tenant resource checker"""

    def test_init_valid(self):
        """Test initialization with valid checker"""
        base_checker = StaticResourceChecker({})
        checker = MultiTenantResourceChecker(base_checker)
        assert checker.base_checker is base_checker

    def test_init_invalid_checker(self):
        """Test initialization with invalid checker"""
        with pytest.raises(TypeError):
            MultiTenantResourceChecker("invalid")

    def test_set_tenant(self):
        """Test setting tenant"""
        base_checker = StaticResourceChecker({})
        checker = MultiTenantResourceChecker(base_checker)

        checker.set_tenant("tenant1")
        assert checker.get_tenant() == "tenant1"

    def test_set_tenant_invalid(self):
        """Test setting invalid tenant"""
        base_checker = StaticResourceChecker({})
        checker = MultiTenantResourceChecker(base_checker)

        with pytest.raises(ValueError):
            checker.set_tenant("")

    @pytest.mark.asyncio
    async def test_check_owner_without_tenant(self):
        """Test checking owner without tenant set"""
        base_checker = StaticResourceChecker({})
        checker = MultiTenantResourceChecker(base_checker)

        with pytest.raises(ValueError):
            await checker.check_owner("user1", "resource1")

    @pytest.mark.asyncio
    async def test_check_owner_with_tenant(self):
        """Test checking owner with tenant set"""
        resources = {
            "resource1": {"owner_id": "user1", "permissions": {}}
        }
        base_checker = StaticResourceChecker(resources)
        checker = MultiTenantResourceChecker(base_checker)

        checker.set_tenant("tenant1")
        is_owner = await checker.check_owner("user1", "resource1")

        assert is_owner is True

    @pytest.mark.asyncio
    async def test_check_permission_without_tenant(self):
        """Test checking permission without tenant set"""
        base_checker = StaticResourceChecker({})
        checker = MultiTenantResourceChecker(base_checker)

        with pytest.raises(ValueError):
            await checker.check_permission("user1", "resource1", "read")

    @pytest.mark.asyncio
    async def test_check_permission_with_tenant(self):
        """Test checking permission with tenant set"""
        resources = {
            "resource1": {
                "owner_id": "user1",
                "permissions": {"user2": ["read"]},
            }
        }
        base_checker = StaticResourceChecker(resources)
        checker = MultiTenantResourceChecker(base_checker)

        checker.set_tenant("tenant1")
        has_permission = await checker.check_permission("user2", "resource1", "read")

        assert has_permission is True

    def test_clear_tenant(self):
        """Test clearing tenant"""
        base_checker = StaticResourceChecker({})
        checker = MultiTenantResourceChecker(base_checker)

        checker.set_tenant("tenant1")
        checker.clear_tenant()

        assert checker.get_tenant() is None
