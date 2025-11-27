"""SQLAlchemy adapter performance tests"""

import pytest
import pytest_asyncio
import time
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter


class Base(DeclarativeBase):
    """SQLAlchemy base class"""
    pass


class Item(Base):
    """Test item model"""
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)


@pytest_asyncio.fixture
async def perf_db_engine():
    """Create performance test database engine"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def perf_db_session_factory(perf_db_engine):
    """Create async session factory"""
    async_session = async_sessionmaker(
        perf_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session


@pytest.fixture
def perf_adapter(perf_db_session_factory):
    """Create SQLAlchemy adapter for performance testing"""
    return SQLAlchemyAdapter(
        model=Item,
        session_factory=perf_db_session_factory,
        pk_field="id",
    )


@pytest_asyncio.fixture
async def perf_sample_data(perf_db_session_factory):
    """Create sample data for performance testing"""
    async with perf_db_session_factory() as session:
        items = [
            Item(name=f"item_{i}", price=float(i * 10))
            for i in range(100)
        ]
        session.add_all(items)
        await session.commit()
        
        for item in items:
            await session.refresh(item)
        
        yield items


@pytest.mark.asyncio
class TestSQLAlchemyPerformance:
    """Performance tests for SQLAlchemy adapter"""
    
    async def test_create_single_item(self, perf_adapter):
        """Test creating a single item"""
        result = await perf_adapter.create({"name": "test", "price": 10.0})
        assert result is not None
        assert result.name == "test"
    
    async def test_get_all_items(self, perf_adapter, perf_sample_data):
        """Test getting all items"""
        result = await perf_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 100},
        )
        assert len(result) == 100
    
    async def test_get_one_item(self, perf_adapter, perf_sample_data):
        """Test getting a single item"""
        item_id = perf_sample_data[0].id
        result = await perf_adapter.get_one(item_id)
        assert result is not None
        assert result.id == item_id
    
    async def test_update_item(self, perf_adapter, perf_sample_data):
        """Test updating an item"""
        item_id = perf_sample_data[0].id
        result = await perf_adapter.update(item_id, {"name": "updated"})
        assert result is not None
        assert result.name == "updated"
    
    async def test_delete_item(self, perf_adapter, perf_sample_data):
        """Test deleting an item"""
        item_id = perf_sample_data[-1].id
        result = await perf_adapter.delete_one(item_id)
        assert result is not None
        assert result.id == item_id
    
    async def test_count_items(self, perf_adapter, perf_sample_data):
        """Test counting items"""
        result = await perf_adapter.count({})
        assert result == 100
    
    async def test_filter_items(self, perf_adapter, perf_sample_data):
        """Test filtering items"""
        filters = {
            "price__gt": {"field": "price", "operator": "gt", "value": 500}
        }
        result = await perf_adapter.get_all(
            filters=filters,
            sorts={},
            pagination={"skip": 0, "limit": 100},
        )
        assert len(result) > 0
