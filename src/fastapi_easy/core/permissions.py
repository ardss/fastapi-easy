"""Permission control support for FastAPI-Easy"""

from typing import Any, Callable, List, Optional, Set
from enum import Enum
from functools import wraps

from .errors import AppError, ErrorCode


class Permission(str, Enum):
    """Permission enumeration"""
    
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ADMIN = "admin"


class Role(str, Enum):
    """Role enumeration"""
    
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    USER = "user"


class PermissionDeniedError(AppError):
    """Permission denied error"""
    
    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            code=ErrorCode.PERMISSION_DENIED,
            status_code=403,
            message=message,
        )


class RoleBasedAccessControl:
    """Role-based access control (RBAC)"""
    
    def __init__(self):
        """Initialize RBAC"""
        self.role_permissions: dict[str, Set[str]] = {
            Role.ADMIN: {Permission.CREATE, Permission.READ, Permission.UPDATE, Permission.DELETE, Permission.ADMIN},
            Role.EDITOR: {Permission.CREATE, Permission.READ, Permission.UPDATE},
            Role.VIEWER: {Permission.READ},
            Role.USER: {Permission.READ},
        }
    
    def add_role(self, role: str, permissions: Set[str]) -> None:
        """Add a new role with permissions
        
        Args:
            role: Role name
            permissions: Set of permissions
        """
        self.role_permissions[role] = permissions
    
    def add_permission_to_role(self, role: str, permission: str) -> None:
        """Add permission to a role
        
        Args:
            role: Role name
            permission: Permission to add
        """
        if role not in self.role_permissions:
            self.role_permissions[role] = set()
        self.role_permissions[role].add(permission)
    
    def remove_permission_from_role(self, role: str, permission: str) -> None:
        """Remove permission from a role
        
        Args:
            role: Role name
            permission: Permission to remove
        """
        if role in self.role_permissions:
            self.role_permissions[role].discard(permission)
    
    def has_permission(self, role: str, permission: str) -> bool:
        """Check if role has permission
        
        Args:
            role: Role name
            permission: Permission to check
            
        Returns:
            True if role has permission
        """
        if role not in self.role_permissions:
            return False
        return permission in self.role_permissions[role]
    
    def get_permissions(self, role: str) -> Set[str]:
        """Get all permissions for a role
        
        Args:
            role: Role name
            
        Returns:
            Set of permissions
        """
        return self.role_permissions.get(role, set())


class AttributeBasedAccessControl:
    """Attribute-based access control (ABAC)"""
    
    def __init__(self):
        """Initialize ABAC"""
        self.policies: List[Callable] = []
    
    def add_policy(self, policy: Callable) -> None:
        """Add a policy
        
        Args:
            policy: Policy function that returns True/False
        """
        self.policies.append(policy)
    
    async def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluate all policies
        
        Args:
            context: Context dictionary with attributes
            
        Returns:
            True if all policies pass
        """
        for policy in self.policies:
            if callable(policy):
                result = policy(context)
                if hasattr(result, '__await__'):
                    result = await result
                if not result:
                    return False
        return True


class PermissionContext:
    """Permission context for requests"""
    
    def __init__(
        self,
        user_id: Optional[int] = None,
        roles: Optional[List[str]] = None,
        permissions: Optional[Set[str]] = None,
        attributes: Optional[dict[str, Any]] = None,
    ):
        """Initialize permission context
        
        Args:
            user_id: User ID
            roles: List of roles
            permissions: Set of permissions
            attributes: Additional attributes
        """
        self.user_id = user_id
        self.roles = roles or []
        self.permissions = permissions or set()
        self.attributes = attributes or {}
    
    def has_role(self, role: str) -> bool:
        """Check if context has role
        
        Args:
            role: Role to check
            
        Returns:
            True if context has role
        """
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if context has permission
        
        Args:
            permission: Permission to check
            
        Returns:
            True if context has permission
        """
        return permission in self.permissions
    
    def is_admin(self) -> bool:
        """Check if context is admin
        
        Returns:
            True if context has admin role
        """
        return self.has_role(Role.ADMIN)


class PermissionChecker:
    """Permission checker utility"""
    
    def __init__(self, rbac: Optional[RoleBasedAccessControl] = None):
        """Initialize permission checker
        
        Args:
            rbac: RBAC instance
        """
        self.rbac = rbac or RoleBasedAccessControl()
    
    def check_permission(
        self,
        context: PermissionContext,
        required_permission: str,
    ) -> None:
        """Check if context has required permission
        
        Args:
            context: Permission context
            required_permission: Required permission
            
        Raises:
            PermissionDeniedError: If permission denied
        """
        # Check direct permissions
        if context.has_permission(required_permission):
            return
        
        # Check role-based permissions
        for role in context.roles:
            if self.rbac.has_permission(role, required_permission):
                return
        
        raise PermissionDeniedError(
            f"Permission '{required_permission}' denied for user {context.user_id}"
        )
    
    def check_any_permission(
        self,
        context: PermissionContext,
        permissions: List[str],
    ) -> None:
        """Check if context has any of the permissions
        
        Args:
            context: Permission context
            permissions: List of permissions
            
        Raises:
            PermissionDeniedError: If no permission found
        """
        for permission in permissions:
            try:
                self.check_permission(context, permission)
                return
            except PermissionDeniedError:
                continue
        
        raise PermissionDeniedError(
            f"None of the required permissions found for user {context.user_id}"
        )
    
    def check_all_permissions(
        self,
        context: PermissionContext,
        permissions: List[str],
    ) -> None:
        """Check if context has all permissions
        
        Args:
            context: Permission context
            permissions: List of permissions
            
        Raises:
            PermissionDeniedError: If any permission missing
        """
        for permission in permissions:
            self.check_permission(context, permission)


class PermissionConfig:
    """Configuration for permissions"""
    
    def __init__(
        self,
        enabled: bool = True,
        default_role: str = Role.USER,
        require_authentication: bool = True,
    ):
        """Initialize permission configuration
        
        Args:
            enabled: Enable permission checking
            default_role: Default role for unauthenticated users
            require_authentication: Require authentication
        """
        self.enabled = enabled
        self.default_role = default_role
        self.require_authentication = require_authentication
