"""Optimized adapter that integrates all performance optimizations"""

from typing import Any, Dict, List, Optional
from .multilayer_cache import MultiLayerCache
from .async_batch import AsyncBatchProcessor
from .query_projection import QueryProjection


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
    ):
        """Initialize optimized adapter
        
        Args:
            base_adapter: Base SQLAlchemy adapter
            enable_cache: Enable multi-layer caching
            enable_async: Enable async batch processing
            cache_config: Cache configuration
            async_config: Async configuration
        """
        self.base_adapter = base_adapter
        self.enable_cache = enable_cache
        self.enable_async = enable_async
        
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
        
        # Track model for cache invalidation
        self.model = base_adapter.model
    
    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation
        
        Args:
            operation: Operation name (get_all, get_one, etc.)
            **kwargs: Operation parameters
            
        Returns:
            Cache key
        """
        key_parts = [operation]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={str(v)[:50]}")
        return "|".join(key_parts)
    
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
        
        # Execute query
        result = await self.base_adapter.get_all(filters, sorts, pagination)
        
        # Cache result
        if self.enable_cache:
            await self.cache.set(cache_key, result)
        
        return result
    
    async def get_one(self, id: Any) -> Optional[Any]:
        """Get single item with caching
        
        Args:
            id: Item id
            
        Returns:
            Item or None
        """
        # Try cache first
        if self.enable_cache:
            cache_key = self._get_cache_key("get_one", id=id)
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached
        
        # Execute query
        result = await self.base_adapter.get_one(id)
        
        # Cache result
        if self.enable_cache and result is not None:
            await self.cache.set(cache_key, result)
        
        return result
    
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
        """Update item and invalidate cache
        
        Args:
            id: Item id
            data: Update data
            
        Returns:
            Updated item
        """
        # Update item
        result = await self.base_adapter.update(id, data)
        
        # Invalidate specific item cache
        if self.enable_cache:
            cache_key = self._get_cache_key("get_one", id=id)
            await self.cache.delete(cache_key)
            # Also invalidate list caches
            await self._invalidate_list_cache()
        
        return result
    
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
        """Invalidate all list-related caches
        
        This is called when data is modified to ensure
        list queries return fresh data.
        """
        if not self.enable_cache:
            return
        
        # Clear all caches to ensure data consistency
        # In production, could use more sophisticated invalidation
        # (e.g., pattern-based invalidation)
        await self.cache.clear()
    
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
