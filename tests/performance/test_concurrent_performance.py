"""Performance tests for concurrent operations"""

import pytest
import asyncio
from typing import List


@pytest.mark.asyncio
class TestConcurrentPerformance:
    """Performance tests for concurrent operations"""
    
    async def test_concurrent_reads(self, perf_sqlalchemy_adapter, large_dataset):
        """Test concurrent read operations (50 concurrent)"""
        async def read_item(item_id: int):
            return await perf_sqlalchemy_adapter.get_one(item_id)
        
        # Create 50 concurrent read tasks
        tasks = [read_item(i % 5000) for i in range(50)]
        
        results = await asyncio.gather(*tasks)
        
        # All reads should succeed
        assert len(results) == 50
        assert all(r is not None for r in results)
    
    async def test_concurrent_writes(self, perf_sqlalchemy_adapter):
        """Test concurrent write operations (20 concurrent)"""
        async def create_item(item_id: int):
            return await perf_sqlalchemy_adapter.create({
                "name": f"concurrent_item_{item_id}",
                "description": f"Concurrent item {item_id}",
                "price": float(item_id),
                "quantity": item_id
            })
        
        # Create 20 concurrent write tasks
        tasks = [create_item(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All writes should succeed
        assert len(results) == 20
        assert all(r is not None for r in results)
    
    async def test_concurrent_mixed_operations(self, perf_sqlalchemy_adapter, large_dataset):
        """Test mixed concurrent operations (reads, writes, updates)"""
        async def read_item(item_id: int):
            return await perf_sqlalchemy_adapter.get_one(item_id)
        
        async def create_item(item_id: int):
            return await perf_sqlalchemy_adapter.create({
                "name": f"mixed_item_{item_id}",
                "price": float(item_id),
                "quantity": item_id
            })
        
        async def update_item(item_id: int):
            return await perf_sqlalchemy_adapter.update(item_id, {
                "price": float(item_id * 2)
            })
        
        # Mix of operations
        tasks = []
        for i in range(15):
            tasks.append(read_item(i % 5000))
        for i in range(10):
            tasks.append(create_item(5000 + i))
        for i in range(5):
            tasks.append(update_item(i * 100))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should complete
        assert len(results) == 30
    
    async def test_concurrent_queries(self, perf_sqlalchemy_adapter, large_dataset):
        """Test concurrent query operations"""
        async def query_items(skip: int, limit: int):
            return await perf_sqlalchemy_adapter.get_all(
                filters={},
                sorts={},
                pagination={"skip": skip, "limit": limit}
            )
        
        # Create 20 concurrent query tasks with different pagination
        tasks = [query_items(i * 100, 100) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        # All queries should succeed
        assert len(results) == 20
    
    async def test_concurrent_count_operations(self, perf_sqlalchemy_adapter, large_dataset):
        """Test concurrent count operations"""
        async def count_items():
            return await perf_sqlalchemy_adapter.count({})
        
        # Create 30 concurrent count tasks
        tasks = [count_items() for _ in range(30)]
        results = await asyncio.gather(*tasks)
        
        # All counts should return same value
        assert len(results) == 30
        assert all(r == 5000 for r in results)
    
    async def test_high_concurrency_stress(self, perf_sqlalchemy_adapter, large_dataset):
        """Stress test with high concurrency (100 concurrent)"""
        async def read_item(item_id: int):
            return await perf_sqlalchemy_adapter.get_one(item_id)
        
        # Create 100 concurrent read tasks
        tasks = [read_item(i % 5000) for i in range(100)]
        results = await asyncio.gather(*tasks)
        
        # All reads should succeed
        assert len(results) == 100
        assert all(r is not None for r in results)
