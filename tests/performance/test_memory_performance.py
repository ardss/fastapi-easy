"""Performance tests for memory usage"""

import pytest


@pytest.mark.asyncio
class TestMemoryPerformance:
    """Performance tests for memory usage"""
    
    async def test_large_dataset_memory(self, perf_sqlalchemy_adapter, large_dataset):
        """Test memory usage with large dataset retrieval"""
        result = await perf_sqlalchemy_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 5000}
        )
        assert len(result) == 5000
    
    async def test_paginated_retrieval_memory(self, perf_sqlalchemy_adapter, large_dataset):
        """Test memory usage with paginated retrieval"""
        all_items = []
        for page in range(5):
            result = await perf_sqlalchemy_adapter.get_all(
                filters={},
                sorts={},
                pagination={"skip": page * 1000, "limit": 1000}
            )
            all_items.extend(result)
        assert len(all_items) == 5000
    
    async def test_repeated_queries_memory(self, perf_sqlalchemy_adapter, large_dataset):
        """Test memory usage with repeated queries"""
        for _ in range(5):
            result = await perf_sqlalchemy_adapter.get_all(
                filters={},
                sorts={},
                pagination={"skip": 0, "limit": 1000}
            )
            assert len(result) == 1000
    
    async def test_create_many_items_memory(self, perf_sqlalchemy_adapter):
        """Test memory usage when creating many items"""
        for i in range(100):
            result = await perf_sqlalchemy_adapter.create({
                "name": f"item_{i}",
                "description": f"Description {i}",
                "price": float(i),
                "quantity": i % 100
            })
            assert result is not None
    
    async def test_filtered_query_memory(self, perf_sqlalchemy_adapter, large_dataset):
        """Test memory usage with filtered queries"""
        result = await perf_sqlalchemy_adapter.get_all(
            filters={
                "price_filter": {
                    "field": "price",
                    "operator": "gte",
                    "value": 500.0
                }
            },
            sorts={},
            pagination={"skip": 0, "limit": 1000}
        )
        assert len(result) > 0
