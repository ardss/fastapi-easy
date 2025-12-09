"""Performance test fixtures"""

import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean, DateTime, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship

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


class User(Base):
    """User model for comprehensive performance testing"""
    __tablename__ = "performance_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    login_count = Column(Integer, default=0)

    # Relationships
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Post(Base):
    """Post model for comprehensive performance testing"""
    __tablename__ = "performance_posts"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("performance_users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    view_count = Column(Integer, default=0)

    # Relationships
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    tags = relationship("PostTag", back_populates="post", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title[:50]}...')>"


class Comment(Base):
    """Comment model for comprehensive performance testing"""
    __tablename__ = "performance_comments"

    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("performance_users.id"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("performance_posts.id"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("performance_comments.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    author = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship("Comment", cascade="all, delete-orphan", overlaps="parent")

    def __repr__(self):
        return f"<Comment(id={self.id}, content='{self.content[:50]}...')>"


class Like(Base):
    """Like model for comprehensive performance testing"""
    __tablename__ = "performance_likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("performance_users.id"), nullable=False)
    post_id = Column(Integer, ForeignKey("performance_posts.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")


class Tag(Base):
    """Tag model for comprehensive performance testing"""
    __tablename__ = "performance_tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    posts = relationship("PostTag", back_populates="tag", cascade="all, delete-orphan")


class PostTag(Base):
    """Post-Tag relationship model for comprehensive performance testing"""
    __tablename__ = "performance_post_tags"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("performance_posts.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("performance_tags.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    post = relationship("Post", back_populates="tags")
    tag = relationship("Tag", back_populates="posts")


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


@pytest_asyncio.fixture
async def shared_perf_db_engine():
    """Shared performance test database engine with all models"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def shared_perf_db_session_factory(shared_perf_db_engine):
    """Shared async session factory for performance tests"""
    async_session = async_sessionmaker(
        shared_perf_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return async_session


@pytest.fixture
def perf_user_adapter(shared_perf_db_session_factory):
    """Create OptimizedSQLAlchemyAdapter for User model"""
    from fastapi_easy.backends.sqlalchemy_optimized import OptimizedSQLAlchemyAdapter
    from fastapi_easy.core.optimization_config import OptimizationConfig

    performance_config = OptimizationConfig(
        enable_query_cache=True,
        enable_session_cache=True,
        enable_result_cache=True,
        cache_size=10000,
        query_timeout=30,
        enable_async=True,
        enable_connection_pooling=True,
        pool_size=10,
        max_overflow=20,
    )

    return OptimizedSQLAlchemyAdapter(
        model=User,
        database_url="sqlite+aiosqlite:///:memory:",
        pk_field="id",
        optimization_config=performance_config,
    )


@pytest.fixture
def perf_post_adapter(shared_perf_db_session_factory):
    """Create OptimizedSQLAlchemyAdapter for Post model"""
    from fastapi_easy.backends.sqlalchemy_optimized import OptimizedSQLAlchemyAdapter
    from fastapi_easy.core.optimization_config import OptimizationConfig

    performance_config = OptimizationConfig(
        enable_query_cache=True,
        enable_session_cache=True,
        enable_result_cache=True,
        cache_size=10000,
        query_timeout=30,
        enable_async=True,
        enable_connection_pooling=True,
        pool_size=10,
        max_overflow=20,
    )

    return OptimizedSQLAlchemyAdapter(
        model=Post,
        database_url="sqlite+aiosqlite:///:memory:",
        pk_field="id",
        optimization_config=performance_config,
    )


@pytest.fixture
def perf_comment_adapter(shared_perf_db_session_factory):
    """Create OptimizedSQLAlchemyAdapter for Comment model"""
    from fastapi_easy.backends.sqlalchemy_optimized import OptimizedSQLAlchemyAdapter
    from fastapi_easy.core.optimization_config import OptimizationConfig

    performance_config = OptimizationConfig(
        enable_query_cache=True,
        enable_session_cache=True,
        enable_result_cache=True,
        cache_size=10000,
        query_timeout=30,
        enable_async=True,
        enable_connection_pooling=True,
        pool_size=10,
        max_overflow=20,
    )

    return OptimizedSQLAlchemyAdapter(
        model=Comment,
        database_url="sqlite+aiosqlite:///:memory:",
        pk_field="id",
        optimization_config=performance_config,
    )
