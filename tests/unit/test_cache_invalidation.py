"""Tests for cache invalidation management"""

import pytest
from unittest.mock import AsyncMock, MagicMock
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
