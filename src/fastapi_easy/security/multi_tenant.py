"""Multi-tenant support for security module"""

import logging
from typing import Any, Dict, List, Optional

from .permission_loader import PermissionLoader
from .resource_checker import ResourcePermissionChecker

logger = logging.getLogger(__name__)


class TenantContext:
    """Tenant context for multi-tenant applications"""

    def __init__(self, tenant_id: str):
        """Initialize tenant context

        Args:
            tenant_id: Tenant ID

        Raises:
            ValueError: If tenant_id is empty
        """
        if not isinstance(tenant_id, str):
            raise TypeError("tenant_id must be a string")

        if not tenant_id.strip():
            raise ValueError("tenant_id cannot be empty")

        self.tenant_id = tenant_id
        logger.debug(f"TenantContext created for tenant: {tenant_id}")

    def __repr__(self) -> str:
        """String representation"""
        return f"TenantContext(tenant_id={self.tenant_id})"


class MultiTenantPermissionLoader:
    """Multi-tenant permission loader wrapper"""

    def __init__(self, base_loader: PermissionLoader):
        """Initialize multi-tenant loader

        Args:
            base_loader: Base permission loader

        Raises:
            TypeError: If base_loader is invalid
        """
        if not hasattr(base_loader, "load_permissions"):
            raise TypeError("base_loader must have load_permissions method")

        self.base_loader = base_loader
        self._tenant_context: Optional[TenantContext] = None

        logger.debug("MultiTenantPermissionLoader initialized")

    def set_tenant(self, tenant_id: str) -> None:
        """Set current tenant

        Args:
            tenant_id: Tenant ID

        Raises:
            ValueError: If tenant_id is invalid
        """
        self._tenant_context = TenantContext(tenant_id)
        logger.debug(f"Tenant set to: {tenant_id}")

    def get_tenant(self) -> Optional[str]:
        """Get current tenant

        Returns:
            Tenant ID or None
        """
        return self._tenant_context.tenant_id if self._tenant_context else None

    async def load_permissions(self, user_id: str) -> List[str]:
        """Load permissions for user in current tenant

        Args:
            user_id: User ID

        Returns:
            List of permissions

        Raises:
            ValueError: If tenant not set
        """
        if not self._tenant_context:
            raise ValueError("Tenant context not set")

        # In real implementation, filter permissions by tenant
        permissions = await self.base_loader.load_permissions(user_id)

        logger.debug(
            f"Loaded {len(permissions)} permissions for user {user_id} "
            f"in tenant {self._tenant_context.tenant_id}"
        )

        return permissions

    def clear_tenant(self) -> None:
        """Clear tenant context"""
        self._tenant_context = None
        logger.debug("Tenant context cleared")


class MultiTenantResourceChecker:
    """Multi-tenant resource checker wrapper"""

    def __init__(self, base_checker: ResourcePermissionChecker):
        """Initialize multi-tenant checker

        Args:
            base_checker: Base resource checker

        Raises:
            TypeError: If base_checker is invalid
        """
        if not hasattr(base_checker, "check_permission"):
            raise TypeError("base_checker must have check_permission method")

        self.base_checker = base_checker
        self._tenant_context: Optional[TenantContext] = None

        logger.debug("MultiTenantResourceChecker initialized")

    def set_tenant(self, tenant_id: str) -> None:
        """Set current tenant

        Args:
            tenant_id: Tenant ID

        Raises:
            ValueError: If tenant_id is invalid
        """
        self._tenant_context = TenantContext(tenant_id)
        logger.debug(f"Tenant set to: {tenant_id}")

    def get_tenant(self) -> Optional[str]:
        """Get current tenant

        Returns:
            Tenant ID or None
        """
        return self._tenant_context.tenant_id if self._tenant_context else None

    async def check_owner(self, user_id: str, resource_id: str) -> bool:
        """Check if user owns resource in current tenant

        Args:
            user_id: User ID
            resource_id: Resource ID

        Returns:
            True if user owns resource, False otherwise

        Raises:
            ValueError: If tenant not set
        """
        if not self._tenant_context:
            raise ValueError("Tenant context not set")

        # In real implementation, check ownership within tenant
        is_owner = await self.base_checker.check_owner(user_id, resource_id)

        logger.debug(
            f"Checked ownership for user {user_id} on resource {resource_id} "
            f"in tenant {self._tenant_context.tenant_id}: {is_owner}"
        )

        return is_owner

    async def check_permission(
        self,
        user_id: str,
        resource_id: str,
        permission: str,
    ) -> bool:
        """Check if user has permission on resource in current tenant

        Args:
            user_id: User ID
            resource_id: Resource ID
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise

        Raises:
            ValueError: If tenant not set
        """
        if not self._tenant_context:
            raise ValueError("Tenant context not set")

        # In real implementation, check permission within tenant
        has_permission = await self.base_checker.check_permission(
            user_id, resource_id, permission
        )

        logger.debug(
            f"Checked permission {permission} for user {user_id} on resource {resource_id} "
            f"in tenant {self._tenant_context.tenant_id}: {has_permission}"
        )

        return has_permission

    def clear_tenant(self) -> None:
        """Clear tenant context"""
        self._tenant_context = None
        logger.debug("Tenant context cleared")


class TenantIsolationMiddleware:
    """Middleware for tenant isolation"""

    def __init__(self, app, tenant_header: str = "X-Tenant-ID"):
        """Initialize middleware

        Args:
            app: FastAPI app
            tenant_header: Header name for tenant ID
        """
        self.app = app
        self.tenant_header = tenant_header
        self.multi_tenant_loaders: List[MultiTenantPermissionLoader] = []
        self.multi_tenant_checkers: List[MultiTenantResourceChecker] = []

        logger.debug(f"TenantIsolationMiddleware initialized with header: {tenant_header}")

    def register_loader(self, loader: MultiTenantPermissionLoader) -> None:
        """Register multi-tenant loader

        Args:
            loader: Multi-tenant loader
        """
        self.multi_tenant_loaders.append(loader)

    def register_checker(self, checker: MultiTenantResourceChecker) -> None:
        """Register multi-tenant checker

        Args:
            checker: Multi-tenant checker
        """
        self.multi_tenant_checkers.append(checker)

    async def __call__(self, scope, receive, send):
        """ASGI middleware"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract tenant ID from header
        headers = dict(scope.get("headers", []))
        tenant_id = headers.get(self.tenant_header.lower().encode(), b"").decode()

        if tenant_id:
            # Set tenant for all registered loaders and checkers
            for loader in self.multi_tenant_loaders:
                loader.set_tenant(tenant_id)

            for checker in self.multi_tenant_checkers:
                checker.set_tenant(tenant_id)

            logger.debug(f"Tenant set from header: {tenant_id}")

        await self.app(scope, receive, send)
