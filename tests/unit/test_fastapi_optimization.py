"""Tests for FastAPI optimization integration"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi_easy.integrations.fastapi_optimization import (
    FastAPIOptimization,
    OptimizationConfig,
    setup_optimization,
)


class TestOptimizationConfig:
    """Test OptimizationConfig class"""

    def test_default_config(self):
        """Test default configuration"""
        config = OptimizationConfig()

        assert config.enable_cache is True
        assert config.enable_async is True
        assert config.enable_monitoring is True
        assert config.enable_health_check is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = OptimizationConfig(
            enable_cache=False,
            enable_monitoring=False,
        )

        assert config.enable_cache is False
        assert config.enable_monitoring is False


class TestFastAPIOptimization:
    """Test FastAPIOptimization class"""

    def test_initialization(self):
        """Test initialization"""
        app = FastAPI()
        config = OptimizationConfig()

        optimization = FastAPIOptimization(app, config)

        assert optimization.app is app
        assert optimization.config is config
        assert len(optimization.adapters) == 0

    def test_register_adapter(self):
        """Test registering adapter"""
        app = FastAPI()
        optimization = FastAPIOptimization(app)

        mock_adapter = AsyncMock()
        optimization.register_adapter("test", mock_adapter)

        assert "test" in optimization.adapters
        assert optimization.adapters["test"] is mock_adapter

    def test_get_adapter(self):
        """Test getting adapter"""
        app = FastAPI()
        optimization = FastAPIOptimization(app)

        mock_adapter = AsyncMock()
        optimization.register_adapter("test", mock_adapter)

        retrieved = optimization.get_adapter("test")

        assert retrieved is mock_adapter

    def test_get_adapter_not_found(self):
        """Test getting non-existent adapter"""
        app = FastAPI()
        optimization = FastAPIOptimization(app)

        retrieved = optimization.get_adapter("nonexistent")

        assert retrieved is None

    def test_health_check_endpoint_enabled(self):
        """Test health check endpoint when enabled"""
        app = FastAPI()
        config = OptimizationConfig(enable_health_check=True)

        optimization = FastAPIOptimization(app, config)

        # Check if route was added
        routes = [route.path for route in app.routes]
        assert "/health/optimization" in routes

    def test_health_check_endpoint_disabled(self):
        """Test health check endpoint when disabled"""
        app = FastAPI()
        config = OptimizationConfig(enable_health_check=False)

        optimization = FastAPIOptimization(app, config)

        # Check if route was not added
        routes = [route.path for route in app.routes]
        assert "/health/optimization" not in routes


class TestSetupOptimization:
    """Test setup_optimization function"""

    def test_setup_optimization(self):
        """Test setup optimization"""
        app = FastAPI()

        optimization = setup_optimization(
            app,
            enable_cache=True,
            enable_monitoring=True,
        )

        assert isinstance(optimization, FastAPIOptimization)
        assert optimization.config.enable_cache is True
        assert optimization.config.enable_monitoring is True

    def test_setup_optimization_with_config(self):
        """Test setup optimization with custom config"""
        app = FastAPI()

        optimization = setup_optimization(
            app,
            enable_cache=False,
            cache_config={"l1_size": 500},
        )

        assert optimization.config.enable_cache is False
