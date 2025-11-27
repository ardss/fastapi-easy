"""End-to-end test for CRUDRouter route generation"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from fastapi_easy import CRUDRouter
from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter


# Define test models
Base = declarative_base()


class ItemModel(Base):
    """SQLAlchemy model for testing"""
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String(500), nullable=True)


class ItemSchema(BaseModel):
    """Pydantic schema for testing"""
    id: int
    name: str
    price: float
    description: str | None = None
    
    class Config:
        from_attributes = True


@pytest.fixture
async def async_db_session():
    """Create async database session for testing"""
    # Use in-memory SQLite database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    yield async_session_factory
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
def app_with_crud_router(async_db_session):
    """Create FastAPI app with CRUDRouter"""
    app = FastAPI()
    
    # Create adapter
    adapter = SQLAlchemyAdapter(
        model=ItemModel,
        session_factory=async_db_session
    )
    
    # Create CRUD router
    router = CRUDRouter(
        schema=ItemSchema,
        adapter=adapter,
        prefix="/items",
        tags=["Items"]
    )
    
    # Include router in app
    app.include_router(router)
    
    return app


@pytest.mark.asyncio
async def test_crud_router_generates_routes(app_with_crud_router):
    """Test that CRUDRouter generates all CRUD routes"""
    app = app_with_crud_router
    
    # Check that routes are registered
    routes = [route.path for route in app.routes]
    
    # Expected routes
    assert "/items/" in routes  # GET all, POST create, DELETE all
    assert "/items/{id}" in routes  # GET one, PUT update, DELETE one


@pytest.mark.asyncio
async def test_get_all_route(app_with_crud_router):
    """Test GET /items route"""
    client = TestClient(app_with_crud_router)
    
    response = client.get("/items/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_route(app_with_crud_router):
    """Test POST /items route"""
    client = TestClient(app_with_crud_router)
    
    item_data = {
        "id": 1,
        "name": "Test Item",
        "price": 19.99,
        "description": "A test item"
    }
    
    response = client.post("/items/", json=item_data)
    assert response.status_code == 201
    assert response.json()["name"] == "Test Item"
    assert response.json()["price"] == 19.99


@pytest.mark.asyncio
async def test_get_one_route(app_with_crud_router):
    """Test GET /items/{id} route"""
    client = TestClient(app_with_crud_router)
    
    # Create an item first
    item_data = {
        "id": 1,
        "name": "Test Item",
        "price": 19.99
    }
    create_response = client.post("/items/", json=item_data)
    assert create_response.status_code == 201
    
    # Get the item
    item_id = create_response.json()["id"]
    response = client.get(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"


@pytest.mark.asyncio
async def test_update_route(app_with_crud_router):
    """Test PUT /items/{id} route"""
    client = TestClient(app_with_crud_router)
    
    # Create an item first
    item_data = {
        "id": 1,
        "name": "Original Item",
        "price": 19.99
    }
    create_response = client.post("/items/", json=item_data)
    item_id = create_response.json()["id"]
    
    # Update the item
    updated_data = {
        "id": item_id,
        "name": "Updated Item",
        "price": 29.99
    }
    response = client.put(f"/items/{item_id}", json=updated_data)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Item"
    assert response.json()["price"] == 29.99


@pytest.mark.asyncio
async def test_delete_one_route(app_with_crud_router):
    """Test DELETE /items/{id} route"""
    client = TestClient(app_with_crud_router)
    
    # Create an item first
    item_data = {
        "id": 1,
        "name": "Item to Delete",
        "price": 19.99
    }
    create_response = client.post("/items/", json=item_data)
    item_id = create_response.json()["id"]
    
    # Delete the item
    response = client.delete(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Item to Delete"


@pytest.mark.asyncio
async def test_pagination(app_with_crud_router):
    """Test pagination parameters"""
    client = TestClient(app_with_crud_router)
    
    # Create multiple items
    for i in range(5):
        item_data = {
            "id": i + 1,
            "name": f"Item {i}",
            "price": 10.0 + i
        }
        client.post("/items/", json=item_data)
    
    # Test pagination
    response = client.get("/items/?skip=0&limit=2")
    assert response.status_code == 200
    items = response.json()
    assert len(items) <= 2


@pytest.mark.asyncio
async def test_openapi_documentation(app_with_crud_router):
    """Test that OpenAPI documentation is generated"""
    client = TestClient(app_with_crud_router)
    
    response = client.get("/openapi.json")
    assert response.status_code == 200
    
    openapi_spec = response.json()
    
    # Check that paths are documented
    assert "/items/" in openapi_spec["paths"]
    assert "/items/{id}" in openapi_spec["paths"]
    
    # Check that operations are documented
    assert "get" in openapi_spec["paths"]["/items/"]
    assert "post" in openapi_spec["paths"]["/items/"]
    assert "get" in openapi_spec["paths"]["/items/{id}"]
    assert "put" in openapi_spec["paths"]["/items/{id}"]
    assert "delete" in openapi_spec["paths"]["/items/{id}"]
