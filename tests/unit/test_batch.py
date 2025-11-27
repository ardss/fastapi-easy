"""Tests for batch operations module"""

import pytest
from fastapi_easy.core.batch import (
    BatchProcessor,
    BulkInsertOptimizer,
    BulkUpdateOptimizer,
    BulkDeleteOptimizer,
    create_batch_processor,
    create_bulk_insert_optimizer,
    create_bulk_update_optimizer,
    create_bulk_delete_optimizer,
)


class TestBatchProcessor:
    """Test BatchProcessor class"""
    
    @pytest.mark.asyncio
    async def test_process_batch_empty(self):
        """Test processing empty items"""
        processor = BatchProcessor()
        
        async def dummy_processor(batch):
            return batch
        
        result = await processor.process_batch([], dummy_processor)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_process_batch(self):
        """Test processing items in batches"""
        processor = BatchProcessor(batch_size=3)
        items = list(range(10))
        
        async def dummy_processor(batch):
            return [x * 2 for x in batch]
        
        result = await processor.process_batch(items, dummy_processor)
        assert len(result) == 10
        assert all(x % 2 == 0 for x in result)
    
    @pytest.mark.asyncio
    async def test_process_items(self):
        """Test processing individual items"""
        processor = BatchProcessor(batch_size=3)
        items = list(range(10))
        
        async def dummy_processor(item):
            return item * 2
        
        result = await processor.process_items(items, dummy_processor)
        assert len(result) == 10
        assert result == [x * 2 for x in items]


class TestBulkInsertOptimizer:
    """Test BulkInsertOptimizer class"""
    
    @pytest.mark.asyncio
    async def test_bulk_insert_empty(self):
        """Test bulk insert with empty items"""
        optimizer = BulkInsertOptimizer()
        
        async def dummy_insert(batch):
            return batch
        
        result = await optimizer.bulk_insert([], dummy_insert)
        assert result == []
    
    @pytest.mark.asyncio
    async def test_bulk_insert(self):
        """Test bulk insert with batching"""
        optimizer = BulkInsertOptimizer(batch_size=3)
        items = [{"id": i, "name": f"item_{i}"} for i in range(10)]
        
        async def dummy_insert(batch):
            return batch
        
        result = await optimizer.bulk_insert(items, dummy_insert)
        assert len(result) == 10


class TestBulkUpdateOptimizer:
    """Test BulkUpdateOptimizer class"""
    
    @pytest.mark.asyncio
    async def test_bulk_update_empty(self):
        """Test bulk update with empty items"""
        optimizer = BulkUpdateOptimizer()
        
        async def dummy_update(batch):
            return len(batch)
        
        result = await optimizer.bulk_update([], dummy_update)
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_bulk_update(self):
        """Test bulk update with batching"""
        optimizer = BulkUpdateOptimizer(batch_size=3)
        items = [{"id": i, "name": f"updated_{i}"} for i in range(10)]
        
        async def dummy_update(batch):
            return len(batch)
        
        result = await optimizer.bulk_update(items, dummy_update)
        assert result == 10


class TestBulkDeleteOptimizer:
    """Test BulkDeleteOptimizer class"""
    
    @pytest.mark.asyncio
    async def test_bulk_delete_empty(self):
        """Test bulk delete with empty IDs"""
        optimizer = BulkDeleteOptimizer()
        
        async def dummy_delete(batch):
            return len(batch)
        
        result = await optimizer.bulk_delete([], dummy_delete)
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_bulk_delete(self):
        """Test bulk delete with batching"""
        optimizer = BulkDeleteOptimizer(batch_size=3)
        ids = list(range(10))
        
        async def dummy_delete(batch):
            return len(batch)
        
        result = await optimizer.bulk_delete(ids, dummy_delete)
        assert result == 10


class TestFactoryFunctions:
    """Test factory functions"""
    
    def test_create_batch_processor(self):
        """Test creating batch processor"""
        processor = create_batch_processor(batch_size=50, max_concurrent=10)
        assert processor.batch_size == 50
        assert processor.max_concurrent == 10
    
    def test_create_bulk_insert_optimizer(self):
        """Test creating bulk insert optimizer"""
        optimizer = create_bulk_insert_optimizer(batch_size=100)
        assert optimizer.batch_size == 100
    
    def test_create_bulk_update_optimizer(self):
        """Test creating bulk update optimizer"""
        optimizer = create_bulk_update_optimizer(batch_size=100)
        assert optimizer.batch_size == 100
    
    def test_create_bulk_delete_optimizer(self):
        """Test creating bulk delete optimizer"""
        optimizer = create_bulk_delete_optimizer(batch_size=100)
        assert optimizer.batch_size == 100
