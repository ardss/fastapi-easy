"""Performance tests for query operations"""

import pytest
import time
import asyncio
from sqlalchemy import select

from tests.performance.conftest import PerformanceItem


@pytest.mark.asyncio
class TestQueryPerformance:
    """Performance tests for query operations"""
    
    async def test_large_dataset_retrieval(self, perf_sqlalchemy_adapter, large_dataset, benchmark):
        """Test retrieval of large dataset (10000+ items)"""
        async def get_all_items():
            return await perf_sqlalchemy_adapter.get_all(
                filters={},
                sorts={},
                pagination={"skip": 0, "limit": 10000}
            )
        
        result = benchmark(asyncio.run, get_all_items())
        assert len(result) == 10000
    
    async def test_filtered_query_performance(self, perf_sqlalchemy_adapter, large_dataset, benchmark):
        """Test filtered query performance"""
        async def filtered_query():
            return await perf_sqlalchemy_adapter.get_all(
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
        
        result = benchmark(asyncio.run, filtered_query())
        assert len(result) > 0
    
    async def test_sorted_query_performance(self, perf_sqlalchemy_adapter, large_dataset, benchmark):
        """Test sorted query performance"""
        async def sorted_query():
            return await perf_sqlalchemy_adapter.get_all(
                filters={},
                sorts={"price": "desc"},
                pagination={"skip": 0, "limit": 1000}
            )
        
        result = benchmark(asyncio.run, sorted_query())
        assert len(result) == 1000
    
    async def test_paginated_query_performance(self, perf_sqlalchemy_adapter, large_dataset, benchmark):
        """Test paginated query performance"""
        async def paginated_query():
            results = []
            for page in range(10):
                result = await perf_sqlalchemy_adapter.get_all(
                    filters={},
                    sorts={},
                    pagination={"skip": page * 1000, "limit": 1000}
                )
                results.extend(result)
            return results
        
        result = benchmark(asyncio.run, paginated_query())
        assert len(result) == 10000
    
    async def test_single_item_retrieval_performance(self, perf_sqlalchemy_adapter, large_dataset, benchmark):
        """Test single item retrieval performance"""
        async def get_single_item():
            return await perf_sqlalchemy_adapter.get_one(5000)
        
        result = benchmark(asyncio.run, get_single_item())
        assert result is not None
    
    async def test_count_performance(self, perf_sqlalchemy_adapter, large_dataset, benchmark):
        """Test count operation performance"""
        async def count_items():
            return await perf_sqlalchemy_adapter.count({})
        
        result = benchmark(asyncio.run, count_items())
        assert result == 10000
    
    async def test_create_performance(self, perf_sqlalchemy_adapter, benchmark):
        """Test create operation performance"""
        async def create_item():
            return await perf_sqlalchemy_adapter.create({
                "name": "test_item",
                "description": "Test description",
                "price": 99.99,
                "quantity": 10
            })
        
        result = benchmark(asyncio.run, create_item())
        assert result is not None
        assert result.name == "test_item"
    
    async def test_update_performance(self, perf_sqlalchemy_adapter, large_dataset, benchmark):
        """Test update operation performance"""
        async def update_item():
            return await perf_sqlalchemy_adapter.update(5000, {
                "price": 199.99,
                "quantity": 50
            })
        
        result = benchmark(asyncio.run, update_item())
        assert result is not None
        assert result.price == 199.99
    
    async def test_delete_performance(self, perf_sqlalchemy_adapter, large_dataset, benchmark):
        """Test delete operation performance"""
        async def delete_item():
            return await perf_sqlalchemy_adapter.delete_one(9999)
        
        result = benchmark(asyncio.run, delete_item())
        assert result is not None
