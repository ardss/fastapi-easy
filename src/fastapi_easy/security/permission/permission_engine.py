"""Permission checking engine"""

from __future__ import annotations

import logging
from typing import List, Optional

from .permission_loader import CachedPermissionLoader, PermissionLoader
from .resource_checker import CachedResourceChecker, ResourcePermissionChecker

logger = logging.getLogger(__name__)


class PermissionEngine:
    """Permission checking engine for unified permission management"""

    def __init__(
        self,
        permission_loader: PermissionLoader,
        resource_checker: Optional[ResourcePermissionChecker] = None,
        enable_cache: bool = True,
        cache_ttl: int = 300,
    ):
        """Initialize permission engine

        Args:
            permission_loader: Permission loader
            resource_checker: Resource permission checker (optional)
            enable_cache: Enable caching (default: True)
            cache_ttl: Cache TTL in seconds (default: 300)

        Raises:
            TypeError: If parameters have invalid types
        """
        if not hasattr(permission_loader, "load_permissions"):
            raise TypeError("permission_loader must have load_permissions method")

        if resource_checker and not hasattr(resource_checker, "check_permission"):
            raise TypeError("resource_checker must have check_permission method")

        # Wrap with cache if enabled
        if enable_cache:
            self.permission_loader = CachedPermissionLoader(permission_loader, cache_ttl=cache_ttl)
        else:
            self.permission_loader = permission_loader

        # Wrap resource checker with cache if enabled
        if resource_checker and enable_cache:
            self.resource_checker = CachedResourceChecker(resource_checker, cache_ttl=cache_ttl)
        else:
            self.resource_checker = resource_checker

        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl

        logger.debug(f"PermissionEngine initialized (cache={enable_cache}, ttl={cache_ttl}s)")

    async def check_permission(
        self,
        user_id: str,
        permission: str,
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if user has permission

        Args:
            user_id: User ID
            permission: Permission to check
            resource_id: Resource ID (optional, for resource-level permission check)

        Returns:
            True if user has permission, False otherwise

        Raises:
            TypeError: If parameters have invalid types
            ValueError: If parameters are invalid
        """
        if not isinstance(user_id, str):
            raise TypeError("user_id must be a string")

        if not isinstance(permission, str):
            raise TypeError("permission must be a string")

        if not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if not permission.strip():
            raise ValueError("permission cannot be empty")

        # Load user permissions
        permissions = await self.permission_loader.load_permissions(user_id)

        # Check basic permission
        if permission in permissions:
            logger.debug(f"User {user_id} has permission {permission}")
            return True

        # Check resource permission if needed
        if resource_id and self.resource_checker:
            if not isinstance(resource_id, str):
                raise TypeError("resource_id must be a string")

            if not resource_id.strip():
                raise ValueError("resource_id cannot be empty")

            has_permission = await self.resource_checker.check_permission(
                user_id, resource_id, permission
            )

            if has_permission:
                logger.debug(
                    f"User {user_id} has permission {permission} on resource {resource_id}"
                )
            else:
                logger.debug(
                    f"User {user_id} does not have permission {permission} on resource {resource_id}"
                )

            return has_permission

        logger.debug(f"User {user_id} does not have permission {permission}")
        return False

    async def check_all_permissions(
        self,
        user_id: str,
        permissions: List[str],
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if user has all permissions

        Args:
            user_id: User ID
            permissions: List of permissions to check
            resource_id: Resource ID (optional)

        Returns:
            True if user has all permissions, False otherwise

        Raises:
            TypeError: If parameters have invalid types
        """
        if not isinstance(permissions, list):
            raise TypeError("permissions must be a list")

        for permission in permissions:
            if not isinstance(permission, str):
                raise TypeError("All permissions must be strings")

            has_permission = await self.check_permission(user_id, permission, resource_id)
            if not has_permission:
                return False

        return True

    async def check_any_permission(
        self,
        user_id: str,
        permissions: List[str],
        resource_id: Optional[str] = None,
    ) -> bool:
        """Check if user has any permission

        Args:
            user_id: User ID
            permissions: List of permissions to check
            resource_id: Resource ID (optional)

        Returns:
            True if user has any permission, False otherwise

        Raises:
            TypeError: If parameters have invalid types
        """
        if not isinstance(permissions, list):
            raise TypeError("permissions must be a list")

        for permission in permissions:
            if not isinstance(permission, str):
                raise TypeError("All permissions must be strings")

            has_permission = await self.check_permission(user_id, permission, resource_id)
            if has_permission:
                return True

        return False

    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear permission cache

        Args:
            user_id: User ID to clear (None to clear all)
        """
        if hasattr(self.permission_loader, "clear_cache"):
            self.permission_loader.clear_cache(user_id)
            logger.debug(f"Cleared permission cache for user {user_id}")

        if self.resource_checker and hasattr(self.resource_checker, "clear_cache"):
            pattern = f"*{user_id}*" if user_id else None
            self.resource_checker.clear_cache(pattern)
            logger.debug(f"Cleared resource cache for user {user_id}")

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"PermissionEngine("
            f"permission_loader={self.permission_loader.__class__.__name__}, "
            f"resource_checker={self.resource_checker.__class__.__name__ if self.resource_checker else None}, "
            f"cache={self.enable_cache}, "
            f"ttl={self.cache_ttl}s"
            f")"
        )
