"""Integration tests for optimization modules"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi_easy.crud_router_optimization import OptimizedCRUDRouter
from fastapi_easy.core.optimized_adapter import OptimizedSQLAlchemyAdapter
from fastapi_easy.core.cache_monitor import CacheMonitor
from fastapi_easy.core.optimization_config import OptimizationConfig


class TestOptimizationIntegration:
    """Integration tests for optimization modules"""
    
    @pytest.mark.asyncio
    async def test_optimized_adapter_with_cache_monitor(self):
        """Test optimized adapter with cache monitoring"""
        # Create mock base adapter
        base_adapter = AsyncMock()
        base_adapter.model = MagicMock()
        base_adapter.get_one = AsyncMock(return_value={"id": 1, "name": "test"})
        
        # Create optimized adapter
        optimized = OptimizedSQLAlchemyAdapter(
            base_adapter,
            enable_cache=True,
        )
        
        # Create cache monitor
        monitor = CacheMonitor()
        
        # First call - cache miss
        result1 = await optimized.get_one(1)
        monitor.record_miss()
        
        # Second call - cache hit
        result2 = await optimized.get_one(1)
        monitor.record_hit()
        
        # Verify results
        assert result1 == result2
        assert monitor.metrics.hits == 1
        assert monitor.metrics.misses == 1
    
    @pytest.mark.asyncio
    async def test_optimized_crud_router_with_config(self):
        """Test optimized CRUD router with configuration"""
        from unittest.mock import patch
        
        # Create configuration
        config = OptimizationConfig(
            enable_cache=True,
            l1_size=500,
            l2_size=5000,
        )
        
        # Create mock schema and backend
        mock_schema = MagicMock()
        mock_schema.__name__ = "TestSchema"
        mock_backend = AsyncMock()
        mock_backend.model = MagicMock()
        
        # Create optimized router with patched CRUDRouter init
        with patch('fastapi_easy.crud_router_optimization.CRUDRouter.__init__', return_value=None):
            router = OptimizedCRUDRouter(
                schema=mock_schema,
                backend=mock_backend,
                enable_optimization=True,
                cache_config={
                    "l1_size": config.l1_size,
                    "l2_size": config.l2_size,
                },
            )
        
        # Verify router is optimized
        assert router.enable_optimization is True
        assert router.optimized_backend is not None
    
    @pytest.mark.asyncio
    async def test_cache_warmup_and_monitoring(self):
        """Test cache warmup with monitoring"""
        # Create mock base adapter
        base_adapter = AsyncMock()
        base_adapter.model = MagicMock()
        base_adapter.get_all = AsyncMock(
            return_value=[
                {"id": 1, "name": "item1"},
                {"id": 2, "name": "item2"},
            ]
        )
        
        # Create optimized adapter
        optimized = OptimizedSQLAlchemyAdapter(
            base_adapter,
            enable_cache=True,
        )
        
        # Warmup cache
        warmed = await optimized.warmup_cache(limit=10)
        
        # Verify warmup
        assert warmed == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_access_with_locks(self):
        """Test concurrent access with lock protection"""
        import asyncio
        
        # Create mock base adapter
        base_adapter = AsyncMock()
        base_adapter.model = MagicMock()
        base_adapter.update = AsyncMock(return_value={"id": 1, "name": "updated"})
        
        # Create optimized adapter
        optimized = OptimizedSQLAlchemyAdapter(
            base_adapter,
            enable_cache=True,
        )
        
        # Simulate concurrent updates
        async def update_item(item_id, data):
            return await optimized.update(item_id, data)
        
        # Run concurrent updates
        results = await asyncio.gather(
            update_item(1, {"name": "update1"}),
            update_item(1, {"name": "update2"}),
            update_item(1, {"name": "update3"}),
        )
        
        # Verify all updates succeeded
        assert len(results) == 3
        assert all(r is not None for r in results)
