"""Optimized SQLAlchemy adapter with connection pooling and performance improvements"""

from __future__ import annotations

import asyncio
import logging
import time
import weakref
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from sqlalchemy import and_, func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import QueuePool

from ..core.cache import QueryCache
from ..core.errors import AppError, ConflictError, ErrorCode
from ..core.optimization_config import OptimizationConfig

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for database operations"""

    query_count: int = 0
    total_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    connection_errors: int = 0
    timeouts: int = 0

    @property
    def avg_query_time(self) -> float:
        return self.total_time / max(1, self.query_count)

    @property
    def cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / max(1, total)) * 100


class OptimizedSQLAlchemyAdapter:
    """High-performance SQLAlchemy adapter with optimizations"""

    def __init__(
        self,
        model: Type[DeclarativeBase],
        database_url: str,
        pk_field: str = "id",
        optimization_config: Optional[OptimizationConfig] = None,
    ):
        """Initialize optimized adapter"""
        self.model = model
        self.pk_field = pk_field
        self.optimization_config = optimization_config or OptimizationConfig()

        # Create async engine with optimized pooling
        self.engine = create_async_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=self.optimization_config.pool_size,
            max_overflow=self.optimization_config.max_overflow,
            pool_timeout=self.optimization_config.pool_timeout,
            pool_recycle=self.optimization_config.pool_recycle,
            pool_pre_ping=True,
            echo=False,
            # Connection specific optimizations
            connect_args=(
                {
                    "command_timeout": self.optimization_config.query_timeout,
                    "server_settings": {
                        "application_name": "fastapi-easy-optimized",
                        "jit": "off",  # Disable JIT for better query planning
                    },
                }
                if "postgresql" in database_url
                else {}
            ),
        )

        # Create session factory with optimized settings
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,  # Manual control for better performance
            autocommit=False,
        )

        # Initialize cache
        self.cache = QueryCache(
            max_size=self.optimization_config.cache_size,
            default_ttl=self.optimization_config.cache_ttl,
        )

        # Performance metrics
        self.metrics = PerformanceMetrics()

        # Query builder cache
        self._query_cache: Dict[str, Any] = {}
        self._prepared_statements: Dict[str, Any] = {}

        # Register cleanup
        weakref.finalize(self, self._cleanup_resources)

    @asynccontextmanager
    async def get_session(self, timeout: Optional[float] = None):
        """Get database session with timeout and error handling"""
        timeout = timeout or self.optimization_config.query_timeout
        session = None

        try:
            session = await asyncio.wait_for(self.session_factory(), timeout=timeout)
            yield session
        except asyncio.TimeoutError:
            self.metrics.timeouts += 1
            logger.error(f"Session acquisition timeout after {timeout}s")
            raise AppError(
                code=ErrorCode.TIMEOUT, status_code=504, message="Database connection timeout"
            )
        except Exception as e:
            self.metrics.connection_errors += 1
            logger.error(f"Session creation error: {e}")
            raise AppError(
                code=ErrorCode.CONNECTION_ERROR,
                status_code=503,
                message="Database connection error",
            )
        finally:
            if session:
                await session.close()

    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation"""
        import hashlib
        import json

        key_data = {"operation": operation, "model": self.model.__name__, **kwargs}
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _build_filter_query(self, filters: Dict[str, Any]) -> Any:
        """Build optimized filter query with caching"""
        if not filters:
            return select(self.model)

        # Check cache
        cache_key = self._get_cache_key("filter", filters=filters)
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        query = select(self.model)

        # Build filters
        filter_conditions = []
        for filter_key, filter_value in filters.items():
            if not isinstance(filter_value, dict):
                continue

            field_name = filter_value.get("field")
            if not field_name:
                continue

            # Security validation
            if not field_name.isidentifier():
                continue

            field = getattr(self.model, field_name, None)
            if field is None:
                continue

            operator = filter_value.get("operator", "exact")
            value = filter_value.get("value")

            # Build condition
            if operator == "exact":
                filter_conditions.append(field == value)
            elif operator == "ne":
                filter_conditions.append(field != value)
            elif operator == "gt":
                filter_conditions.append(field > value)
            elif operator == "gte":
                filter_conditions.append(field >= value)
            elif operator == "lt":
                filter_conditions.append(field < value)
            elif operator == "lte":
                filter_conditions.append(field <= value)
            elif operator == "in":
                if isinstance(value, str):
                    values = value.split(",")
                else:
                    values = value
                filter_conditions.append(field.in_(values))
            elif operator == "like":
                filter_conditions.append(field.like(f"%{value}%"))
            elif operator == "ilike":
                filter_conditions.append(field.ilike(f"%{value}%"))

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        # Cache the query
        self._query_cache[cache_key] = query

        return query

    async def get_all(
        self,
        filters: Dict[str, Any],
        sorts: Dict[str, Any],
        pagination: Dict[str, Any],
        use_cache: bool = True,
    ) -> List[Any]:
        """Get all items with caching and optimizations"""
        start_time = time.time()

        # Check cache first
        if use_cache and self.optimization_config.enable_cache:
            cache_key = self._get_cache_key(
                "get_all",
                filters=filters,
                sorts=sorts,
                pagination=pagination,
            )
            cached = await self.cache.get(cache_key)
            if cached is not None:
                self.metrics.cache_hits += 1
                return cached
            self.metrics.cache_misses += 1

        try:
            async with self.get_session() as session:
                # Build query with optimizations
                query = self._build_filter_query(filters)

                # Apply sorting
                for field_name, direction in sorts.items():
                    if not field_name.isidentifier():
                        continue
                    field = getattr(self.model, field_name, None)
                    if field is not None:
                        if direction == "desc":
                            query = query.order_by(field.desc())
                        else:
                            query = query.order_by(field.asc())

                # Apply pagination
                skip = pagination.get("skip", 0)
                limit = pagination.get("limit", 10)
                query = query.offset(skip).limit(limit)

                # Execute with timeout
                result = await asyncio.wait_for(
                    session.execute(query), timeout=self.optimization_config.query_timeout
                )

                items = result.scalars().all()

                # Cache result
                if use_cache and self.optimization_config.enable_cache:
                    await self.cache.set(cache_key, items)

                # Update metrics
                self.metrics.query_count += 1
                self.metrics.total_time += time.time() - start_time

                return items

        except asyncio.TimeoutError:
            raise AppError(code=ErrorCode.TIMEOUT, status_code=504, message="Query timeout")
        except SQLAlchemyError as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {e!s}"
            )

    async def get_one(self, id: Any, use_cache: bool = True) -> Optional[Any]:
        """Get single item with caching"""
        start_time = time.time()

        # Check cache first
        if use_cache and self.optimization_config.enable_cache:
            cache_key = self._get_cache_key("get_one", id=id)
            cached = await self.cache.get(cache_key)
            if cached is not None:
                self.metrics.cache_hits += 1
                return cached
            self.metrics.cache_misses += 1

        try:
            async with self.get_session() as session:
                pk_field = getattr(self.model, self.pk_field)
                query = select(self.model).where(pk_field == id)

                result = await asyncio.wait_for(
                    session.execute(query), timeout=self.optimization_config.query_timeout
                )
                item = result.scalar_one_or_none()

                # Cache result (including None)
                if use_cache and self.optimization_config.enable_cache:
                    await self.cache.set(cache_key, item)

                # Update metrics
                self.metrics.query_count += 1
                self.metrics.total_time += time.time() - start_time

                return item

        except asyncio.TimeoutError:
            raise AppError(code=ErrorCode.TIMEOUT, status_code=504, message="Query timeout")
        except SQLAlchemyError as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {e!s}"
            )

    async def create(self, data: Dict[str, Any]) -> Any:
        """Create item with optimized transaction handling"""
        start_time = time.time()

        try:
            async with self.get_session() as session:
                # Create item with validation
                item = self.model(**data)
                session.add(item)

                # Commit with timeout
                await asyncio.wait_for(
                    session.commit(), timeout=self.optimization_config.query_timeout
                )

                # Refresh to get generated fields
                await asyncio.wait_for(
                    session.refresh(item), timeout=self.optimization_config.query_timeout
                )

                # Invalidate caches
                if self.optimization_config.enable_cache:
                    await self._invalidate_caches("create")

                # Update metrics
                self.metrics.query_count += 1
                self.metrics.total_time += time.time() - start_time

                return item

        except IntegrityError as e:
            await session.rollback()
            raise ConflictError(f"Item already exists: {e!s}")
        except asyncio.TimeoutError:
            await session.rollback()
            raise AppError(code=ErrorCode.TIMEOUT, status_code=504, message="Create timeout")
        except SQLAlchemyError as e:
            await session.rollback()
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {e!s}"
            )

    async def create_batch(self, items: List[Dict[str, Any]]) -> List[Any]:
        """Batch create for better performance"""
        start_time = time.time()

        if not items:
            return []

        try:
            async with self.get_session() as session:
                # Create all items
                objects = [self.model(**data) for data in items]
                session.add_all(objects)

                # Commit with timeout
                await asyncio.wait_for(
                    session.commit(), timeout=self.optimization_config.query_timeout * len(items)
                )

                # Refresh all
                for obj in objects:
                    await asyncio.wait_for(
                        session.refresh(obj), timeout=self.optimization_config.query_timeout
                    )

                # Invalidate caches
                if self.optimization_config.enable_cache:
                    await self._invalidate_caches("create_batch")

                # Update metrics
                self.metrics.query_count += 1
                self.metrics.total_time += time.time() - start_time

                return objects

        except IntegrityError as e:
            await session.rollback()
            raise ConflictError(f"Batch create conflict: {e!s}")
        except SQLAlchemyError as e:
            await session.rollback()
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {e!s}"
            )

    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[Any]:
        """Update item with optimistic locking"""
        start_time = time.time()

        try:
            async with self.get_session() as session:
                pk_field = getattr(self.model, self.pk_field)
                query = select(self.model).where(pk_field == id)

                result = await asyncio.wait_for(
                    session.execute(query), timeout=self.optimization_config.query_timeout
                )
                item = result.scalar_one_or_none()

                if item is None:
                    return None

                # Update fields
                for key, value in data.items():
                    setattr(item, key, value)

                # Commit with timeout
                await asyncio.wait_for(
                    session.commit(), timeout=self.optimization_config.query_timeout
                )

                # Refresh
                await asyncio.wait_for(
                    session.refresh(item), timeout=self.optimization_config.query_timeout
                )

                # Invalidate caches
                if self.optimization_config.enable_cache:
                    await self.cache.delete(self._get_cache_key("get_one", id=id))
                    await self._invalidate_caches("update")

                # Update metrics
                self.metrics.query_count += 1
                self.metrics.total_time += time.time() - start_time

                return item

        except SQLAlchemyError as e:
            await session.rollback()
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {e!s}"
            )

    async def delete_one(self, id: Any) -> bool:
        """Delete item"""
        start_time = time.time()

        try:
            async with self.get_session() as session:
                pk_field = getattr(self.model, self.pk_field)
                query = select(self.model).where(pk_field == id)

                result = await asyncio.wait_for(
                    session.execute(query), timeout=self.optimization_config.query_timeout
                )
                item = result.scalar_one_or_none()

                if item is None:
                    return False

                # Delete with timeout
                await asyncio.wait_for(
                    session.delete(item), timeout=self.optimization_config.query_timeout
                )
                await asyncio.wait_for(
                    session.commit(), timeout=self.optimization_config.query_timeout
                )

                # Invalidate caches
                if self.optimization_config.enable_cache:
                    await self.cache.delete(self._get_cache_key("get_one", id=id))
                    await self._invalidate_caches("delete")

                # Update metrics
                self.metrics.query_count += 1
                self.metrics.total_time += time.time() - start_time

                return True

        except SQLAlchemyError as e:
            await session.rollback()
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {e!s}"
            )

    async def count(self, filters: Dict[str, Any] = None) -> int:
        """Count items with caching"""
        start_time = time.time()
        filters = filters or {}

        # Check cache first
        if self.optimization_config.enable_cache:
            cache_key = self._get_cache_key("count", filters=filters)
            cached = await self.cache.get(cache_key)
            if cached is not None:
                self.metrics.cache_hits += 1
                return cached
            self.metrics.cache_misses += 1

        try:
            async with self.get_session() as session:
                # Build count query
                query = select(func.count(self.model))
                query = self._build_filter_query(filters).with_only_columns(func.count())

                result = await asyncio.wait_for(
                    session.execute(query), timeout=self.optimization_config.query_timeout
                )
                count = result.scalar()

                # Cache result
                if self.optimization_config.enable_cache:
                    await self.cache.set(cache_key, count)

                # Update metrics
                self.metrics.query_count += 1
                self.metrics.total_time += time.time() - start_time

                return count

        except SQLAlchemyError as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {e!s}"
            )

    async def _invalidate_caches(self, operation: str):
        """Invalidate relevant caches"""
        try:
            # For now, clear all caches
            # TODO: Implement fine-grained invalidation
            await self.cache.clear()
        except Exception as e:
            logger.warning(f"Cache invalidation error: {e}")

    def _cleanup_resources(self):
        """Cleanup resources"""
        # Close engine
        if hasattr(self.engine, "sync_engine"):
            self.engine.sync_engine.dispose()
        else:
            asyncio.create_task(self.engine.dispose())

    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            "queries": self.metrics.query_count,
            "avg_time": self.metrics.avg_query_time,
            "total_time": self.metrics.total_time,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "connection_errors": self.metrics.connection_errors,
            "timeouts": self.metrics.timeouts,
            "cache_stats": self.cache.get_stats() if self.cache else None,
            "pool_size": self.engine.pool.size() if hasattr(self.engine.pool, "size") else None,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on database connection"""
        try:
            async with self.get_session(timeout=5.0) as session:
                result = await session.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    return {"status": "healthy", "timestamp": time.time()}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e), "timestamp": time.time()}

    async def close(self):
        """Close database connections"""
        await self.engine.dispose()


# Factory function for easy instantiation
def create_optimized_adapter(
    model: Type[DeclarativeBase],
    database_url: str,
    pk_field: str = "id",
    optimization_config: Optional[OptimizationConfig] = None,
) -> OptimizedSQLAlchemyAdapter:
    """Create optimized SQLAlchemy adapter"""
    return OptimizedSQLAlchemyAdapter(
        model=model,
        database_url=database_url,
        pk_field=pk_field,
        optimization_config=optimization_config,
    )
