"""Tests for optimized adapter"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi_easy.core.optimized_adapter import (
    OptimizedSQLAlchemyAdapter,
    create_optimized_adapter,
)


class TestOptimizedAdapter:
    """Test OptimizedSQLAlchemyAdapter"""

    @pytest.fixture
    def mock_adapter(self):
        """Create mock base adapter"""
        adapter = AsyncMock()
        adapter.model = MagicMock()
        return adapter

    @pytest.mark.asyncio
    async def test_get_one_with_cache(self, mock_adapter):
        """Test get_one with caching"""
        mock_adapter.get_one.return_value = {"id": 1, "name": "test"}

        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=True)

        # First call: cache miss
        result1 = await optimized.get_one(1)
        assert result1 == {"id": 1, "name": "test"}
        assert mock_adapter.get_one.call_count == 1

        # Second call: cache hit
        result2 = await optimized.get_one(1)
        assert result2 == {"id": 1, "name": "test"}
        assert mock_adapter.get_one.call_count == 1  # Not called again

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_update(self, mock_adapter):
        """Test cache invalidation on update"""
        mock_adapter.get_one.return_value = {"id": 1, "name": "old"}
        mock_adapter.update.return_value = {"id": 1, "name": "new"}

        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=True)

        # Get item (cached)
        result1 = await optimized.get_one(1)
        assert result1["name"] == "old"

        # Update item
        await optimized.update(1, {"name": "new"})

        # Get item again (should query DB, not cache)
        mock_adapter.get_one.return_value = {"id": 1, "name": "new"}
        result2 = await optimized.get_one(1)
        assert result2["name"] == "new"
        assert mock_adapter.get_one.call_count == 2  # Called again

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_delete(self, mock_adapter):
        """Test cache invalidation on delete"""
        mock_adapter.get_one.return_value = {"id": 1, "name": "test"}
        mock_adapter.delete_one.return_value = True

        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=True)

        # Get item (cached)
        await optimized.get_one(1)

        # Delete item
        await optimized.delete_one(1)

        # Get item again (should query DB)
        mock_adapter.get_one.return_value = None
        result = await optimized.get_one(1)
        assert result is None
        assert mock_adapter.get_one.call_count == 2  # Called again

    @pytest.mark.asyncio
    async def test_cache_invalidation_on_create(self, mock_adapter):
        """Test cache invalidation on create"""
        call_count = 0

        async def get_all_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [{"id": 1}]
            else:
                return [{"id": 1}, {"id": 2}]

        mock_adapter.get_all.side_effect = get_all_side_effect
        mock_adapter.create.return_value = {"id": 2}

        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=True)

        # Get all (cached)
        result1 = await optimized.get_all({}, {}, {"skip": 0, "limit": 10})
        assert len(result1) == 1

        # Create new item
        await optimized.create({"name": "new"})

        # Get all again (should query DB due to cache invalidation)
        result2 = await optimized.get_all({}, {}, {"skip": 0, "limit": 10})
        assert len(result2) == 2
        assert call_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_cache_clear_on_delete_all(self, mock_adapter):
        """Test cache clear on delete_all"""
        mock_adapter.get_one.return_value = {"id": 1}
        mock_adapter.delete_all.return_value = 1

        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=True)

        # Get item (cached)
        await optimized.get_one(1)

        # Delete all
        await optimized.delete_all()

        # Get item again (should query DB)
        mock_adapter.get_one.return_value = None
        result = await optimized.get_one(1)
        assert result is None
        assert mock_adapter.get_one.call_count == 2

    @pytest.mark.asyncio
    async def test_get_all_with_cache(self, mock_adapter):
        """Test get_all with caching"""
        mock_adapter.get_all.return_value = [{"id": 1}, {"id": 2}]

        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=True)

        # First call: cache miss
        result1 = await optimized.get_all({}, {}, {"skip": 0, "limit": 10})
        assert len(result1) == 2
        assert mock_adapter.get_all.call_count == 1

        # Second call: cache hit
        result2 = await optimized.get_all({}, {}, {"skip": 0, "limit": 10})
        assert len(result2) == 2
        assert mock_adapter.get_all.call_count == 1  # Not called again

    @pytest.mark.asyncio
    async def test_count_with_cache(self, mock_adapter):
        """Test count with caching"""
        mock_adapter.count.return_value = 5

        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=True)

        # First call: cache miss
        result1 = await optimized.count({})
        assert result1 == 5
        assert mock_adapter.count.call_count == 1

        # Second call: cache hit
        result2 = await optimized.count({})
        assert result2 == 5
        assert mock_adapter.count.call_count == 1  # Not called again

    def test_cache_stats(self, mock_adapter):
        """Test cache statistics"""
        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=True)

        stats = optimized.get_cache_stats()
        assert stats is not None
        assert "l1_stats" in stats
        assert "l2_stats" in stats

    @pytest.mark.asyncio
    async def test_cache_disabled(self, mock_adapter):
        """Test with cache disabled"""
        mock_adapter.get_one.return_value = {"id": 1}

        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=False)

        # Both calls should hit the adapter
        await optimized.get_one(1)
        await optimized.get_one(1)

        assert mock_adapter.get_one.call_count == 2  # Called twice

    def test_cache_stats_disabled(self, mock_adapter):
        """Test cache stats when disabled"""
        optimized = OptimizedSQLAlchemyAdapter(mock_adapter, enable_cache=False)

        stats = optimized.get_cache_stats()
        assert stats is None


class TestFactoryFunction:
    """Test factory function"""

    def test_create_optimized_adapter(self):
        """Test creating optimized adapter"""
        mock_adapter = AsyncMock()
        mock_adapter.model = MagicMock()

        optimized = create_optimized_adapter(
            mock_adapter,
            enable_cache=True,
            cache_config={"l1_size": 500},
        )

        assert isinstance(optimized, OptimizedSQLAlchemyAdapter)
        assert optimized.enable_cache is True
