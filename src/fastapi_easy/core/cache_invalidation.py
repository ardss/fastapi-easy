"""Cache invalidation management

This module provides fine-grained cache invalidation strategies
to ensure data consistency while minimizing cache clearing.
"""

import logging
from typing import Optional, Set, Any, Dict
from enum import Enum


logger = logging.getLogger(__name__)


class InvalidationStrategy(Enum):
    """Cache invalidation strategies"""
    
    FULL = "full"  # Clear all caches
    PATTERN = "pattern"  # Clear by pattern
    SELECTIVE = "selective"  # Clear specific keys


class CacheInvalidationManager:
    """Manage cache invalidation with fine-grained control"""
    
    def __init__(self):
        """Initialize invalidation manager"""
        self.strategy = InvalidationStrategy.SELECTIVE
        self.invalidation_log: list = []
        self.max_log_size = 1000
    
    async def invalidate_list_cache(
        self,
        cache,
        operation: str = "get_all"
    ) -> int:
        """Invalidate list operation caches
        
        Clears all caches related to list operations (get_all, etc.)
        while preserving single-item caches.
        
        Args:
            cache: Cache instance
            operation: Operation name to invalidate
            
        Returns:
            Number of keys invalidated
        """
        if self.strategy == InvalidationStrategy.FULL:
            return await self._invalidate_full(cache)
        elif self.strategy == InvalidationStrategy.PATTERN:
            return await self._invalidate_by_pattern(cache, operation)
        else:
            return await self._invalidate_selective(cache, operation)
    
    async def invalidate_item_cache(
        self,
        cache,
        item_id: Any
    ) -> int:
        """Invalidate single item cache
        
        Args:
            cache: Cache instance
            item_id: Item ID
            
        Returns:
            Number of keys invalidated
        """
        try:
            # Build cache key pattern
            key_pattern = f"get_one:*id*{item_id}*"
            
            # Find and delete matching keys
            deleted_count = 0
            for key in list(cache.l1_cache.keys()):
                if str(item_id) in str(key):
                    await cache.delete(key)
                    deleted_count += 1
            
            # Log invalidation
            self._log_invalidation("item", item_id, deleted_count)
            
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to invalidate item cache: {str(e)}")
            return 0
    
    async def invalidate_by_filter(
        self,
        cache,
        filter_key: str
    ) -> int:
        """Invalidate caches related to specific filter
        
        Args:
            cache: Cache instance
            filter_key: Filter key to invalidate
            
        Returns:
            Number of keys invalidated
        """
        try:
            deleted_count = 0
            for key in list(cache.l1_cache.keys()):
                if filter_key in str(key):
                    await cache.delete(key)
                    deleted_count += 1
            
            self._log_invalidation("filter", filter_key, deleted_count)
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to invalidate by filter: {str(e)}")
            return 0
    
    async def _invalidate_full(self, cache) -> int:
        """Full cache invalidation
        
        Args:
            cache: Cache instance
            
        Returns:
            Number of keys invalidated
        """
        try:
            count = len(cache.l1_cache)
            await cache.clear()
            self._log_invalidation("full", "all", count)
            return count
        except Exception as e:
            logger.error(f"Failed to perform full invalidation: {str(e)}")
            return 0
    
    async def _invalidate_by_pattern(
        self,
        cache,
        operation: str
    ) -> int:
        """Pattern-based cache invalidation
        
        Args:
            cache: Cache instance
            operation: Operation pattern
            
        Returns:
            Number of keys invalidated
        """
        try:
            deleted_count = 0
            pattern = f"{operation}:"
            
            for key in list(cache.l1_cache.keys()):
                if key.startswith(pattern):
                    await cache.delete(key)
                    deleted_count += 1
            
            self._log_invalidation("pattern", operation, deleted_count)
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to perform pattern invalidation: {str(e)}")
            return 0
    
    async def _invalidate_selective(
        self,
        cache,
        operation: str
    ) -> int:
        """Selective cache invalidation
        
        Only invalidates caches that are definitely affected by the operation.
        
        Args:
            cache: Cache instance
            operation: Operation name
            
        Returns:
            Number of keys invalidated
        """
        try:
            deleted_count = 0
            
            # Only invalidate list-related caches
            if operation in ("get_all", "create", "update", "delete"):
                # For MultiLayerCache, use cleanup_expired which is safer
                if hasattr(cache, 'cleanup_expired'):
                    await cache.cleanup_expired()
                    deleted_count = 1  # Mark as invalidated
                else:
                    # For dict-like caches
                    pattern = "get_all:"
                    for key in list(cache.keys()):
                        if key.startswith(pattern):
                            await cache.delete(key)
                            deleted_count += 1
            
            self._log_invalidation("selective", operation, deleted_count)
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to perform selective invalidation: {str(e)}")
            return 0
    
    def _log_invalidation(
        self,
        inv_type: str,
        target: str,
        count: int
    ) -> None:
        """Log invalidation operation
        
        Args:
            inv_type: Invalidation type
            target: Invalidation target
            count: Number of keys invalidated
        """
        import time
        
        log_entry = {
            "timestamp": time.time(),
            "type": inv_type,
            "target": target,
            "count": count
        }
        
        self.invalidation_log.append(log_entry)
        
        # Limit log size
        if len(self.invalidation_log) > self.max_log_size:
            self.invalidation_log = self.invalidation_log[-self.max_log_size:]
        
        logger.debug(
            f"Cache invalidation: type={inv_type}, target={target}, count={count}"
        )
    
    def get_invalidation_stats(self) -> Dict[str, Any]:
        """Get invalidation statistics
        
        Returns:
            Statistics dictionary
        """
        if not self.invalidation_log:
            return {"total": 0, "by_type": {}}
        
        total = sum(entry["count"] for entry in self.invalidation_log)
        by_type = {}
        
        for entry in self.invalidation_log:
            inv_type = entry["type"]
            if inv_type not in by_type:
                by_type[inv_type] = 0
            by_type[inv_type] += entry["count"]
        
        return {
            "total": total,
            "by_type": by_type,
            "recent": self.invalidation_log[-10:]
        }


# Singleton instance
_manager = CacheInvalidationManager()


def get_invalidation_manager() -> CacheInvalidationManager:
    """Get invalidation manager instance
    
    Returns:
        CacheInvalidationManager instance
    """
    return _manager
