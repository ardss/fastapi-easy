"""Unit tests for permission control"""

import pytest
from fastapi_easy.core.permissions import (
    Permission,
    Role,
    PermissionDeniedError,
    RoleBasedAccessControl,
    AttributeBasedAccessControl,
    PermissionContext,
    PermissionChecker,
    PermissionConfig,
)


class TestRoleBasedAccessControl:
    """Test RBAC functionality"""
    
    def test_rbac_initialization(self):
        """Test RBAC initialization"""
        rbac = RoleBasedAccessControl()
        
        assert Role.ADMIN in rbac.role_permissions
        assert Role.EDITOR in rbac.role_permissions
        assert Role.VIEWER in rbac.role_permissions
    
    def test_admin_has_all_permissions(self):
        """Test admin has all permissions"""
        rbac = RoleBasedAccessControl()
        
        assert rbac.has_permission(Role.ADMIN, Permission.CREATE)
        assert rbac.has_permission(Role.ADMIN, Permission.READ)
        assert rbac.has_permission(Role.ADMIN, Permission.UPDATE)
        assert rbac.has_permission(Role.ADMIN, Permission.DELETE)
    
    def test_viewer_has_read_only(self):
        """Test viewer has read-only permission"""
        rbac = RoleBasedAccessControl()
        
        assert rbac.has_permission(Role.VIEWER, Permission.READ)
        assert not rbac.has_permission(Role.VIEWER, Permission.CREATE)
        assert not rbac.has_permission(Role.VIEWER, Permission.UPDATE)
        assert not rbac.has_permission(Role.VIEWER, Permission.DELETE)
    
    def test_add_role(self):
        """Test adding a new role"""
        rbac = RoleBasedAccessControl()
        
        rbac.add_role("moderator", {Permission.READ, Permission.UPDATE})
        
        assert rbac.has_permission("moderator", Permission.READ)
        assert rbac.has_permission("moderator", Permission.UPDATE)
        assert not rbac.has_permission("moderator", Permission.DELETE)
    
    def test_add_permission_to_role(self):
        """Test adding permission to role"""
        rbac = RoleBasedAccessControl()
        
        rbac.add_permission_to_role(Role.VIEWER, Permission.CREATE)
        
        assert rbac.has_permission(Role.VIEWER, Permission.CREATE)
    
    def test_remove_permission_from_role(self):
        """Test removing permission from role"""
        rbac = RoleBasedAccessControl()
        
        rbac.remove_permission_from_role(Role.ADMIN, Permission.DELETE)
        
        assert not rbac.has_permission(Role.ADMIN, Permission.DELETE)
    
    def test_get_permissions(self):
        """Test getting all permissions for role"""
        rbac = RoleBasedAccessControl()
        
        permissions = rbac.get_permissions(Role.VIEWER)
        
        assert Permission.READ in permissions
        assert Permission.CREATE not in permissions


class TestAttributeBasedAccessControl:
    """Test ABAC functionality"""
    
    def test_abac_initialization(self):
        """Test ABAC initialization"""
        abac = AttributeBasedAccessControl()
        
        assert abac.policies == []
    
    def test_add_policy(self):
        """Test adding policy"""
        abac = AttributeBasedAccessControl()
        
        def policy(context):
            return context.get("age", 0) >= 18
        
        abac.add_policy(policy)
        
        assert len(abac.policies) == 1
    
    @pytest.mark.asyncio
    async def test_evaluate_policies_pass(self):
        """Test evaluating policies that pass"""
        abac = AttributeBasedAccessControl()
        
        def policy1(context):
            return context.get("age", 0) >= 18
        
        def policy2(context):
            return context.get("status") == "active"
        
        abac.add_policy(policy1)
        abac.add_policy(policy2)
        
        context = {"age": 25, "status": "active"}
        result = await abac.evaluate(context)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_evaluate_policies_fail(self):
        """Test evaluating policies that fail"""
        abac = AttributeBasedAccessControl()
        
        def policy(context):
            return context.get("age", 0) >= 18
        
        abac.add_policy(policy)
        
        context = {"age": 16}
        result = await abac.evaluate(context)
        
        assert result is False


class TestPermissionContext:
    """Test PermissionContext"""
    
    def test_context_initialization(self):
        """Test context initialization"""
        context = PermissionContext(
            user_id=1,
            roles=[Role.ADMIN],
            permissions={Permission.CREATE},
        )
        
        assert context.user_id == 1
        assert Role.ADMIN in context.roles
        assert Permission.CREATE in context.permissions
    
    def test_has_role(self):
        """Test has_role method"""
        context = PermissionContext(roles=[Role.ADMIN])
        
        assert context.has_role(Role.ADMIN)
        assert not context.has_role(Role.VIEWER)
    
    def test_has_permission(self):
        """Test has_permission method"""
        context = PermissionContext(permissions={Permission.READ})
        
        assert context.has_permission(Permission.READ)
        assert not context.has_permission(Permission.CREATE)
    
    def test_is_admin(self):
        """Test is_admin method"""
        admin_context = PermissionContext(roles=[Role.ADMIN])
        user_context = PermissionContext(roles=[Role.USER])
        
        assert admin_context.is_admin()
        assert not user_context.is_admin()


class TestPermissionChecker:
    """Test PermissionChecker"""
    
    def test_checker_initialization(self):
        """Test checker initialization"""
        checker = PermissionChecker()
        
        assert checker.rbac is not None
    
    def test_check_permission_success(self):
        """Test successful permission check"""
        checker = PermissionChecker()
        context = PermissionContext(roles=[Role.ADMIN])
        
        # Should not raise
        checker.check_permission(context, Permission.DELETE)
    
    def test_check_permission_failure(self):
        """Test failed permission check"""
        checker = PermissionChecker()
        context = PermissionContext(roles=[Role.VIEWER])
        
        with pytest.raises(PermissionDeniedError):
            checker.check_permission(context, Permission.DELETE)
    
    def test_check_any_permission_success(self):
        """Test successful any permission check"""
        checker = PermissionChecker()
        context = PermissionContext(roles=[Role.EDITOR])
        
        # Should not raise
        checker.check_any_permission(
            context,
            [Permission.DELETE, Permission.UPDATE],
        )
    
    def test_check_any_permission_failure(self):
        """Test failed any permission check"""
        checker = PermissionChecker()
        context = PermissionContext(roles=[Role.VIEWER])
        
        with pytest.raises(PermissionDeniedError):
            checker.check_any_permission(
                context,
                [Permission.DELETE, Permission.CREATE],
            )
    
    def test_check_all_permissions_success(self):
        """Test successful all permissions check"""
        checker = PermissionChecker()
        context = PermissionContext(roles=[Role.ADMIN])
        
        # Should not raise
        checker.check_all_permissions(
            context,
            [Permission.CREATE, Permission.READ, Permission.UPDATE],
        )
    
    def test_check_all_permissions_failure(self):
        """Test failed all permissions check"""
        checker = PermissionChecker()
        context = PermissionContext(roles=[Role.VIEWER])
        
        with pytest.raises(PermissionDeniedError):
            checker.check_all_permissions(
                context,
                [Permission.READ, Permission.CREATE],
            )


class TestPermissionConfig:
    """Test PermissionConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = PermissionConfig()
        
        assert config.enabled is True
        assert config.default_role == Role.USER
        assert config.require_authentication is True
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = PermissionConfig(
            enabled=False,
            default_role=Role.VIEWER,
            require_authentication=False,
        )
        
        assert config.enabled is False
        assert config.default_role == Role.VIEWER
        assert config.require_authentication is False
