"""Global pytest configuration and fixtures"""

import pytest
from unittest.mock import AsyncMock
from pydantic import BaseModel

from fastapi_easy.core.adapters import ORMAdapter
from fastapi_easy.core.config import CRUDConfig
from fastapi_easy.core.crud_router import CRUDRouter


# ============================================================================
# Test Models
# ============================================================================

class ItemSchema(BaseModel):
    """Test item schema"""
    id: int
    name: str
    price: float
    
    class Config:
        from_attributes = True


class UserSchema(BaseModel):
    """Test user schema"""
    id: int
    username: str
    email: str
    
    class Config:
        from_attributes = True


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_adapter():
    """Mock ORM adapter for testing"""
    adapter = AsyncMock(spec=ORMAdapter)
    
    # Default return values
    adapter.get_all.return_value = []
    adapter.get_one.return_value = None
    adapter.create.return_value = {"id": 1, "name": "test", "price": 10.0}
    adapter.update.return_value = {"id": 1, "name": "updated", "price": 20.0}
    adapter.delete_one.return_value = {"id": 1, "name": "test", "price": 10.0}
    adapter.delete_all.return_value = []
    adapter.count.return_value = 0
    
    return adapter


@pytest.fixture
def mock_adapter_with_data():
    """Mock ORM adapter with test data"""
    adapter = AsyncMock(spec=ORMAdapter)
    
    test_items = [
        {"id": 1, "name": "apple", "price": 10.0},
        {"id": 2, "name": "banana", "price": 5.0},
        {"id": 3, "name": "orange", "price": 8.0},
    ]
    
    adapter.get_all.return_value = test_items
    adapter.get_one.side_effect = lambda id: next(
        (item for item in test_items if item["id"] == id), None
    )
    adapter.count.return_value = len(test_items)
    
    return adapter


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def default_config():
    """Default CRUD configuration"""
    return CRUDConfig(
        enable_filters=True,
        enable_sorters=True,
        enable_pagination=True,
        default_limit=10,
        max_limit=100,
    )


@pytest.fixture
def minimal_config():
    """Minimal CRUD configuration"""
    return CRUDConfig(
        enable_filters=False,
        enable_sorters=False,
        enable_pagination=False,
    )


# ============================================================================
# Router Fixtures
# ============================================================================

@pytest.fixture
def crud_router(mock_adapter, default_config):
    """CRUD router with mock adapter"""
    return CRUDRouter(
        schema=ItemSchema,
        adapter=mock_adapter,
        config=default_config,
    )


@pytest.fixture
def crud_router_with_data(mock_adapter_with_data, default_config):
    """CRUD router with mock adapter and test data"""
    return CRUDRouter(
        schema=ItemSchema,
        adapter=mock_adapter_with_data,
        config=default_config,
    )


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
