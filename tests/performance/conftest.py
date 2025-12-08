"""Performance test fixtures"""

import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter


class Base(DeclarativeBase):
    """SQLAlchemy base class"""


class PerformanceItem(Base):
    """Test item model for performance tests"""

    __tablename__ = "performance_items"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=0)

    def __repr__(self):
        return f"<PerformanceItem(id={self.id}, name={self.name}, price={self.price})>"


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
    """Create async session factory for performance tests"""
    async_session = async_sessionmaker(
        perf_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session


@pytest.fixture
def perf_sqlalchemy_adapter(perf_db_session_factory):
    """Create SQLAlchemy adapter for performance tests"""
    return SQLAlchemyAdapter(
        model=PerformanceItem,
        session_factory=perf_db_session_factory,
        pk_field="id",
    )


@pytest_asyncio.fixture
async def large_dataset(perf_db_session_factory):
    """Create large dataset for performance tests (5000 items for faster setup)"""
    async with perf_db_session_factory() as session:
        # Create 5000 items (reduced from 10000 for faster test setup)
        items = [
            PerformanceItem(
                name=f"item_{i}",
                description=f"Description for item {i}",
                price=float(i % 1000),
                quantity=i % 100,
            )
            for i in range(5000)
        ]
        session.add_all(items)
        await session.commit()

        yield items
