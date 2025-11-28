"""Integration of security module with CRUDRouter"""

from typing import Any, Callable, List, Optional

from fastapi import Depends, HTTPException

from .decorators import get_current_user, require_permission, require_role


class CRUDSecurityConfig:
    """Configuration for CRUD security integration"""

    def __init__(
        self,
        enable_auth: bool = False,
        require_roles: Optional[List[str]] = None,
        require_permissions: Optional[List[str]] = None,
        role_permissions_map: Optional[dict] = None,
    ):
        """Initialize CRUD security config

        Args:
            enable_auth: Enable authentication for all routes
            require_roles: Required roles for all routes
            require_permissions: Required permissions for all routes
            role_permissions_map: Map of roles to permissions
        """
        self.enable_auth = enable_auth
        self.require_roles = require_roles or []
        self.require_permissions = require_permissions or []
        self.role_permissions_map = role_permissions_map or {}


class ProtectedCRUDRouter:
    """Wrapper for CRUDRouter with security integration"""

    def __init__(
        self,
        crud_router,
        security_config: Optional[CRUDSecurityConfig] = None,
    ):
        """Initialize protected CRUD router

        Args:
            crud_router: CRUDRouter instance
            security_config: Security configuration
        """
        self.crud_router = crud_router
        self.security_config = security_config or CRUDSecurityConfig()

    def add_security_to_routes(self) -> None:
        """Add security checks to all routes"""
        if not self.security_config.enable_auth:
            return

        # Get all routes from the router
        for route in self.crud_router.routes:
            if hasattr(route, "endpoint"):
                # Wrap the endpoint with security checks
                original_endpoint = route.endpoint
                route.endpoint = self._wrap_with_security(original_endpoint)

    def _wrap_with_security(self, endpoint: Callable) -> Callable:
        """Wrap endpoint with security checks

        Args:
            endpoint: Original endpoint function

        Returns:
            Wrapped endpoint function
        """
        async def secured_endpoint(*args, **kwargs):
            # Get current user
            current_user = kwargs.get("current_user")
            if current_user is None:
                # Try to get from dependency injection
                try:
                    current_user = await get_current_user(
                        kwargs.get("authorization")
                    )
                except Exception:
                    if self.security_config.enable_auth:
                        raise HTTPException(status_code=401, detail="Unauthorized")

            # Check roles
            if self.security_config.require_roles:
                user_roles = current_user.get("roles", [])
                if not any(role in user_roles for role in self.security_config.require_roles):
                    raise HTTPException(
                        status_code=403,
                        detail="Insufficient role",
                    )

            # Check permissions
            if self.security_config.require_permissions:
                user_permissions = current_user.get("permissions", [])
                if not any(
                    perm in user_permissions
                    for perm in self.security_config.require_permissions
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="Insufficient permission",
                    )

            # Call original endpoint
            return await endpoint(*args, **kwargs)

        return secured_endpoint

    def get_protected_routes(self) -> List[Any]:
        """Get all protected routes

        Returns:
            List of protected routes
        """
        return self.crud_router.routes


def create_protected_crud_router(
    crud_router,
    enable_auth: bool = False,
    require_roles: Optional[List[str]] = None,
    require_permissions: Optional[List[str]] = None,
) -> ProtectedCRUDRouter:
    """Create a protected CRUD router

    Args:
        crud_router: CRUDRouter instance
        enable_auth: Enable authentication
        require_roles: Required roles
        require_permissions: Required permissions

    Returns:
        ProtectedCRUDRouter instance
    """
    security_config = CRUDSecurityConfig(
        enable_auth=enable_auth,
        require_roles=require_roles,
        require_permissions=require_permissions,
    )

    protected_router = ProtectedCRUDRouter(crud_router, security_config)
    protected_router.add_security_to_routes()

    return protected_router
