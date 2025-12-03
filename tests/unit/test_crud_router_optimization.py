"""Tests for optimized CRUD router"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi_easy.crud_router_optimization import (
    create_optimized_crud_router,
)
from fastapi_easy.core.optimized_adapter import OptimizedSQLAlchemyAdapter


class TestOptimizedCRUDRouterIntegration:
    """Test OptimizedCRUDRouter integration"""

    def test_create_optimized_crud_router_with_optimization(self):
        """Test creating optimized CRUD router with optimization enabled"""
        # Create mock backend
        mock_backend = AsyncMock()
        mock_backend.model = MagicMock()

        # Create mock schema
        mock_schema = MagicMock()
        mock_schema.__name__ = "TestSchema"

        # Create router with optimization
        with patch('fastapi_easy.crud_router_optimization.CRUDRouter.__init__', return_value=None):
            router = create_optimized_crud_router(
                schema=mock_schema,
                backend=mock_backend,
                enable_optimization=True,
            )

        # Verify optimization is enabled
        assert router.enable_optimization is True
        assert router.optimized_backend is not None
        assert isinstance(router.optimized_backend, OptimizedSQLAlchemyAdapter)

    def test_create_optimized_crud_router_without_optimization(self):
        """Test creating optimized CRUD router without optimization"""
        # Create mock backend
        mock_backend = AsyncMock()
        mock_backend.model = MagicMock()

        # Create mock schema
        mock_schema = MagicMock()
        mock_schema.__name__ = "TestSchema"

        # Create router without optimization
        with patch('fastapi_easy.crud_router_optimization.CRUDRouter.__init__', return_value=None):
            router = create_optimized_crud_router(
                schema=mock_schema,
                backend=mock_backend,
                enable_optimization=False,
            )

        # Verify optimization is disabled
        assert router.enable_optimization is False
        assert router.optimized_backend is None

    @pytest.mark.asyncio
    async def test_optimized_adapter_wrapping(self):
        """Test that backend is wrapped with optimization"""
        # Create mock backend
        mock_backend = AsyncMock()
        mock_backend.model = MagicMock()

        # Create mock schema
        mock_schema = MagicMock()
        mock_schema.__name__ = "TestSchema"

        # Create router with optimization
        with patch('fastapi_easy.crud_router_optimization.CRUDRouter.__init__', return_value=None):
            router = create_optimized_crud_router(
                schema=mock_schema,
                backend=mock_backend,
                enable_optimization=True,
            )

        # Verify backend is wrapped
        assert isinstance(router.optimized_backend, OptimizedSQLAlchemyAdapter)
        assert router.optimized_backend.base_adapter is mock_backend
