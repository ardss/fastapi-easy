"""
Optimized Database Operations Module

Provides high-performance database operations with:
- Connection pooling optimization
- Query batching
- Smart caching
- Performance monitoring
- Async/await best practices
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import wraps
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
)

from sqlalchemy import (
    delete,
    event,
    insert,
    text,
    update,
)
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
    TimeoutError,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)


@dataclass
class PerformanceMetrics:
    """Track database performance metrics"""

    # Query metrics
    query_count: int = 0
    total_time: float = 0.0
    slow_queries: int = 0
    timeout_queries: int = 0
    failed_queries: int = 0

    # Connection metrics
    active_connections: int = 0
    pool_hits: int = 0
    pool_misses: int = 0

    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_size: int = 0

    # Batch metrics
    batch_operations: int = 0
    batch_size: int = 0

    @property
    def avg_query_time(self) -> float:
        """Calculate average query time"""
        return self.total_time / max(1, self.query_count)

    @property
    def success_rate(self) -> float:
        """Calculate query success rate"""
        total = self.query_count
        failed = self.failed_queries
        return ((total - failed) / max(1, total)) * 100

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / max(1, total)) * 100

    def reset(self) -> None:
        """Reset all metrics"""
        for field_name in self.__dataclass_fields__:
            setattr(self, field_name, 0)


class QueryCache:
    """
    High-performance query cache with LRU eviction
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key in self._cache:
                value, expiry_time = self._cache[key]
                if time.time() < expiry_time:
                    self._access_times[key] = time.time()
                    return value
                else:
                    # Expired
                    del self._cache[key]
                    del self._access_times[key]
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        async with self._lock:
            expiry_time = time.time() + (ttl or self.default_ttl)

            # Check if we need to evict
            if len(self._cache) >= self.max_size and key not in self._cache:
                await self._evict_lru()

            self._cache[key] = (value, expiry_time)
            self._access_times[key] = time.time()

    async def _evict_lru(self) -> None:
        """Evict least recently used item"""
        if not self._access_times:
            return

        # Find least recently used key
        lru_key = min(self._access_times, key=self._access_times.get)

        # Remove from cache
        if lru_key in self._cache:
            del self._cache[lru_key]
        del self._access_times[lru_key]

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        async with self._lock:
            to_remove = [k for k in self._cache if pattern in k]
            for key in to_remove:
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]
            return len(to_remove)

    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)


