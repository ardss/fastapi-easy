"""
Optimized database utilities for FastAPI-Easy testing.
Provides high-performance transaction handling, connection pooling, and test data management.
"""

import asyncio
import time
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator, Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from functools import wraps
import threading
import warnings

# SQLAlchemy imports
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.orm import Session, sessionmaker, sessionmaker as async_sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.event import listen
from sqlalchemy.exc import SQLAlchemyError

# Project imports
from fastapi_easy.testing.test_cache import cached, cache_context


@dataclass
class TransactionMetrics:
    """Transaction performance metrics"""
    duration: float
    operations_count: int
    rows_affected: int
    memory_usage_mb: float
    rollback_count: int = 0


class OptimizedTransactionManager:
    """High-performance transaction manager for testing"""

    def __init__(self, engine: Engine, pool_size: int = 5):
        self.engine = engine
        self.pool_size = pool_size
        self.metrics: List[TransactionMetrics] = []
        self._lock = threading.Lock()

    @contextmanager
    def transaction(self, isolation_level: Optional[str] = None) -> Generator[Session, None, None]:
        """Execute operations within optimized transaction"""
        start_time = time.perf_counter()
        operations_count = 0
        rows_affected = 0

        # Configure session for optimal performance
        SessionLocal = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )

        session = SessionLocal()

        # Set isolation level if specified
        if isolation_level:
            session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))

        try:
            # Enable performance optimizations for SQLite
            if self.engine.dialect.name == "sqlite":
                session.execute(text("PRAGMA synchronous = NORMAL"))
                session.execute(text("PRAGMA journal_mode = WAL"))
                session.execute(text("PRAGMA cache_size = 10000"))
                session.execute(text("PRAGMA temp_store = MEMORY"))

            yield session

            # Count operations before commit
            operations_count = len(session.dirty) + len(session.new) + len(session.deleted)
            rows_affected = sum(
                row._sa_instance_state.dict.get('_sa_instance_state', {}).get('rowcount', 0)
                for row in session.dirty
            )

            session.commit()
            session.flush()

        except Exception as e:
            session.rollback()

            # Record rollback metrics
            duration = time.perf_counter() - start_time
            with self._lock:
                self.metrics.append(TransactionMetrics(
                    duration=duration,
                    operations_count=operations_count,
                    rows_affected=rows_affected,
                    memory_usage_mb=0,  # Could be enhanced with memory tracking
                    rollback_count=1
                ))

            raise e
        finally:
            # Record success metrics
            duration = time.perf_counter() - start_time
            with self._lock:
                self.metrics.append(TransactionMetrics(
                    duration=duration,
                    operations_count=operations_count,
                    rows_affected=rows_affected,
                    memory_usage_mb=0,
                    rollback_count=0
                ))

            session.close()

    @asynccontextmanager
    async def async_transaction(self, async_engine: AsyncEngine,
                              isolation_level: Optional[str] = None) -> AsyncGenerator[AsyncSession, None]:
        """Execute operations within optimized async transaction"""
        start_time = time.perf_counter()
        operations_count = 0

        # Configure async session
        async_session = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )

        async with async_session() as session:
            try:
                # SQLite optimizations
                if async_engine.dialect.name == "sqlite":
                    await session.execute(text("PRAGMA synchronous = NORMAL"))
                    await session.execute(text("PRAGMA journal_mode = WAL"))
                    await session.execute(text("PRAGMA cache_size = 10000"))
                    await session.execute(text("PRAGMA temp_store = MEMORY"))

                yield session

                # Count operations
                operations_count = len(session.dirty) + len(session.new) + len(session.deleted)

                await session.commit()
                await session.flush()

            except Exception as e:
                await session.rollback()

                # Record rollback metrics
                duration = time.perf_counter() - start_time
                with self._lock:
                    self.metrics.append(TransactionMetrics(
                        duration=duration,
                        operations_count=operations_count,
                        rows_affected=0,
                        memory_usage_mb=0,
                        rollback_count=1
                    ))

                raise e
            finally:
                # Record success metrics
                duration = time.perf_counter() - start_time
                with self._lock:
                    self.metrics.append(TransactionMetrics(
                        duration=duration,
                        operations_count=operations_count,
                        rows_affected=0,
                        memory_usage_mb=0,
                        rollback_count=0
                    ))

    def batch_insert(self, session: Session, model_class: type,
                    data_list: List[Dict[str, Any]], batch_size: int = 1000) -> int:
        """Optimized batch insert operation"""
        total_inserted = 0

        # Process in batches for optimal performance
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]

            # Use bulk_insert_mappings for better performance
            session.bulk_insert_mappings(model_class, batch)
            total_inserted += len(batch)

            # Flush periodically to avoid memory issues
            if i % (batch_size * 10) == 0:
                session.flush()

        return total_inserted

    async def async_batch_insert(self, session: AsyncSession, model_class: type,
                                data_list: List[Dict[str, Any]], batch_size: int = 1000) -> int:
        """Optimized async batch insert operation"""
        total_inserted = 0

        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i + batch_size]

            await session.run_sync(
                lambda sync_session: sync_session.bulk_insert_mappings(model_class, batch)
            )
            total_inserted += len(batch)

            # Flush periodically
            if i % (batch_size * 10) == 0:
                await session.flush()

        return total_inserted

    def get_metrics_summary(self) -> Dict[str, float]:
        """Get summary of transaction metrics"""
        if not self.metrics:
            return {}

        with self._lock:
            durations = [m.duration for m in self.metrics]
            operations = [m.operations_count for m in self.metrics]
            rollbacks = sum(m.rollback_count for m in self.metrics)

            return {
                "total_transactions": len(self.metrics),
                "avg_duration": sum(durations) / len(durations),
                "max_duration": max(durations),
                "min_duration": min(durations),
                "avg_operations": sum(operations) / len(operations),
                "rollback_rate": rollbacks / len(self.metrics) * 100,
            }


