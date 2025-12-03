"""Tortoise ORM integration test fixtures"""

import pytest
import pytest_asyncio
from tortoise import Model, fields
from tortoise import Tortoise

from fastapi_easy.backends.tortoise import TortoiseAdapter


class Item(Model):
    """Test item model"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.FloatField()

    class Meta:
        table = "items"

    def __repr__(self):
        return f"<Item(id={self.id}, name={self.name}, price={self.price})>"


class UniqueItem(Model):
    """Test item model with unique constraint"""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    price = fields.FloatField()

    class Meta:
        table = "unique_items"

    def __repr__(self):
        return f"<UniqueItem(id={self.id}, name={self.name}, price={self.price})>"


@pytest_asyncio.fixture
async def tortoise_db():
    """Initialize Tortoise ORM with in-memory SQLite"""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["tests.integration.test_tortoise.conftest"]}
    )
    await Tortoise.generate_schemas()

    yield

    await Tortoise.close_connections()


@pytest.fixture
def tortoise_adapter(tortoise_db):
    """Create Tortoise adapter"""
    return TortoiseAdapter(
        model=Item,
        session_factory=None,  # Tortoise doesn't use session factory
        pk_field="id",
    )


@pytest.fixture
def unique_item_adapter(tortoise_db):
    """Create Tortoise adapter for unique items"""
    return TortoiseAdapter(
        model=UniqueItem,
        session_factory=None,
        pk_field="id",
    )


@pytest_asyncio.fixture
async def sample_items(tortoise_db):
    """Create sample items"""
    items = [
        Item(name="apple", price=10.0),
        Item(name="banana", price=5.0),
        Item(name="orange", price=8.0),
        Item(name="grape", price=15.0),
        Item(name="mango", price=12.0),
    ]

    for item in items:
        await item.save()

    yield items

    # Cleanup
    await Item.all().delete()
