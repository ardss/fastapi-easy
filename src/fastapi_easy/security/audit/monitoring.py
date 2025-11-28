"""Performance monitoring for security module"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PermissionCheckMetrics:
    """Metrics for permission checks"""

    def __init__(self):
        """Initialize metrics"""
        self.total_checks = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.error_checks = 0
        self.total_duration = 0.0
        self.min_duration = float("inf")
        self.max_duration = 0.0
        self.cache_hits = 0
        self.cache_misses = 0

    def record_check(
        self,
        duration: float,
        success: bool,
        error: bool = False,
        cache_hit: bool = False,
    ) -> None:
        """Record a permission check

        Args:
            duration: Check duration in seconds
            success: Whether check was successful
            error: Whether an error occurred
            cache_hit: Whether result came from cache
        """
        self.total_checks += 1
        self.total_duration += duration
        self.min_duration = min(self.min_duration, duration)
        self.max_duration = max(self.max_duration, duration)

        if error:
            self.error_checks += 1
        elif success:
            self.successful_checks += 1
        else:
            self.failed_checks += 1

        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get metrics statistics

        Returns:
            Dictionary with metrics
        """
        avg_duration = (
            self.total_duration / self.total_checks if self.total_checks > 0 else 0
        )
        cache_hit_rate = (
            self.cache_hits / (self.cache_hits + self.cache_misses) * 100
            if (self.cache_hits + self.cache_misses) > 0
            else 0
        )

        return {
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "failed_checks": self.failed_checks,
            "error_checks": self.error_checks,
            "total_duration": f"{self.total_duration:.4f}s",
            "avg_duration": f"{avg_duration:.6f}s",
            "min_duration": f"{self.min_duration:.6f}s" if self.min_duration != float("inf") else "N/A",
            "max_duration": f"{self.max_duration:.6f}s",
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": f"{cache_hit_rate:.2f}%",
        }

    def reset(self) -> None:
        """Reset metrics"""
        self.total_checks = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.error_checks = 0
        self.total_duration = 0.0
        self.min_duration = float("inf")
        self.max_duration = 0.0
        self.cache_hits = 0
        self.cache_misses = 0


class MonitoredPermissionEngine:
    """Permission engine with performance monitoring"""

    def __init__(self, base_engine):
        """Initialize monitored permission engine

        Args:
            base_engine: Base permission engine to wrap
        """
        self.base_engine = base_engine
        self.metrics = PermissionCheckMetrics()

        logger.debug("MonitoredPermissionEngine initialized")

    async def check_permission(
        self, user_id: str, permission: str, resource_id: Optional[str] = None
    ) -> bool:
        """Check permission with monitoring

        Args:
            user_id: User ID
            permission: Permission to check
            resource_id: Resource ID (optional)

        Returns:
            True if user has permission
        """
        start = time.time()
        cache_hit = False
        success = False
        error = False

        try:
            # Check if result is from cache
            # This is a heuristic - we check if the permission loader has cache stats
            if hasattr(self.base_engine, "permission_loader"):
                loader = self.base_engine.permission_loader
                if hasattr(loader, "cache"):
                    # Get current cache state before check
                    cache_size_before = len(loader.cache.cache) if hasattr(loader.cache, "cache") else 0

            result = await self.base_engine.check_permission(
                user_id, permission, resource_id
            )

            # Check if result is from cache
            if hasattr(self.base_engine, "permission_loader"):
                loader = self.base_engine.permission_loader
                if hasattr(loader, "cache"):
                    cache_size_after = len(loader.cache.cache) if hasattr(loader.cache, "cache") else 0
                    cache_hit = cache_size_after == cache_size_before

            success = True
            return result

        except Exception as e:
            error = True
            logger.error(f"Error checking permission: {e}")
            raise

        finally:
            duration = time.time() - start
            self.metrics.record_check(
                duration=duration,
                success=success,
                error=error,
                cache_hit=cache_hit,
            )
            logger.debug(
                f"Permission check for {user_id}/{permission}: {duration:.6f}s, "
                f"cache_hit={cache_hit}, success={success}"
            )

    async def check_all_permissions(
        self, user_id: str, permissions: list
    ) -> bool:
        """Check all permissions with monitoring

        Args:
            user_id: User ID
            permissions: List of permissions to check

        Returns:
            True if user has all permissions
        """
        start = time.time()
        error = False

        try:
            result = await self.base_engine.check_all_permissions(
                user_id, permissions
            )
            return result

        except Exception as e:
            error = True
            logger.error(f"Error checking all permissions: {e}")
            raise

        finally:
            duration = time.time() - start
            self.metrics.record_check(
                duration=duration,
                success=not error,
                error=error,
                cache_hit=False,
            )

    async def check_any_permission(
        self, user_id: str, permissions: list
    ) -> bool:
        """Check any permission with monitoring

        Args:
            user_id: User ID
            permissions: List of permissions to check

        Returns:
            True if user has any permission
        """
        start = time.time()
        error = False

        try:
            result = await self.base_engine.check_any_permission(
                user_id, permissions
            )
            return result

        except Exception as e:
            error = True
            logger.error(f"Error checking any permission: {e}")
            raise

        finally:
            duration = time.time() - start
            self.metrics.record_check(
                duration=duration,
                success=not error,
                error=error,
                cache_hit=False,
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics

        Returns:
            Dictionary with metrics
        """
        return self.metrics.get_stats()

    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self.metrics.reset()
        logger.debug("Performance metrics reset")
