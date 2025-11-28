"""Async batch processing optimization for concurrent operations"""

import asyncio
from typing import Any, List, Callable, Awaitable, Optional


class AsyncBatchProcessor:
    """Process items concurrently with controlled concurrency"""
    
    def __init__(self, max_concurrent: int = 10):
        """Initialize async batch processor
        
        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self.max_concurrent = max_concurrent
    
    async def process_concurrent(
        self,
        items: List[Any],
        processor: Callable[[Any], Awaitable[Any]],
        timeout: Optional[float] = None,
    ) -> List[Any]:
        """Process items concurrently with semaphore
        
        Args:
            items: Items to process
            processor: Async function to process each item
            timeout: Optional timeout for each item
            
        Returns:
            List of processed results (may contain exceptions)
        """
        if not items:
            return []
        
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def bounded_processor(item):
            async with semaphore:
                try:
                    if timeout:
                        return await asyncio.wait_for(processor(item), timeout=timeout)
                    return await processor(item)
                except Exception as e:
                    return e  # 返回异常而不是抛出
        
        tasks = [bounded_processor(item) for item in items]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def process_batches(
        self,
        items: List[Any],
        batch_size: int,
        processor: Callable[[List[Any]], Awaitable[List[Any]]],
        timeout: Optional[float] = None,
    ) -> List[Any]:
        """Process items in batches concurrently
        
        Args:
            items: Items to process
            batch_size: Size of each batch
            processor: Async function to process batch
            timeout: Optional timeout for each batch
            
        Returns:
            List of processed results (may contain exceptions)
        """
        if not items:
            return []
        
        # Split into batches
        batches = [
            items[i:i + batch_size]
            for i in range(0, len(items), batch_size)
        ]
        
        # Process batches concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def bounded_processor(batch):
            async with semaphore:
                try:
                    if timeout:
                        return await asyncio.wait_for(processor(batch), timeout=timeout)
                    return await processor(batch)
                except Exception as e:
                    return e  # 返回异常而不是抛出
        
        tasks = [bounded_processor(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        results = []
        for batch_result in batch_results:
            if batch_result and not isinstance(batch_result, Exception):
                results.extend(batch_result)
            elif isinstance(batch_result, Exception):
                results.append(batch_result)  # 保留异常
        
        return results


class AsyncPipeline:
    """Async pipeline for chaining operations"""
    
    def __init__(self):
        """Initialize async pipeline"""
        self.stages: List[Callable] = []
    
    def add_stage(self, processor: Callable) -> "AsyncPipeline":
        """Add processing stage
        
        Args:
            processor: Async function to process items
            
        Returns:
            Self for chaining
        """
        self.stages.append(processor)
        return self
    
    async def execute(self, items: List[Any]) -> List[Any]:
        """Execute pipeline
        
        Args:
            items: Input items
            
        Returns:
            Processed items
        """
        result = items
        for stage in self.stages:
            result = await stage(result)
        return result


def create_async_batch_processor(max_concurrent: int = 10) -> AsyncBatchProcessor:
    """Create async batch processor
    
    Args:
        max_concurrent: Maximum concurrent tasks
        
    Returns:
        Async batch processor instance
    """
    return AsyncBatchProcessor(max_concurrent)


def create_async_pipeline() -> AsyncPipeline:
    """Create async pipeline
    
    Returns:
        Async pipeline instance
    """
    return AsyncPipeline()
