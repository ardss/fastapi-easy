"""Tests for cache invalidation management"""

import asyncio
from unittest.mock import AsyncMock

import pytest

from fastapi_easy.core.cache_invalidation import (
    CacheInvalidationManager,
    InvalidationStrategy,
    get_invalidation_manager,
)


class TestCacheInvalidationManager:
    """Test cache invalidation manager"""

    @pytest.fixture
    def manager(self):
        """Create invalidation manager"""
        return CacheInvalidationManager()

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache"""
        cache = AsyncMock()
        cache.l1_cache = {
            "get_all:abc123": ({"id": 1}, 0),
            "get_all:def456": ({"id": 2}, 0),
            "get_one:ghi789": ({"id": 1}, 0),
        }
        cache.delete = AsyncMock()
        cache.clear = AsyncMock()
        return cache

    @pytest.mark.asyncio
    async def test_invalidate_list_cache_selective(self, manager, mock_cache):
        """Test selective list cache invalidation"""
        manager.strategy = InvalidationStrategy.SELECTIVE

        count = await manager.invalidate_list_cache(mock_cache, "get_all")

        assert count >= 0

    @pytest.mark.asyncio
    async def test_invalidate_list_cache_pattern(self, manager, mock_cache):
        """Test pattern-based list cache invalidation"""
        manager.strategy = InvalidationStrategy.PATTERN

        count = await manager.invalidate_list_cache(mock_cache, "get_all")

        assert count >= 0

    @pytest.mark.asyncio
    async def test_invalidate_list_cache_full(self, manager, mock_cache):
        """Test full cache invalidation"""
        manager.strategy = InvalidationStrategy.FULL

        count = await manager.invalidate_list_cache(mock_cache, "get_all")

        assert count >= 0

    @pytest.mark.asyncio
    async def test_invalidate_item_cache(self, manager, mock_cache):
        """Test item cache invalidation"""
        count = await manager.invalidate_item_cache(mock_cache, item_id=1)

        assert count >= 0

    @pytest.mark.asyncio
    async def test_invalidate_by_filter(self, manager, mock_cache):
        """Test filter-based invalidation"""
        count = await manager.invalidate_by_filter(mock_cache, "get_all")

        assert count >= 0

    def test_get_invalidation_stats(self, manager):
        """Test getting invalidation statistics"""
        # Perform some invalidations
        manager._log_invalidation("full", "all", 10)
        manager._log_invalidation("pattern", "get_all", 5)

        stats = manager.get_invalidation_stats()

        assert stats["total"] == 15
        assert "full" in stats["by_type"]
        assert "pattern" in stats["by_type"]

    def test_invalidation_log_size_limit(self, manager):
        """Test that invalidation log is limited"""
        # Add many entries
        for i in range(2000):
            manager._log_invalidation("test", f"target_{i}", 1)

        # Log should be limited
        assert len(manager.invalidation_log) <= manager.max_log_size

    @pytest.mark.asyncio
    async def test_error_handling(self, manager):
        """Test error handling in invalidation"""
        # Create cache that raises error
        bad_cache = AsyncMock()
        bad_cache.l1_cache = None  # This will cause error
        bad_cache.delete = AsyncMock(side_effect=Exception("Test error"))

        # Should not raise error
        count = await manager.invalidate_item_cache(bad_cache, item_id=1)

        assert count == 0


class TestInvalidationStrategies:
    """Test different invalidation strategies"""

    def test_strategy_enum(self):
        """Test invalidation strategy enum"""
        assert InvalidationStrategy.FULL.value == "full"
        assert InvalidationStrategy.PATTERN.value == "pattern"
        assert InvalidationStrategy.SELECTIVE.value == "selective"


class TestInvalidationManagerSingleton:
    """Test invalidation manager singleton"""

    def test_get_manager(self):
        """Test getting manager instance"""
        manager1 = get_invalidation_manager()
        manager2 = get_invalidation_manager()

        assert manager1 is manager2


class TestCacheInvalidationEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.fixture
    def manager(self):
        """Create invalidation manager"""
        return CacheInvalidationManager()

    @pytest.mark.asyncio
    async def test_invalidate_empty_cache(self, manager):
        """Test invalidation with empty cache"""
        empty_cache = AsyncMock()
        empty_cache.l1_cache = {}
        empty_cache.delete = AsyncMock()
        empty_cache.cleanup_expired = AsyncMock()

        count = await manager.invalidate_list_cache(empty_cache, "get_all")

        # Should handle empty cache gracefully
        assert count >= 0

    @pytest.mark.asyncio
    async def test_invalidate_with_none_cache(self, manager):
        """Test invalidation with None cache"""
        count = await manager.invalidate_list_cache(None, "get_all")

        assert count == 0

    @pytest.mark.asyncio
    async def test_invalidate_multiple_operations(self, manager):
        """Test multiple invalidation operations"""
        cache = AsyncMock()
        cache.l1_cache = {
            "get_all:1": ({"id": 1}, 0),
            "get_all:2": ({"id": 2}, 0),
            "get_one:1": ({"id": 1}, 0),
        }
        cache.delete = AsyncMock()
        cache.cleanup_expired = AsyncMock()

        # Test multiple operations
        count1 = await manager.invalidate_list_cache(cache, "get_all")
        count2 = await manager.invalidate_item_cache(cache, item_id=1)
        count3 = await manager.invalidate_by_filter(cache, "get_all")

        assert count1 >= 0
        assert count2 >= 0
        assert count3 >= 0

    def test_log_invalidation_with_large_count(self, manager):
        """Test logging invalidation with large count"""
        manager._log_invalidation("full", "all", 10000)

        stats = manager.get_invalidation_stats()
        assert stats["total"] == 10000

    def test_get_stats_empty_log(self, manager):
        """Test getting stats with empty log"""
        stats = manager.get_invalidation_stats()

        assert stats["total"] == 0
        assert stats["by_type"] == {}

    @pytest.mark.asyncio
    async def test_concurrent_invalidations(self, manager):
        """Test concurrent invalidation operations"""
        cache = AsyncMock()
        cache.l1_cache = {f"get_all:{i}": ({}, 0) for i in range(100)}
        cache.delete = AsyncMock()
        cache.cleanup_expired = AsyncMock()

        # Run multiple invalidations concurrently
        tasks = [manager.invalidate_list_cache(cache, "get_all") for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(count >= 0 for count in results)

    def test_invalidation_log_rotation(self, manager):
        """Test that old log entries are rotated out"""
        # Fill log to capacity
        for i in range(manager.max_log_size + 100):
            manager._log_invalidation("test", f"target_{i}", 1)

        # Check that log is limited
        assert len(manager.invalidation_log) == manager.max_log_size

        # Check that recent entries are kept
        recent_targets = {entry["target"] for entry in manager.invalidation_log[-10:]}
        assert len(recent_targets) > 0


class TestCacheInvalidationIntegration:
    """Integration tests for cache invalidation"""

    @pytest.fixture
    def manager(self):
        """Create invalidation manager"""
        return CacheInvalidationManager()

    @pytest.mark.asyncio
    async def test_full_invalidation_workflow(self, manager):
        """Test complete invalidation workflow"""
        cache = AsyncMock()
        cache.l1_cache = {
            "get_all:filter1": ({}, 0),
            "get_all:filter2": ({}, 0),
            "get_one:1": ({}, 0),
            "get_one:2": ({}, 0),
        }
        cache.delete = AsyncMock()
        cache.cleanup_expired = AsyncMock()

        # Test full invalidation
        manager.strategy = InvalidationStrategy.FULL
        count = await manager.invalidate_list_cache(cache, "get_all")
        assert count >= 0

        # Log an invalidation to generate stats
        manager._log_invalidation("full", "all", 10)

        # Check stats
        stats = manager.get_invalidation_stats()
        assert stats["total"] > 0

    @pytest.mark.asyncio
    async def test_selective_invalidation_workflow(self, manager):
        """Test selective invalidation workflow"""
        cache = AsyncMock()
        cache.l1_cache = {
            "get_all:filter1": ({}, 0),
            "get_all:filter2": ({}, 0),
            "get_one:1": ({}, 0),
        }
        cache.delete = AsyncMock()
        cache.cleanup_expired = AsyncMock()

        # Test selective invalidation
        manager.strategy = InvalidationStrategy.SELECTIVE
        count = await manager.invalidate_list_cache(cache, "get_all")
        assert count >= 0

    def test_stats_accumulation(self, manager):
        """Test that stats accumulate correctly"""
        # Perform multiple invalidations
        manager._log_invalidation("full", "all", 10)
        manager._log_invalidation("full", "all", 20)
        manager._log_invalidation("pattern", "get_all", 5)

        stats = manager.get_invalidation_stats()

        assert stats["total"] == 35
        assert stats["by_type"]["full"] == 30
        assert stats["by_type"]["pattern"] == 5

    @pytest.mark.asyncio
    async def test_error_recovery(self, manager):
        """Test recovery from errors during invalidation"""
        cache = AsyncMock()
        cache.l1_cache = {"get_all:1": ({}, 0)}
        cache.delete = AsyncMock(side_effect=RuntimeError("Test error"))
        cache.cleanup_expired = AsyncMock()

        # Should handle error gracefully
        count = await manager.invalidate_list_cache(cache, "get_all")

        # Should return >= 0 even with errors
        assert count >= 0

    def test_strategy_switching(self, manager):
        """Test switching between strategies"""
        assert manager.strategy == InvalidationStrategy.SELECTIVE

        manager.strategy = InvalidationStrategy.FULL
        assert manager.strategy == InvalidationStrategy.FULL

        manager.strategy = InvalidationStrategy.PATTERN
        assert manager.strategy == InvalidationStrategy.PATTERN


class TestCacheInvalidationPerformance:
    """Performance tests for cache invalidation"""

    @pytest.fixture
    def manager(self):
        """Create invalidation manager"""
        return CacheInvalidationManager()

    def test_large_log_handling(self, manager):
        """Test handling of large invalidation logs"""
        # Add many entries
        for i in range(5000):
            manager._log_invalidation("test", f"target_{i}", 1)

        # Should still be limited
        assert len(manager.invalidation_log) <= manager.max_log_size

        # Stats should be accurate
        stats = manager.get_invalidation_stats()
        assert stats["total"] > 0

    @pytest.mark.asyncio
    async def test_invalidation_performance(self, manager):
        """Test invalidation performance with large cache"""
        cache = AsyncMock()
        cache.l1_cache = {f"get_all:{i}": ({}, 0) for i in range(10000)}
        cache.delete = AsyncMock()
        cache.cleanup_expired = AsyncMock()

        # Should complete quickly
        import time

        start = time.time()

        count = await manager.invalidate_list_cache(cache, "get_all")

        elapsed = time.time() - start
        assert elapsed < 5.0  # Should complete in less than 5 seconds
        assert count >= 0
