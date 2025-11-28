"""Permission loader interface and implementations"""

import logging
from typing import Any, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


class PermissionLoader(Protocol):
    """Protocol for loading user permissions"""

    async def load_permissions(self, user_id: str) -> List[str]:
        """Load permissions for a user

        Args:
            user_id: User ID

        Returns:
            List of permission strings

        Raises:
            ValueError: If user_id is invalid
        """
        ...


class StaticPermissionLoader:
    """Load permissions from static configuration"""

    def __init__(self, permissions_map: dict):
        """Initialize static permission loader

        Args:
            permissions_map: Dict mapping user_id to list of permissions
        """
        if not isinstance(permissions_map, dict):
            raise TypeError("permissions_map must be a dict")

        self.permissions_map = permissions_map
        logger.debug(f"StaticPermissionLoader initialized with {len(permissions_map)} users")

    async def load_permissions(self, user_id: str) -> List[str]:
        """Load permissions from static map

        Args:
            user_id: User ID

        Returns:
            List of permissions

        Raises:
            ValueError: If user_id is invalid
        """
        if not isinstance(user_id, str):
            raise TypeError("user_id must be a string")

        if not user_id.strip():
            raise ValueError("user_id cannot be empty")

        permissions = self.permissions_map.get(user_id, [])
        logger.debug(f"Loaded {len(permissions)} permissions for user {user_id}")

        return permissions


class DatabasePermissionLoader:
    """Load permissions from database (placeholder)"""

    def __init__(self, db_session=None):
        """Initialize database permission loader

        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session
        logger.debug("DatabasePermissionLoader initialized")

    async def load_permissions(self, user_id: str) -> List[str]:
        """Load permissions from database

        Args:
            user_id: User ID

        Returns:
            List of permissions

        Raises:
            ValueError: If user_id is invalid
        """
        if not isinstance(user_id, str):
            raise TypeError("user_id must be a string")

        if not user_id.strip():
            raise ValueError("user_id cannot be empty")

        # Placeholder: In real implementation, query database
        # For now, return empty list
        logger.debug(f"Loaded permissions for user {user_id} from database")

        return []


class CachedPermissionLoader:
    """Wrap permission loader with caching"""

    def __init__(self, base_loader: PermissionLoader, cache_ttl: int = 300):
        """Initialize cached permission loader

        Args:
            base_loader: Base permission loader
            cache_ttl: Cache TTL in seconds
        """
        if not hasattr(base_loader, "load_permissions"):
            raise TypeError("base_loader must have load_permissions method")

        self.base_loader = base_loader
        self.cache_ttl = cache_ttl
        self.cache: dict = {}
        self.cache_times: dict = {}
        self.hits = 0
        self.misses = 0

        logger.debug(f"CachedPermissionLoader initialized with TTL {cache_ttl}s")

    async def load_permissions(self, user_id: str) -> List[str]:
        """Load permissions with caching

        Args:
            user_id: User ID

        Returns:
            List of permissions
        """
        import time

        if not isinstance(user_id, str):
            raise TypeError("user_id must be a string")

        # Check cache
        now = time.time()
        if user_id in self.cache:
            cache_time = self.cache_times.get(user_id, 0)
            if now - cache_time < self.cache_ttl:
                self.hits += 1
                logger.debug(f"Cache hit for user {user_id}")
                return self.cache[user_id]

        # Load from base loader
        self.misses += 1
        permissions = await self.base_loader.load_permissions(user_id)

        # Cache result
        self.cache[user_id] = permissions
        self.cache_times[user_id] = now

        logger.debug(f"Cached permissions for user {user_id}")

        return permissions

    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear cache

        Args:
            user_id: User ID to clear (None to clear all)
        """
        if user_id is None:
            self.cache.clear()
            self.cache_times.clear()
            logger.debug("Cleared all permission cache")
        else:
            self.cache.pop(user_id, None)
            self.cache_times.pop(user_id, None)
            logger.debug(f"Cleared cache for user {user_id}")

    def get_cache_stats(self) -> Dict[str, Any]:
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
