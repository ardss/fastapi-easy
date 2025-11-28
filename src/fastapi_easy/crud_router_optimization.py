"""CRUDRouter optimization integration"""

from typing import Optional, Dict, Any, Type
from fastapi_easy.crud_router import CRUDRouter
from fastapi_easy.core.optimized_adapter import OptimizedSQLAlchemyAdapter, create_optimized_adapter


class OptimizedCRUDRouter(CRUDRouter):
    """CRUDRouter with integrated performance optimizations
    
    Automatically wraps the backend adapter with optimization features:
    - Multi-layer caching
    - Async batch processing
    - Query projection
    - Cache monitoring
    """
    
    def __init__(
        self,
        schema: Type,
        backend,
        enable_optimization: bool = True,
        cache_config: Optional[Dict[str, Any]] = None,
        async_config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """Initialize optimized CRUD router
        
        Args:
            schema: Pydantic schema
            backend: ORM adapter
            enable_optimization: Enable performance optimizations
            cache_config: Cache configuration
            async_config: Async configuration
            **kwargs: Additional CRUDRouter arguments
        """
        # Wrap backend with optimization if enabled
        if enable_optimization and not isinstance(backend, OptimizedSQLAlchemyAdapter):
            backend = create_optimized_adapter(
                backend,
                enable_cache=True,
                enable_async=True,
                cache_config=cache_config or {},
                async_config=async_config or {},
            )
        
        # Store optimization config
        self.enable_optimization = enable_optimization
        self.optimized_backend = backend if enable_optimization else None
        
        # Initialize parent CRUDRouter
        super().__init__(schema=schema, backend=backend, **kwargs)
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics
        
        Returns:
            Cache statistics if optimization enabled
        """
        if self.enable_optimization and self.optimized_backend:
            return self.optimized_backend.get_cache_stats()
        return None
    
    async def warmup_cache(self, limit: int = 1000) -> int:
        """Warmup cache with hot data
        
        Args:
            limit: Maximum items to preload
            
        Returns:
            Number of items warmed up
        """
        if self.enable_optimization and self.optimized_backend:
            return await self.optimized_backend.warmup_cache(limit)
        return 0
    
    async def clear_cache(self) -> None:
        """Clear all caches
        
        Useful for testing or manual cache invalidation.
        """
        if self.enable_optimization and self.optimized_backend:
            await self.optimized_backend.clear_cache()


def create_optimized_crud_router(
    schema: Type,
    backend,
    enable_optimization: bool = True,
    cache_config: Optional[Dict[str, Any]] = None,
    async_config: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> OptimizedCRUDRouter:
    """Create an optimized CRUD router
    
    Args:
        schema: Pydantic schema
        backend: ORM adapter
        enable_optimization: Enable optimizations
        cache_config: Cache configuration
        async_config: Async configuration
        **kwargs: Additional CRUDRouter arguments
        
    Returns:
        Optimized CRUD router instance
    """
    return OptimizedCRUDRouter(
        schema=schema,
        backend=backend,
        enable_optimization=enable_optimization,
        cache_config=cache_config,
        async_config=async_config,
        **kwargs,
    )
