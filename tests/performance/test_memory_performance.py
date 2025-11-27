"""Performance tests for memory usage"""

import pytest
import sys
import gc
from typing import List


@pytest.mark.asyncio
class TestMemoryPerformance:
    """Performance tests for memory usage"""
    
    async def test_large_dataset_memory(self, perf_sqlalchemy_adapter, large_dataset):
        """Test memory usage with large dataset retrieval"""
        gc.collect()
        
        # Get memory before
        import tracemalloc
        tracemalloc.start()
        
        # Retrieve all items
        result = await perf_sqlalchemy_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 10000}
        )
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should retrieve all items
        assert len(result) == 10000
        
        # Memory usage should be reasonable (< 100 MB for 10000 items)
        # This is a rough estimate, adjust based on actual measurements
        assert peak < 100 * 1024 * 1024  # 100 MB
    
    async def test_paginated_retrieval_memory(self, perf_sqlalchemy_adapter, large_dataset):
        """Test memory usage with paginated retrieval"""
        gc.collect()
        
        import tracemalloc
        tracemalloc.start()
        
        # Retrieve in pages
        all_items = []
        for page in range(10):
            result = await perf_sqlalchemy_adapter.get_all(
                filters={},
                sorts={},
                pagination={"skip": page * 1000, "limit": 1000}
            )
            all_items.extend(result)
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should retrieve all items
        assert len(all_items) == 10000
        
        # Memory usage should be reasonable
        assert peak < 100 * 1024 * 1024  # 100 MB
    
    async def test_repeated_queries_memory(self, perf_sqlalchemy_adapter, large_dataset):
        """Test memory usage with repeated queries"""
        gc.collect()
        
        import tracemalloc
        tracemalloc.start()
        
        # Execute same query multiple times
        for _ in range(10):
            result = await perf_sqlalchemy_adapter.get_all(
                filters={},
                sorts={},
                pagination={"skip": 0, "limit": 1000}
            )
            assert len(result) == 1000
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory should not grow significantly with repeated queries
        assert peak < 50 * 1024 * 1024  # 50 MB
    
    async def test_create_many_items_memory(self, perf_sqlalchemy_adapter):
        """Test memory usage when creating many items"""
        gc.collect()
        
        import tracemalloc
        tracemalloc.start()
        
        # Create 1000 items
        for i in range(1000):
            await perf_sqlalchemy_adapter.create({
                "name": f"item_{i}",
                "description": f"Description {i}",
                "price": float(i),
                "quantity": i % 100
            })
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory usage should be reasonable
        assert peak < 50 * 1024 * 1024  # 50 MB
    
    async def test_memory_cleanup_after_operations(self, perf_sqlalchemy_adapter, large_dataset):
        """Test that memory is properly cleaned up after operations"""
        gc.collect()
        
        import tracemalloc
        tracemalloc.start()
        
        # Execute operation
        result = await perf_sqlalchemy_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 10000}
        )
        
        peak_during = tracemalloc.get_traced_memory()[1]
        
        # Clear result
        del result
        gc.collect()
        
        current_after, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Memory should be freed after clearing result
        # Allow some overhead, but should be significantly less than peak
        assert current_after < peak_during * 0.5
    
    async def test_filtered_query_memory(self, perf_sqlalchemy_adapter, large_dataset):
        """Test memory usage with filtered queries"""
        gc.collect()
        
        import tracemalloc
        tracemalloc.start()
        
        # Execute filtered query
        result = await perf_sqlalchemy_adapter.get_all(
            filters={
                "price_filter": {
                    "field": "price",
                    "operator": "gte",
                    "value": 500.0
                }
            },
            sorts={},
            pagination={"skip": 0, "limit": 5000}
        )
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Should retrieve filtered results
        assert len(result) > 0
        
        # Memory usage should be reasonable
        assert peak < 50 * 1024 * 1024  # 50 MB
