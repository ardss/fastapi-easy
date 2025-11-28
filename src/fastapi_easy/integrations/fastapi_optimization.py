"""FastAPI integration for performance optimization"""

from typing import Optional, Dict, Any
from fastapi import FastAPI
from ..core.optimized_adapter import OptimizedSQLAlchemyAdapter


class OptimizationConfig:
    """Configuration for FastAPI optimization integration"""
    
    def __init__(
        self,
        enable_cache: bool = True,
        enable_async: bool = True,
        cache_config: Optional[Dict[str, Any]] = None,
        async_config: Optional[Dict[str, Any]] = None,
        enable_monitoring: bool = True,
        enable_health_check: bool = True,
    ):
        """Initialize optimization config
        
        Args:
            enable_cache: Enable caching
            enable_async: Enable async optimization
            cache_config: Cache configuration
            async_config: Async configuration
            enable_monitoring: Enable performance monitoring
            enable_health_check: Enable health check endpoint
        """
        self.enable_cache = enable_cache
        self.enable_async = enable_async
        self.cache_config = cache_config or {}
        self.async_config = async_config or {}
        self.enable_monitoring = enable_monitoring
        self.enable_health_check = enable_health_check


class FastAPIOptimization:
    """FastAPI optimization integration"""
    
    def __init__(self, app: FastAPI, config: Optional[OptimizationConfig] = None):
        """Initialize FastAPI optimization
        
        Args:
            app: FastAPI application
            config: Optimization configuration
        """
        self.app = app
        self.config = config or OptimizationConfig()
        self.adapters: Dict[str, OptimizedSQLAlchemyAdapter] = {}
        self.monitors = {}
        
        self._setup_hooks()
        self._setup_health_check()
    
    def _setup_hooks(self) -> None:
        """Setup application lifecycle hooks"""
        
        @self.app.on_event("startup")
        async def startup():
            """Startup event handler"""
            # Warmup caches for all adapters
            for adapter_name, adapter in self.adapters.items():
                if self.config.enable_cache:
                    warmed = await adapter.warmup_cache(limit=1000)
                    print(f"[Optimization] Warmed up {warmed} items for {adapter_name}")
        
        @self.app.on_event("shutdown")
        async def shutdown():
            """Shutdown event handler"""
            # Cleanup resources
            for adapter_name, adapter in self.adapters.items():
                await adapter.clear_cache()
                print(f"[Optimization] Cleared cache for {adapter_name}")
    
    def _setup_health_check(self) -> None:
        """Setup health check endpoint"""
        if not self.config.enable_health_check:
            return
        
        @self.app.get("/health/optimization")
        async def health_check():
            """Health check endpoint for optimization"""
            health_status = {
                "status": "healthy",
                "adapters": {},
            }
            
            for adapter_name, adapter in self.adapters.items():
                stats = adapter.get_cache_stats()
                if stats:
                    health_status["adapters"][adapter_name] = {
                        "cache_enabled": True,
                        "hit_rate": stats.get("hit_rate", "N/A"),
                        "l1_size": stats.get("l1_stats", {}).get("size", 0),
                        "l2_size": stats.get("l2_stats", {}).get("size", 0),
                    }
            
            return health_status
    
    def register_adapter(
        self,
        name: str,
        adapter: OptimizedSQLAlchemyAdapter,
    ) -> None:
        """Register an optimized adapter
        
        Args:
            name: Adapter name
            adapter: Optimized adapter instance
        """
        self.adapters[name] = adapter
    
    def get_adapter(self, name: str) -> Optional[OptimizedSQLAlchemyAdapter]:
        """Get registered adapter
        
        Args:
            name: Adapter name
            
        Returns:
            Adapter instance or None
        """
        return self.adapters.get(name)


def setup_optimization(
    app: FastAPI,
    enable_cache: bool = True,
    enable_async: bool = True,
    cache_config: Optional[Dict[str, Any]] = None,
    async_config: Optional[Dict[str, Any]] = None,
    enable_monitoring: bool = True,
    enable_health_check: bool = True,
) -> FastAPIOptimization:
    """Setup FastAPI optimization
    
    Args:
        app: FastAPI application
        enable_cache: Enable caching
        enable_async: Enable async optimization
        cache_config: Cache configuration
        async_config: Async configuration
        enable_monitoring: Enable monitoring
        enable_health_check: Enable health check endpoint
        
    Returns:
        FastAPI optimization instance
    """
    config = OptimizationConfig(
        enable_cache=enable_cache,
        enable_async=enable_async,
        cache_config=cache_config,
        async_config=async_config,
        enable_monitoring=enable_monitoring,
        enable_health_check=enable_health_check,
    )
    
    return FastAPIOptimization(app, config)
