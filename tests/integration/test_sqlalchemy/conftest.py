"""SQLAlchemy integration test fixtures"""

import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter


class Base(DeclarativeBase):
    """SQLAlchemy base class"""


class Item(Base):
    """Test item model"""

    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)

    def __repr__(self):
        return f"<Item(id={self.id}, name={self.name}, price={self.price})>"


class TransactionItem(Base):
    """Test item model for transaction tests"""

    __tablename__ = "transaction_items"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    price = Column(Float, nullable=False)
    quantity = Column(Integer, default=0)

    def __repr__(self):
        return f"<TransactionItem(id={self.id}, name={self.name}, price={self.price}, quantity={self.quantity})>"


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session_factory(db_engine):
    """Create async session factory"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session


@pytest.fixture
def sqlalchemy_adapter(db_session_factory):
    """Create SQLAlchemy adapter"""
    return SQLAlchemyAdapter(
        model=Item,
        session_factory=db_session_factory,
        pk_field="id",
    )


@pytest_asyncio.fixture
async def sample_items(db_session_factory):
    """Create sample items"""
    async with db_session_factory() as session:
        items = [
            Item(name="apple", price=10.0),
            Item(name="banana", price=5.0),
            Item(name="orange", price=8.0),
            Item(name="grape", price=15.0),
            Item(name="mango", price=12.0),
        ]
        session.add_all(items)
        await session.commit()

        # Refresh to get IDs
        for item in items:
            await session.refresh(item)

        yield items


@pytest.fixture
def transaction_adapter(db_session_factory):
    """Create SQLAlchemy adapter for transaction tests"""
    return SQLAlchemyAdapter(
        model=TransactionItem,
        session_factory=db_session_factory,
        pk_field="id",
    )


@pytest_asyncio.fixture
async def transaction_sample_data(db_session_factory):
    """Create sample data for transaction tests"""
    async with db_session_factory() as session:
        items = [
            TransactionItem(name="item1", price=10.0, quantity=100),
            TransactionItem(name="item2", price=20.0, quantity=50),
            TransactionItem(name="item3", price=30.0, quantity=75),
        ]
        session.add_all(items)
        await session.commit()

        # Refresh to get IDs
        for item in items:
            await session.refresh(item)

        yield items