class TestDatabaseFactory:
    """Factory for creating optimized test databases"""

    @staticmethod
    def create_memory_engine() -> Engine:
        """Create optimized in-memory database engine"""
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 20,
            },
            echo=False,
            pool_pre_ping=True,
        )

        # Performance optimizations
        @listen(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA cache_size = 10000")
            cursor.execute("PRAGMA temp_store = MEMORY")
            cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB
            cursor.close()

        return engine

    @staticmethod
    def create_async_memory_engine() -> AsyncEngine:
        """Create optimized async in-memory database engine"""
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 20,
            },
            echo=False,
            pool_pre_ping=True,
        )

        return engine

    @staticmethod
    def create_pooled_engine(database_url: str, pool_size: int = 10) -> Engine:
        """Create database engine with connection pooling"""
        return create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )

    @staticmethod
    def create_async_pooled_engine(database_url: str, pool_size: int = 10) -> AsyncEngine:
        """Create async database engine with connection pooling"""
        return create_async_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )


class TestDataManager:
    """Manager for creating and managing test data"""

    def __init__(self, cache_ttl: float = 3600):
        self.cache_ttl = cache_ttl
        self._factories: Dict[str, Callable] = {}

    def register_factory(self, name: str, factory_func: Callable):
        """Register a test data factory"""
        self._factories[name] = factory_func

    @cached(ttl=3600)
    def get_test_data(self, factory_name: str, count: int = 1) -> List[Any]:
        """Get cached test data from factory"""
        if factory_name not in self._factories:
            raise ValueError(f"Factory '{factory_name}' not registered")

        factory = self._factories[factory_name]
        if count == 1:
            return [factory()]
        else:
            return [factory() for _ in range(count)]

    def create_test_dataset(self, models_data: Dict[type, List[Dict[str, Any]]],
                           session: Session) -> Dict[type, List[Any]]:
        """Create complete test dataset with multiple models"""
        created_objects = {}

        for model_class, data_list in models_data.items():
            objects = []
            for data in data_list:
                obj = model_class(**data)
                session.add(obj)
                objects.append(obj)

            # Flush to get IDs
            session.flush()
            created_objects[model_class] = objects

        return created_objects

    async def async_create_test_dataset(self, models_data: Dict[type, List[Dict[str, Any]]],
                                       session: AsyncSession) -> Dict[type, List[Any]]:
        """Create complete test dataset asynchronously"""
        created_objects = {}

        for model_class, data_list in models_data.items():
            objects = []
            for data in data_list:
                obj = model_class(**data)
                session.add(obj)
                objects.append(obj)

            await session.flush()
            created_objects[model_class] = objects

        return created_objects


# Utility decorators for database testing
def database_test(isolation_level: Optional[str] = None):
    """Decorator for database tests with transaction management"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract engine from kwargs or create one
            engine = kwargs.pop('engine', None)
            if engine is None:
                engine = TestDatabaseFactory.create_memory_engine()
                kwargs['engine'] = engine

            transaction_manager = OptimizedTransactionManager(engine)

            with transaction_manager.transaction(isolation_level=isolation_level) as session:
                kwargs['session'] = session
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract async engine from kwargs or create one
            async_engine = kwargs.pop('async_engine', None)
            if async_engine is None:
                async_engine = TestDatabaseFactory.create_async_memory_engine()
                kwargs['async_engine'] = async_engine

            transaction_manager = OptimizedTransactionManager(None)  # Not used for async

            async with transaction_manager.async_transaction(async_engine, isolation_level) as session:
                kwargs['session'] = session
                return await func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator


def performance_database_test(min_operations: int = 10):
    """Decorator for performance-focused database tests"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            result = func(*args, **kwargs)

            duration = time.perf_counter() - start_time

            if duration > 1.0:  # Warn if test is slow
                warnings.warn(
                    f"Database test {func.__name__} took {duration:.3f}s",
                    PerformanceWarning
                )

            return result

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            result = await func(*args, **kwargs)

            duration = time.perf_counter() - start_time

            if duration > 1.0:  # Warn if test is slow
                warnings.warn(
                    f"Async database test {func.__name__} took {duration:.3f}s",
                    PerformanceWarning
                )

            return result

        return async_wrapper if asyncio.iscoroutinefunction(func) else wrapper
    return decorator


class PerformanceWarning(UserWarning):
    """Warning for performance issues in tests"""
    pass


# Global instances
test_data_manager = TestDataManager()


# Export public API
__all__ = [
    "TransactionMetrics",
    "OptimizedTransactionManager",
    "TestDatabaseFactory",
    "TestDataManager",
    "database_test",
    "performance_database_test",
    "PerformanceWarning",
    "test_data_manager",
]