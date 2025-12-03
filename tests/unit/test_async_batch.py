"""Tests for async batch processing module"""

import pytest
import asyncio
from fastapi_easy.core.async_batch import (
    AsyncBatchProcessor,
    AsyncPipeline,
    create_async_batch_processor,
    create_async_pipeline,
)


class TestAsyncBatchProcessor:
    """Test AsyncBatchProcessor class"""

    @pytest.mark.asyncio
    async def test_process_concurrent_empty(self):
        """Test processing empty items"""
        processor = AsyncBatchProcessor()

        async def dummy_processor(item):
            return item * 2

        result = await processor.process_concurrent([], dummy_processor)
        assert result == []

    @pytest.mark.asyncio
    async def test_process_concurrent(self):
        """Test concurrent processing"""
        processor = AsyncBatchProcessor(max_concurrent=3)
        items = list(range(10))

        async def dummy_processor(item):
            await asyncio.sleep(0.01)
            return item * 2

        result = await processor.process_concurrent(items, dummy_processor)
        assert len(result) == 10
        assert result == [x * 2 for x in items]

    @pytest.mark.asyncio
    async def test_process_batches_empty(self):
        """Test processing empty batches"""
        processor = AsyncBatchProcessor()

        async def dummy_processor(batch):
            return batch

        result = await processor.process_batches([], 5, dummy_processor)
        assert result == []

    @pytest.mark.asyncio
    async def test_process_batches(self):
        """Test batch processing"""
        processor = AsyncBatchProcessor(max_concurrent=2)
        items = list(range(10))

        async def dummy_processor(batch):
            await asyncio.sleep(0.01)
            return [x * 2 for x in batch]

        result = await processor.process_batches(items, 3, dummy_processor)
        assert len(result) == 10
        assert result == [x * 2 for x in items]

    @pytest.mark.asyncio
    async def test_max_concurrent_limit(self):
        """Test max concurrent limit"""
        processor = AsyncBatchProcessor(max_concurrent=2)
        concurrent_count = 0
        max_concurrent_seen = 0

        async def counting_processor(item):
            nonlocal concurrent_count, max_concurrent_seen
            concurrent_count += 1
            max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
            await asyncio.sleep(0.01)
            concurrent_count -= 1
            return item

        items = list(range(10))
        await processor.process_concurrent(items, counting_processor)

        # Should not exceed max_concurrent
        assert max_concurrent_seen <= 2


class TestAsyncPipeline:
    """Test AsyncPipeline class"""

    @pytest.mark.asyncio
    async def test_single_stage(self):
        """Test pipeline with single stage"""
        pipeline = AsyncPipeline()

        async def stage1(items):
            return [x * 2 for x in items]

        pipeline.add_stage(stage1)
        result = await pipeline.execute([1, 2, 3])

        assert result == [2, 4, 6]

    @pytest.mark.asyncio
    async def test_multiple_stages(self):
        """Test pipeline with multiple stages"""
        pipeline = AsyncPipeline()

        async def stage1(items):
            return [x * 2 for x in items]

        async def stage2(items):
            return [x + 1 for x in items]

        pipeline.add_stage(stage1).add_stage(stage2)
        result = await pipeline.execute([1, 2, 3])

        assert result == [3, 5, 7]

    @pytest.mark.asyncio
    async def test_pipeline_chaining(self):
        """Test pipeline method chaining"""

        async def stage1(items):
            return [x * 2 for x in items]

        async def stage2(items):
            return [x + 1 for x in items]

        async def stage3(items):
            return [x * 2 for x in items]

        pipeline = AsyncPipeline().add_stage(stage1).add_stage(stage2).add_stage(stage3)

        result = await pipeline.execute([1, 2, 3])
        assert result == [6, 10, 14]


class TestFactoryFunctions:
    """Test factory functions"""

    def test_create_async_batch_processor(self):
        """Test creating async batch processor"""
        processor = create_async_batch_processor(max_concurrent=5)
        assert processor.max_concurrent == 5

    def test_create_async_pipeline(self):
        """Test creating async pipeline"""
        pipeline = create_async_pipeline()
        assert isinstance(pipeline, AsyncPipeline)
        assert len(pipeline.stages) == 0
