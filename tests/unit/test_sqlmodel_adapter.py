
import pytest
from typing import Optional
try:
    from sqlmodel import SQLModel, Field
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
except ImportError:
    pytest.skip("SQLModel not installed", allow_module_level=True)

from fastapi_easy.backends.sqlmodel import SQLModelAdapter

# Define a test model
class Hero(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    secret_name: str
    age: Optional[int] = None

@pytest.fixture
async def session_factory():
    # Use in-memory SQLite database
    # Note: aiosqlite is required for async sqlite
    try:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    except ImportError:
        pytest.skip("aiosqlite not installed", allow_module_level=True)

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    yield async_session

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_sqlmodel_adapter_crud(session_factory):
    # Initialize adapter
    adapter = SQLModelAdapter(model=Hero, session_factory=session_factory)

    # 1. Create
    hero_data = {"name": "Deadpond", "secret_name": "Dive Wilson", "age": 30}
    created_hero = await adapter.create(hero_data)
    assert created_hero.id is not None
    assert created_hero.name == "Deadpond"

    # 2. Get One
    hero = await adapter.get_one(created_hero.id)
    assert hero is not None
    assert hero.id == created_hero.id

    # 3. Get All
    heroes = await adapter.get_all(filters={}, sorts={}, pagination={})
    assert len(heroes) == 1
    assert heroes[0].name == "Deadpond"

    # 4. Update
    updated_hero = await adapter.update(created_hero.id, {"age": 31})
    assert updated_hero.age == 31

    # Verify update in DB
    hero_check = await adapter.get_one(created_hero.id)
    assert hero_check.age == 31

    # 5. Count
    count = await adapter.count({})
    assert count == 1

    # 6. Delete
    deleted_hero = await adapter.delete_one(created_hero.id)
    assert deleted_hero.id == created_hero.id

    # Verify deletion
    hero_check = await adapter.get_one(created_hero.id)
    assert hero_check is None

    count = await adapter.count({})
    assert count == 0

@pytest.mark.asyncio
async def test_sqlmodel_adapter_filtering(session_factory):
    adapter = SQLModelAdapter(model=Hero, session_factory=session_factory)

    # Create multiple heroes
    await adapter.create({"name": "Spider-Boy", "secret_name": "Pedro Parqueador", "age": 18})
    await adapter.create({"name": "Rusty-Man", "secret_name": "Tommy Stark", "age": 48})

    # Filter by age > 20
    filters = {
        "age_filter": {
            "field": "age",
            "operator": "gt",
            "value": 20
        }
    }

    results = await adapter.get_all(filters=filters, sorts={}, pagination={})
    assert len(results) == 1
    assert results[0].name == "Rusty-Man"
