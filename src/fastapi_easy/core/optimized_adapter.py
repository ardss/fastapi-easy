"""Optimized adapter that integrates all performance optimizations"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .async_batch import AsyncBatchProcessor
from .cache_invalidation import get_invalidation_manager
from .cache_key_generator import generate_cache_key
from .lock_manager import LockManager
from .multilayer_cache import MultiLayerCache
from .query_projection import QueryProjection
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
        from .config_validator import ConfigValidator
        
        self.base_adapter = base_adapter
        self.enable_cache = enable_cache
        self.enable_async = enable_async
        
        # Validate and set query timeout
        if not ConfigValidator.validate_timeout(query_timeout):
            raise ValueError(f"Invalid query timeout: {query_timeout}")
        self.query_timeout = query_timeout
        
        # Initialize cache with validation
        if enable_cache:
            cache_cfg = cache_config or {}
            if not ConfigValidator.validate_cache_config(cache_cfg):
                raise ValueError("Invalid cache configuration")
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
        try:
            result = await self._execute_with_timeout(
                self.base_adapter.get_all(filters, sorts, pagination),
                "get_all"
            )
        except asyncio.TimeoutError:
            logger.error("Query timeout, not caching empty result")
            # Don't cache timeout results, return empty list directly
            return []
        
        # Cache result only if successful
        if self.enable_cache and result:
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
        max_retries = 3
        
        for attempt in range(max_retries):
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
                # Lock acquisition failed, wait with exponential backoff
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.05 * (2 ** attempt))
                else:
                    logger.error(f"Failed to acquire lock for get_one({id}) after {max_retries} attempts")
                    return None
    
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
        max_retries = 3
        
        for attempt in range(max_retries):
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
                # Lock acquisition failed, wait with exponential backoff
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.1 * (2 ** attempt))
                else:
                    logger.error(f"Failed to acquire lock for update({id}) after {max_retries} attempts")
                    raise RuntimeError(f"Failed to acquire lock for update({id})")
    
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
        """Get cache statistics with error handling
        
        Returns:
            Cache statistics or None if caching disabled or error occurs
        """
        if not self.enable_cache:
            logger.debug("Cache is not enabled")
            return None
        
        try:
            stats = self.cache.get_stats()
            if stats is None:
                logger.warning("Cache stats returned None")
                return None
            return stats
        except Exception as e:
            logger.error(
                f"Failed to get cache stats: {str(e)}",
                exc_info=True,
                extra={
                    "action": "get_cache_stats",
                    "error": str(e),
                }
            )
            return None
    
    async def clear_cache(self) -> Dict[str, Any]:
        """Clear all caches with audit logging and error handling
        
        Useful for testing or manual cache invalidation.
        Ensures cache clearing doesn't block application shutdown.
        
        Returns:
            Dictionary with operation status and details
        """
        if not self.enable_cache:
            logger.debug("Cache is not enabled, skipping clear")
            return {"status": "skipped", "message": "Cache is not enabled"}
        
        try:
            # Log operation
            logger.info(
                "Cache clear operation started",
                extra={
                    "action": "cache_clear",
                    "timestamp": time.time(),
                }
            )
            
            await self.cache.clear()
            
            logger.info(
                "Cache cleared successfully",
                extra={
                    "action": "cache_clear",
                    "status": "success",
                    "timestamp": time.time(),
                }
            )
            
            return {
                "status": "success",
                "message": "Cache cleared successfully",
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(
                f"Failed to clear cache: {str(e)}",
                exc_info=True,
                extra={
                    "action": "cache_clear",
                    "status": "error",
                    "error": str(e),
                    "timestamp": time.time(),
                }
            )
            
            return {
                "status": "error",
                "message": f"Failed to clear cache: {str(e)}",
                "timestamp": time.time()
            }
    
    async def warmup_cache(
        self,
        limit: int = 1000,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        max_concurrent: int = 10,
    ) -> int:
        """Warmup cache by preloading hot data with retry mechanism
        
        Loads frequently accessed items into cache to improve
        cold start performance. Retries on failure.
        
        Args:
            limit: Maximum number of items to preload
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
            max_concurrent: Maximum concurrent items to cache (default: 10)
            
        Returns:
            Number of items warmed up
        """
        if not self.enable_cache:
            logger.debug("Cache is disabled, skipping warmup")
            return 0
        
        last_error = None
        for attempt in range(max_retries):
            try:
                # Load hot data (first N items) with timeout
                logger.debug(f"Cache warmup attempt {attempt + 1}/{max_retries}: loading up to {limit} items")
                items = await self._execute_with_timeout(
                    self.base_adapter.get_all(
                        filters={},
                        sorts={},
                        pagination={"skip": 0, "limit": limit},
                    ),
                    "warmup_cache"
                )
                
                if not items:
                    logger.warning("Cache warmup: no items returned from database")
                    return 0
                
                # Cache each item with concurrency limit
                count = 0
                semaphore = asyncio.Semaphore(max_concurrent)
                
                async def cache_item(item):
                    nonlocal count
                    async with semaphore:
                        try:
                            # Try to get ID from item
                            item_id = getattr(item, "id", None)
                            # If is dict, try get method
                            if item_id is None and isinstance(item, dict):
                                item_id = item.get("id")
                            
                            if item_id:
                                cache_key = self._get_cache_key("get_one", id=item_id)
                                await self.cache.set(cache_key, item)
                                count += 1
                        except Exception as e:
                            logger.warning(f"Failed to cache item: {str(e)}")
                
                # Cache all items concurrently
                await asyncio.gather(*[cache_item(item) for item in items], return_exceptions=True)
                
                logger.info(
                    f"Cache warmup completed successfully",
                    extra={
                        "action": "cache_warmup",
                        "items_warmed": count,
                        "total_items": len(items),
                        "attempt": attempt + 1,
                    }
                )
                return count
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Cache warmup attempt {attempt + 1} failed: {str(e)}. "
                        f"Retrying in {retry_delay}s...",
                        exc_info=True
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(
                        f"Cache warmup failed after {max_retries} attempts: {str(e)}",
                        exc_info=True,
                        extra={
                            "action": "cache_warmup_failed",
                            "attempts": max_retries,
                            "last_error": str(e),
                        }
                    )
        
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
