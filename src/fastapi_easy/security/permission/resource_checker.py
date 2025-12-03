"""Resource-level permission checking"""

import logging
from typing import Any, Callable, Optional, Protocol

logger = logging.getLogger(__name__)


class ResourcePermissionChecker(Protocol):
    """Protocol for checking resource-level permissions"""

    async def check_owner(self, user_id: str, resource_id: str) -> bool:
        """Check if user owns the resource

        Args:
            user_id: User ID
            resource_id: Resource ID

        Returns:
            True if user owns resource
        """
        ...

    async def check_permission(self, user_id: str, resource_id: str, permission: str) -> bool:
        """Check if user has permission on resource

        Args:
            user_id: User ID
            resource_id: Resource ID
            permission: Permission to check

        Returns:
            True if user has permission
        """
        ...


class StaticResourceChecker:
    """Check resource permissions from static configuration"""

    def __init__(self, resources_map: dict):
        """Initialize static resource checker

        Args:
            resources_map: Dict mapping resource_id to owner_id and permissions
        """
        if not isinstance(resources_map, dict):
            raise TypeError("resources_map must be a dict")

        self.resources_map = resources_map
        logger.debug(f"StaticResourceChecker initialized with {len(resources_map)} resources")

    async def check_owner(self, user_id: str, resource_id: str) -> bool:
        """Check if user owns the resource

        Args:
            user_id: User ID
            resource_id: Resource ID

        Returns:
            True if user owns resource
        """
        if not isinstance(user_id, str) or not isinstance(resource_id, str):
            raise TypeError("user_id and resource_id must be strings")

        resource = self.resources_map.get(resource_id)
        if not resource:
            logger.warning(f"Resource {resource_id} not found")
            return False

        owner_id = resource.get("owner_id")
        is_owner = owner_id == user_id

        logger.debug(f"Owner check for user {user_id} on resource {resource_id}: {is_owner}")

        return is_owner

    async def check_permission(self, user_id: str, resource_id: str, permission: str) -> bool:
        """Check if user has permission on resource

        Args:
            user_id: User ID
            resource_id: Resource ID
            permission: Permission to check

        Returns:
            True if user has permission
        """
        if not isinstance(user_id, str) or not isinstance(resource_id, str):
            raise TypeError("user_id and resource_id must be strings")

        if not isinstance(permission, str):
            raise TypeError("permission must be a string")

        # Check owner first
        is_owner = await self.check_owner(user_id, resource_id)
        if is_owner:
            logger.debug(f"User {user_id} is owner of resource {resource_id}")
            return True

        # Check explicit permissions
        resource = self.resources_map.get(resource_id)
        if not resource:
            return False

        permissions = resource.get("permissions", {})
        user_permissions = permissions.get(user_id, [])

        has_permission = permission in user_permissions

        logger.debug(
            f"Permission check for user {user_id} on resource {resource_id}: {has_permission}"
        )

        return has_permission


class DatabaseResourceChecker:
    """Check resource permissions from database (placeholder)"""

    def __init__(self, db_session=None):
        """Initialize database resource checker

        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session
        logger.debug("DatabaseResourceChecker initialized")

    async def check_owner(self, user_id: str, resource_id: str) -> bool:
        """Check if user owns the resource

        Args:
            user_id: User ID
            resource_id: Resource ID

        Returns:
            True if user owns resource
        """
        if not isinstance(user_id, str) or not isinstance(resource_id, str):
            raise TypeError("user_id and resource_id must be strings")

        # Placeholder: In real implementation, query database
        logger.debug(f"Checking owner in database for user {user_id} on resource {resource_id}")

        return False

    async def check_permission(self, user_id: str, resource_id: str, permission: str) -> bool:
        """Check if user has permission on resource

        Args:
            user_id: User ID
            resource_id: Resource ID
            permission: Permission to check

        Returns:
            True if user has permission
        """
        if not isinstance(user_id, str) or not isinstance(resource_id, str):
            raise TypeError("user_id and resource_id must be strings")

        if not isinstance(permission, str):
            raise TypeError("permission must be a string")

        # Placeholder: In real implementation, query database
        logger.debug(
            f"Checking permission in database for user {user_id} on resource {resource_id}"
        )

        return False


class CachedResourceChecker:
    """Wrap resource checker with caching"""

    def __init__(self, base_checker: ResourcePermissionChecker, cache_ttl: int = 300):
        """Initialize cached resource checker

        Args:
            base_checker: Base resource checker
            cache_ttl: Cache TTL in seconds
        """
        if not hasattr(base_checker, "check_owner") or not hasattr(
            base_checker, "check_permission"
        ):
            raise TypeError("base_checker must have check_owner and check_permission methods")

        self.base_checker = base_checker
        self.cache_ttl = cache_ttl
        self.cache: dict = {}
        self.cache_times: dict = {}
        self.hits = 0
        self.misses = 0

        logger.debug(f"CachedResourceChecker initialized with TTL {cache_ttl}s")

    async def check_owner(self, user_id: str, resource_id: str) -> bool:
        """Check if user owns the resource with caching

        Args:
            user_id: User ID
            resource_id: Resource ID

        Returns:
            True if user owns resource
        """
        import time

        if not isinstance(user_id, str) or not isinstance(resource_id, str):
            raise TypeError("user_id and resource_id must be strings")

        cache_key = f"owner:{user_id}:{resource_id}"
        now = time.time()

        # Check cache
        if cache_key in self.cache:
            cache_time = self.cache_times.get(cache_key, 0)
            if now - cache_time < self.cache_ttl:
                self.hits += 1
                logger.debug(f"Cache hit for {cache_key}")
                return self.cache[cache_key]

        # Check with base checker
        self.misses += 1
        result = await self.base_checker.check_owner(user_id, resource_id)

        # Cache result
        self.cache[cache_key] = result
        self.cache_times[cache_key] = now

        return result

    async def check_permission(self, user_id: str, resource_id: str, permission: str) -> bool:
        """Check if user has permission on resource with caching

        Args:
            user_id: User ID
            resource_id: Resource ID
            permission: Permission to check

        Returns:
            True if user has permission
        """
        import time

        if not isinstance(user_id, str) or not isinstance(resource_id, str):
            raise TypeError("user_id and resource_id must be strings")

        if not isinstance(permission, str):
            raise TypeError("permission must be a string")

        cache_key = f"perm:{user_id}:{resource_id}:{permission}"
        now = time.time()

        # Check cache
        if cache_key in self.cache:
            cache_time = self.cache_times.get(cache_key, 0)
            if now - cache_time < self.cache_ttl:
                self.hits += 1
                logger.debug(f"Cache hit for {cache_key}")
                return self.cache[cache_key]

        # Check with base checker
        self.misses += 1
        result = await self.base_checker.check_permission(user_id, resource_id, permission)

        # Cache result
        self.cache[cache_key] = result
        self.cache_times[cache_key] = now

        return result

    def get_cache_stats(self) -> dict:
        """Get cache statistics

        Returns:
            Dictionary with cache statistics
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            "size": len(self.cache),
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate": f"{hit_rate:.2f}%",
        }

    def clear_cache(self, pattern: Optional[str] = None) -> None:
        """Clear cache

        Args:
            pattern: Cache key pattern to clear (None to clear all)
        """
        if pattern is None:
            self.cache.clear()
            self.cache_times.clear()
            logger.debug("Cleared all resource cache")
        else:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for key in keys_to_delete:
                self.cache.pop(key, None)
                self.cache_times.pop(key, None)
            logger.debug(f"Cleared {len(keys_to_delete)} cache entries matching {pattern}")
