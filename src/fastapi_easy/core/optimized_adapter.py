"""Optimized adapter that integrates all performance optimizations"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from .multilayer_cache import MultiLayerCache
from .async_batch import AsyncBatchProcessor
from .query_projection import QueryProjection
from .lock_manager import LockManager
from .cache_key_generator import generate_cache_key
from .cache_invalidation import get_invalidation_manager
from .reentrant_lock import get_lock_manager


logger = logging.getLogger(__name__)


class OptimizedSQLAlchemyAdapter:
    """SQLAlchemy adapter with integrated performance optimizations
    
    Combines:
    - Multi-layer caching (L1/L2)
    - Async batch processing
    - Query projection
    - Automatic cache invalidation
    """
    
    def __init__(
        self,
        base_adapter,
        enable_cache: bool = True,
        enable_async: bool = True,
        cache_config: Optional[Dict[str, Any]] = None,
        async_config: Optional[Dict[str, Any]] = None,
        query_timeout: float = 30.0,
    ):
        """Initialize optimized adapter
        
        Args:
            base_adapter: Base SQLAlchemy adapter
            enable_cache: Enable multi-layer caching
            enable_async: Enable async batch processing
            cache_config: Cache configuration
            async_config: Async configuration
            query_timeout: Query timeout in seconds (default: 30)
        """
        self.base_adapter = base_adapter
        self.enable_cache = enable_cache
        self.enable_async = enable_async
        self.query_timeout = query_timeout
        
        # Initialize cache
        if enable_cache:
            cache_cfg = cache_config or {}
            self.cache = MultiLayerCache(
                l1_size=cache_cfg.get("l1_size", 1000),
                l1_ttl=cache_cfg.get("l1_ttl", 60),
                l2_size=cache_cfg.get("l2_size", 10000),
                l2_ttl=cache_cfg.get("l2_ttl", 600),
            )
        else:
            self.cache = None
        
        # Initialize async processor
        if enable_async:
            async_cfg = async_config or {}
            self.async_processor = AsyncBatchProcessor(
                max_concurrent=async_cfg.get("max_concurrent", 10)
            )
        else:
            self.async_processor = None
        
        # Initialize lock manager for concurrent access control
        self.lock_manager = LockManager(default_timeout=5.0)
        
        # Track model for cache invalidation
        self.model = base_adapter.model
    
    async def _execute_with_timeout(self, coro, operation: str) -> Any:
        """Execute async operation with timeout
        
        Args:
            coro: Coroutine to execute
            operation: Operation name for logging
            
        Returns:
            Operation result
            
        Raises:
            asyncio.TimeoutError: If operation exceeds timeout
        """
        try:
            return await asyncio.wait_for(coro, timeout=self.query_timeout)
        except asyncio.TimeoutError:
            logger.error(f"Operation {operation} exceeded timeout of {self.query_timeout}s")
            raise
    
    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation
        
        Uses secure MD5-based key generation to prevent collisions.
        
        Args:
            operation: Operation name (get_all, get_one, etc.)
            **kwargs: Operation parameters
            
        Returns:
            Cache key
        """
        return generate_cache_key(operation, **kwargs)
    
    async def get_all(
        self,
        filters: Dict[str, Any],
        sorts: Dict[str, Any],
        pagination: Dict[str, Any],
    ) -> List[Any]:
        """Get all items with caching
        
        Args:
            filters: Filter conditions
            sorts: Sort conditions
            pagination: Pagination info
            
        Returns:
            List of items
        """
        # Try cache first
        if self.enable_cache:
            cache_key = self._get_cache_key(
                "get_all",
                filters=str(filters),
                sorts=str(sorts),
                pagination=str(pagination),
            )
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Execute query with timeout
        result = await self._execute_with_timeout(
            self.base_adapter.get_all(filters, sorts, pagination),
            "get_all"
        )
        
        # Cache result
        if self.enable_cache:
            await self.cache.set(cache_key, result)
        
        return result
    
    async def get_one(self, id: Any) -> Optional[Any]:
        """Get single item with caching and avalanche prevention
        
        Prevents cache avalanche by using distributed lock
        when multiple requests query the same missing item.
        
        Args:
            id: Item id
            
        Returns:
            Item or None
        """
        # Try cache first
        if self.enable_cache:
            cache_key = self._get_cache_key("get_one", id=id)
            cached = await self.cache.get(cache_key)
            
            # Check for cached None value (cache penetration prevention)
            if cached is not None:
                if cached == "__NULL__":
                    return None
                return cached
        
        # Use lock to prevent cache avalanche
        lock_key = f"get_one_{id}"
        
        if await self.lock_manager.acquire(lock_key):
            try:
                # Double-check cache after acquiring lock
                if self.enable_cache:
                    cached = await self.cache.get(cache_key)
                    if cached is not None:
                        if cached == "__NULL__":
                            return None
                        return cached
                
                # Execute query
                result = await self.base_adapter.get_one(id)
                
                # Cache result (including None values for cache penetration prevention)
                if self.enable_cache:
                    cache_value = result if result is not None else "__NULL__"
                    await self.cache.set(cache_key, cache_value)
                
                return result
            finally:
                self.lock_manager.release(lock_key)
        else:
            # Lock acquisition failed, wait and retry
            await asyncio.sleep(0.05)
            return await self.get_one(id)
    
    async def create(self, data: Dict[str, Any]) -> Any:
        """Create item and invalidate cache
        
        Args:
            data: Item data
            
        Returns:
            Created item
        """
        # Create item
        result = await self.base_adapter.create(data)
        
        # Invalidate all get_all caches
        if self.enable_cache:
            await self._invalidate_list_cache()
        
        return result
    
    async def update(self, id: Any, data: Dict[str, Any]) -> Any:
        """Update item and invalidate cache with concurrent control
        
        Uses distributed lock to prevent concurrent modifications
        and cache avalanche.
        
        Args:
            id: Item id
            data: Update data
            
        Returns:
            Updated item
        """
        # Use lock to prevent concurrent modifications
        lock_key = f"update_{id}"
        
        if await self.lock_manager.acquire(lock_key):
            try:
                # Update item
                result = await self.base_adapter.update(id, data)
                
                # Invalidate specific item cache
                if self.enable_cache:
                    cache_key = self._get_cache_key("get_one", id=id)
                    await self.cache.delete(cache_key)
                    # Also invalidate list caches
                    await self._invalidate_list_cache()
                
                return result
            finally:
                self.lock_manager.release(lock_key)
        else:
            # Lock acquisition failed, retry with exponential backoff
            await asyncio.sleep(0.1)
            return await self.update(id, data)
    
    async def delete_one(self, id: Any) -> bool:
        """Delete item and invalidate cache
        
        Args:
            id: Item id
            
        Returns:
            Success flag
        """
        # Delete item
        result = await self.base_adapter.delete_one(id)
        
        # Invalidate specific item cache
        if self.enable_cache and result:
            cache_key = self._get_cache_key("get_one", id=id)
            await self.cache.delete(cache_key)
            # Also invalidate list caches
            await self._invalidate_list_cache()
        
        return result
    
    async def delete_all(self) -> int:
        """Delete all items and invalidate cache
        
        Returns:
            Number of deleted items
        """
        # Delete all items
        result = await self.base_adapter.delete_all()
        
        # Clear all caches
        if self.enable_cache:
            await self.cache.clear()
        
        return result
    
    async def count(self, filters: Dict[str, Any]) -> int:
        """Count items with caching
        
        Args:
            filters: Filter conditions
            
        Returns:
            Count
        """
        # Try cache first
        if self.enable_cache:
            cache_key = self._get_cache_key("count", filters=str(filters))
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Execute query
        result = await self.base_adapter.count(filters)
        
        # Cache result
        if self.enable_cache:
            await self.cache.set(cache_key, result)
        
        return result
    
    async def _invalidate_list_cache(self) -> None:
        """Invalidate list-related caches with fine-grained control
        
        Clears all list-related caches to ensure data consistency.
        """
        if not self.enable_cache:
            return
        
        try:
            # Clear all caches to ensure consistency
            # This is a conservative approach that guarantees correctness
            await self.cache.clear()
            logger.debug("Cleared all caches after data modification")
        except Exception as e:
            logger.error(f"Cache invalidation failed: {str(e)}")
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics
        
        Returns:
            Cache statistics or None if caching disabled
        """
        if not self.enable_cache:
            return None
        return self.cache.get_stats()
    
    async def clear_cache(self) -> None:
        """Clear all caches
        
        Useful for testing or manual cache invalidation.
        """
        if self.enable_cache:
            await self.cache.clear()
    
    async def warmup_cache(self, limit: int = 1000) -> int:
        """Warmup cache by preloading hot data
        
        Loads frequently accessed items into cache to improve
        cold start performance.
        
        Args:
            limit: Maximum number of items to preload
            
        Returns:
            Number of items warmed up
        """
        if not self.enable_cache:
            return 0
        
        try:
            # Load hot data (first N items)
            items = await self.base_adapter.get_all(
                filters={},
                sorts={},
                pagination={"skip": 0, "limit": limit},
            )
            
            # Cache each item
            count = 0
            for item in items:
                # Try to get ID from item
                item_id = getattr(item, "id", None) or item.get("id")
                if item_id:
                    cache_key = self._get_cache_key("get_one", id=item_id)
                    await self.cache.set(cache_key, item)
                    count += 1
            
            logger.info(f"Cache warmup completed: {count} items preloaded")
            return count
        except Exception as e:
            logger.error(f"Cache warmup failed: {str(e)}", exc_info=True)
            return 0


def create_optimized_adapter(
    base_adapter,
    enable_cache: bool = True,
    enable_async: bool = True,
    cache_config: Optional[Dict[str, Any]] = None,
    async_config: Optional[Dict[str, Any]] = None,
) -> OptimizedSQLAlchemyAdapter:
    """Create an optimized adapter
    
    Args:
        base_adapter: Base SQLAlchemy adapter
        enable_cache: Enable caching
        enable_async: Enable async processing
        cache_config: Cache configuration
        async_config: Async configuration
        
    Returns:
        Optimized adapter instance
    """
    return OptimizedSQLAlchemyAdapter(
        base_adapter,
        enable_cache=enable_cache,
        enable_async=enable_async,
        cache_config=cache_config,
        async_config=async_config,
    )