class BatchProcessor:
    """
    Efficiently batch database operations
    """

    def __init__(self, batch_size: int = 1000, flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._operations: List[Tuple[str, Any, Dict[str, Any]]] = []
        self._last_flush = time.time()
        self._lock = asyncio.Lock()

    async def add_operation(
        self, operation_type: str, model: Type[T], data: Dict[str, Any]
    ) -> None:
        """Add operation to batch"""
        async with self._lock:
            self._operations.append((operation_type, model, data))

            # Auto-flush if needed
            if (
                len(self._operations) >= self.batch_size
                or time.time() - self._last_flush >= self.flush_interval
            ):
                await self.flush()

    async def flush(self) -> None:
        """Flush all pending operations"""
        if not self._operations:
            return

        # Group operations by type and model
        grouped: Dict[Tuple[str, Type[T]], List[Dict[str, Any]]] = {}
        for op_type, model, data in self._operations:
            key = (op_type, model)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(data)

        # Execute grouped operations
        for (op_type, model), items in grouped.items():
            if op_type == "insert":
                await self._batch_insert(model, items)
            elif op_type == "update":
                await self._batch_update(model, items)
            elif op_type == "delete":
                await self._batch_delete(model, items)

        # Reset
        self._operations.clear()
        self._last_flush = time.time()

    async def _batch_insert(self, model: Type[T], items: List[Dict[str, Any]]) -> None:
        """Execute batch insert"""
        # Implementation would depend on your database backend
        # This is a placeholder for the actual implementation
        logger.debug(f"Batch inserting {len(items)} {model.__name__} items")

    async def _batch_update(self, model: Type[T], items: List[Dict[str, Any]]) -> None:
        """Execute batch update"""
        logger.debug(f"Batch updating {len(items)} {model.__name__} items")

    async def _batch_delete(self, model: Type[T], items: List[Dict[str, Any]]) -> None:
        """Execute batch delete"""
        logger.debug(f"Batch deleting {len(items)} {model.__name__} items")


def monitor_performance(metrics: PerformanceMetrics):
    """Decorator to monitor database performance"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            metrics.query_count += 1

            try:
                result = await func(*args, **kwargs)

                # Track slow queries (> 1 second)
                elapsed = time.time() - start_time
                if elapsed > 1.0:
                    metrics.slow_queries += 1
                    logger.warning(f"Slow query detected: {func.__name__} took {elapsed:.2f}s")

                return result

            except TimeoutError:
                metrics.timeout_queries += 1
                raise
            except (SQLAlchemyError, IntegrityError, OperationalError):
                metrics.failed_queries += 1
                raise
            finally:
                metrics.total_time += time.time() - start_time

        return wrapper

    return decorator


class OptimizedDatabaseManager:
    """
    High-performance database manager with optimizations
    """

    def __init__(
        self,
        database_url: str,
        pool_size: int = 20,
        max_overflow: int = 30,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        cache_size: int = 1000,
        cache_ttl: int = 3600,
        batch_size: int = 1000,
        echo: bool = False,
    ):
        """Initialize optimized database manager"""
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.echo = echo

        # Performance tracking
        self.metrics = PerformanceMetrics()

        # Initialize engine
        self.engine = self._create_engine()

        # Initialize session factory
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        # Initialize cache
        self.cache = QueryCache(max_size=cache_size, default_ttl=cache_ttl)

        # Initialize batch processor
        self.batch_processor = BatchProcessor(batch_size=batch_size)

        # Connection tracking
        self._active_connections: Set[AsyncSession] = set()
        self._connection_lock = asyncio.Lock()

    def _create_engine(self) -> AsyncEngine:
        """Create optimized async engine"""
        # Database-specific optimizations
        connect_args = {}

        if "postgresql" in self.database_url:
            connect_args.update(
                {
                    "command_timeout": self.pool_timeout,
                    "server_settings": {
                        "application_name": "fastapi-easy-optimized",
                        "jit": "off",  # Disable JIT for better query planning
                        "timezone": "UTC",
                    },
                }
            )
        elif "mysql" in self.database_url:
            connect_args.update(
                {
                    "charset": "utf8mb4",
                    "use_unicode": True,
                    "sql_mode": "STRICT_TRANS_TABLES",
                }
            )
        elif "sqlite" in self.database_url:
            connect_args.update(
                {
                    "check_same_thread": False,
                    "timeout": self.pool_timeout,
                }
            )

        engine = create_async_engine(
            self.database_url,
            poolclass=QueuePool,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_timeout=self.pool_timeout,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=True,
            echo=self.echo,
            connect_args=connect_args,
        )

        # Add event listeners for monitoring
        event.listen(engine.sync_engine, "connect", self._on_connect)
        event.listen(engine.sync_engine, "checkout", self._on_checkout)
        event.listen(engine.sync_engine, "checkin", self._on_checkin)

        return engine

    def _on_connect(self, connection, branch):
        """Handle connection events"""
        pass

    def _on_checkout(self, connection, branch, connection_record):
        """Track connection checkout"""
        self.metrics.pool_hits += 1

    def _on_checkin(self, connection, connection_record):
        """Track connection checkin"""
        pass

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session with automatic cleanup"""
        session = self.session_factory()

        try:
            async with self._connection_lock:
                self._active_connections.add(session)
                self.metrics.active_connections = len(self._active_connections)

            yield session

        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()
            async with self._connection_lock:
                self._active_connections.discard(session)
                self.metrics.active_connections = len(self._active_connections)

    @monitor_performance
    async def execute_query(
        self,
        query: Any,
        session: Optional[AsyncSession] = None,
        cache_key: Optional[str] = None,
        cache_ttl: Optional[int] = None,
    ) -> Any:
        """Execute query with optional caching"""
        # Check cache first
        if cache_key:
            cached_result = await self.cache.get(cache_key)
            if cached_result is not None:
                self.metrics.cache_hits += 1
                return cached_result
            self.metrics.cache_misses += 1

        # Execute query
        if session:
            result = await session.execute(query)
        else:
            async with self.get_session() as session:
                result = await session.execute(query)

        # Cache result if applicable
        if cache_key and query.is_select:
            await self.cache.set(cache_key, result, cache_ttl)

        return result

    async def execute_batch(self, operations: List[Tuple[str, Any, Dict[str, Any]]]) -> None:
        """Execute multiple operations in batch"""
        async with self.get_session() as session:
            try:
                # Group operations by type for optimization
                for op_type, model, data in operations:
                    if op_type == "insert":
                        await session.execute(insert(model).values(**data))
                    elif op_type == "update":
                        await session.execute(
                            update(model).where(model.id == data.get("id")).values(**data)
                        )
                    elif op_type == "delete":
                        await session.execute(delete(model).where(model.id == data.get("id")))

                await session.commit()
                self.metrics.batch_operations += 1
                self.metrics.batch_size += len(operations)

            except Exception:
                await session.rollback()
                raise

    async def health_check(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            async with self.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                await session.commit()

            return {
                "status": "healthy",
                "connection_pool": {
                    "size": self.pool_size,
                    "overflow": self.max_overflow,
                    "active": self.metrics.active_connections,
                },
                "metrics": {
                    "query_count": self.metrics.query_count,
                    "avg_time": self.metrics.avg_query_time,
                    "success_rate": self.metrics.success_rate,
                    "cache_hit_rate": self.metrics.cache_hit_rate,
                },
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    async def close(self) -> None:
        """Close all connections and cleanup"""
        await self.batch_processor.flush()
        await self.engine.dispose()

        # Clear cache
        async with self.cache._lock:
            self.cache._cache.clear()
            self.cache._access_times.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "queries": {
                "count": self.metrics.query_count,
                "total_time": self.metrics.total_time,
                "avg_time": self.metrics.avg_query_time,
                "slow_queries": self.metrics.slow_queries,
                "timeouts": self.metrics.timeout_queries,
                "failed": self.metrics.failed_queries,
                "success_rate": self.metrics.success_rate,
            },
            "connections": {
                "active": self.metrics.active_connections,
                "pool_hits": self.metrics.pool_hits,
                "pool_misses": self.metrics.pool_misses,
            },
            "cache": {
                "size": self.cache.size(),
                "hit_rate": self.metrics.cache_hit_rate,
                "hits": self.metrics.cache_hits,
                "misses": self.metrics.cache_misses,
            },
            "batch": {
                "operations": self.metrics.batch_operations,
                "total_size": self.metrics.batch_size,
                "avg_size": self.metrics.batch_size / max(1, self.metrics.batch_operations),
            },
        }


# Global instance for easy access
_db_manager: Optional[OptimizedDatabaseManager] = None


async def get_db_manager() -> OptimizedDatabaseManager:
    """Get or create global database manager"""
    global _db_manager
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized. Call init_db_manager() first.")
    return _db_manager


def init_db_manager(**kwargs) -> OptimizedDatabaseManager:
    """Initialize global database manager"""
    global _db_manager
    if _db_manager is not None:
        logger.warning("Database manager already initialized")
    _db_manager = OptimizedDatabaseManager(**kwargs)
    return _db_manager
