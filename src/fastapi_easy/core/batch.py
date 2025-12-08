"""Batch operations optimization for better performance"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List


class BatchProcessor:
    """Process operations in batches for better performance"""

    def __init__(self, batch_size: int = 100, max_concurrent: int = 5):
        """Initialize batch processor

        Args:
            batch_size: Number of items per batch
            max_concurrent: Maximum concurrent batches
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent

    async def process_batch(
        self,
        items: List[Any],
        processor: Callable[[List[Any]], Awaitable[List[Any]]],
    ) -> List[Any]:
        """Process items in batches

        Args:
            items: Items to process
            processor: Async function to process batch

        Returns:
            List of processed results
        """
        if not items:
            return []

        # Split items into batches
        batches = [items[i : i + self.batch_size] for i in range(0, len(items), self.batch_size)]

        # Process batches concurrently with limit
        results = []
        for i in range(0, len(batches), self.max_concurrent):
            batch_chunk = batches[i : i + self.max_concurrent]
            tasks = [processor(batch) for batch in batch_chunk]
            batch_results = await asyncio.gather(*tasks)

            # Flatten results
            for batch_result in batch_results:
                if batch_result:
                    results.extend(batch_result)

        return results

    async def process_items(
        self,
        items: List[Any],
        processor: Callable[[Any], Awaitable[Any]],
    ) -> List[Any]:
        """Process individual items with batching

        Args:
            items: Items to process
            processor: Async function to process item

        Returns:
            List of processed results
        """
        if not items:
            return []

        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            tasks = [processor(item) for item in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

        return results


class BulkInsertOptimizer:
    """Optimize bulk insert operations"""

    def __init__(self, batch_size: int = 100):
        """Initialize bulk insert optimizer

        Args:
            batch_size: Number of items per insert batch
        """
        self.batch_size = batch_size

    async def bulk_insert(
        self,
        items: List[Dict[str, Any]],
        insert_func: Callable[[List[Dict[str, Any]]], Awaitable[List[Any]]],
    ) -> List[Any]:
        """Perform bulk insert with batching

        Args:
            items: Items to insert
            insert_func: Async function to insert batch

        Returns:
            List of inserted items
        """
        if not items:
            return []

        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            batch_results = await insert_func(batch)
            results.extend(batch_results)

        return results


class BulkUpdateOptimizer:
    """Optimize bulk update operations"""

    def __init__(self, batch_size: int = 100):
        """Initialize bulk update optimizer

        Args:
            batch_size: Number of items per update batch
        """
        self.batch_size = batch_size

    async def bulk_update(
        self,
        items: List[Dict[str, Any]],
        update_func: Callable[[List[Dict[str, Any]]], Awaitable[int]],
    ) -> int:
        """Perform bulk update with batching

        Args:
            items: Items to update
            update_func: Async function to update batch

        Returns:
            Total number of updated items
        """
        if not items:
            return 0

        total_updated = 0
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            updated = await update_func(batch)
            total_updated += updated

        return total_updated


class BulkDeleteOptimizer:
    """Optimize bulk delete operations"""

    def __init__(self, batch_size: int = 100):
        """Initialize bulk delete optimizer

        Args:
            batch_size: Number of items per delete batch
        """
        self.batch_size = batch_size

    async def bulk_delete(
        self,
        ids: List[Any],
        delete_func: Callable[[List[Any]], Awaitable[int]],
    ) -> int:
        """Perform bulk delete with batching

        Args:
            ids: IDs to delete
            delete_func: Async function to delete batch

        Returns:
            Total number of deleted items
        """
        if not ids:
            return 0

        total_deleted = 0
        for i in range(0, len(ids), self.batch_size):
            batch = ids[i : i + self.batch_size]
            deleted = await delete_func(batch)
            total_deleted += deleted

        return total_deleted


def create_batch_processor(batch_size: int = 100, max_concurrent: int = 5) -> BatchProcessor:
    """Create a batch processor instance

    Args:
        batch_size: Number of items per batch
        max_concurrent: Maximum concurrent batches

    Returns:
        Batch processor instance
    """
    return BatchProcessor(batch_size, max_concurrent)


def create_bulk_insert_optimizer(batch_size: int = 100) -> BulkInsertOptimizer:
    """Create a bulk insert optimizer instance

    Args:
        batch_size: Number of items per insert batch

    Returns:
        Bulk insert optimizer instance
    """
    return BulkInsertOptimizer(batch_size)


def create_bulk_update_optimizer(batch_size: int = 100) -> BulkUpdateOptimizer:
    """Create a bulk update optimizer instance

    Args:
        batch_size: Number of items per update batch

    Returns:
        Bulk update optimizer instance
    """
    return BulkUpdateOptimizer(batch_size)


def create_bulk_delete_optimizer(batch_size: int = 100) -> BulkDeleteOptimizer:
    """Create a bulk delete optimizer instance

    Args:
        batch_size: Number of items per delete batch

    Returns:
        Bulk delete optimizer instance
    """
    return BulkDeleteOptimizer(batch_size)
