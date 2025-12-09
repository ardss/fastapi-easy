"""
Performance Benchmark Tests for FastAPI-Easy

Comprehensive performance tests including:
- Database operation benchmarks
- API endpoint response times
- Concurrency performance
- Memory usage tests
- Cache efficiency tests
- Scalability tests
"""

import asyncio
import gc
import json
import os
import psutil
import pytest
import pytest_asyncio
import time
import statistics
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, Index, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter
from fastapi_easy.backends.sqlalchemy_optimized import OptimizedSQLAlchemyAdapter
from fastapi_easy.core.optimized_crud_router import OptimizedCRUDRouter
from fastapi_easy.core.optimized_database import (
    OptimizedDatabaseManager,
    QueryCache,
    BatchProcessor,
)
from fastapi_easy.core.async_utils import (
    AsyncBatchProcessor,
    AsyncStream,
    AsyncRateLimiter,
    monitor_async_performance,
)
from pydantic import BaseModel


class Base(DeclarativeBase):
    """SQLAlchemy base class for tests"""

    pass


class PerformanceTestModel(Base):
    """Test model for performance benchmarks"""

    __tablename__ = "performance_test"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(Integer, default=lambda: int(time.time()), index=True)

    # Create composite index for performance testing
    __table_args__ = (
        Index("idx_name_active", "name", "is_active"),
        Index("idx_price_created", "price", "created_at"),
    )


class PerformanceTestSchema(BaseModel):
    """Pydantic schema for test model"""

    id: int
    name: str
    description: Optional[str] = None
    price: float
    is_active: bool = True
    created_at: int

    class Config:
        from_attributes = True


@dataclass
class BenchmarkResult:
    """Benchmark result data"""

    operation: str
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    ops_per_second: float
    success_count: int
    error_count: int
    memory_usage_mb: float
    details: Dict[str, Any]


class PerformanceBenchmark:
    """Performance testing utilities"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    @staticmethod
    def get_memory_usage() -> float:
        """Get current memory usage in MB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024

    @staticmethod
    async def measure_operation(
        operation: callable, iterations: int = 100, concurrency: int = 10, warmup: int = 10
    ) -> BenchmarkResult:
        """
        Measure operation performance with concurrency
        """
        # Warmup
        for _ in range(warmup):
            try:
                if asyncio.iscoroutinefunction(operation):
                    await operation()
                else:
                    operation()
            except Exception:
                pass  # Ignore warmup errors

        # Measure memory before
        initial_memory = PerformanceBenchmark.get_memory_usage()

        # Collect timing data
        times = []
        success_count = 0
        error_count = 0

        async def worker():
            nonlocal success_count, error_count
            for _ in range(iterations // concurrency):
                start_time = time.perf_counter()
                try:
                    if asyncio.iscoroutinefunction(operation):
                        await operation()
                    else:
                        operation()
                    success_count += 1
                except Exception:
                    error_count += 1
                finally:
                    times.append(time.perf_counter() - start_time)

        # Run concurrent workers
        tasks = [worker() for _ in range(concurrency)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Calculate metrics
        total_time = sum(times)
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        ops_per_second = len(times) / total_time

        # Measure memory after
        final_memory = PerformanceBenchmark.get_memory_usage()
        memory_usage = final_memory - initial_memory

        # Get operation name
        op_name = operation.__name__ if hasattr(operation, "__name__") else "unknown"

        return BenchmarkResult(
            operation=op_name,
            total_time=total_time,
            avg_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            ops_per_second=ops_per_second,
            success_count=success_count,
            error_count=error_count,
            memory_usage_mb=memory_usage,
            details={"iterations": iterations, "concurrency": concurrency, "warmup": warmup},
        )

    def add_result(self, result: BenchmarkResult) -> None:
        """Add benchmark result"""
        self.results.append(result)

    def print_summary(self) -> None:
        """Print benchmark summary"""
        print("\n" + "=" * 80)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 80)

        for result in self.results:
            print(f"\nOperation: {result.operation}")
            print(f"  Total Time: {result.total_time:.4f}s")
            print(f"  Average Time: {result.avg_time:.6f}s")
            print(f"  Min Time: {result.min_time:.6f}s")
            print(f"  Max Time: {result.max_time:.6f}s")
            print(f"  Ops/sec: {result.ops_per_second:.2f}")
            print(
                f"  Success Rate: {result.success_count/(result.success_count+result.error_count)*100:.1f}%"
            )
            print(f"  Memory Used: {result.memory_usage_mb:.2f}MB")

    def save_results(self, filename: str) -> None:
        """Save results to JSON file"""
        data = []
        for result in self.results:
            data.append(
                {
                    "operation": result.operation,
                    "total_time": result.total_time,
                    "avg_time": result.avg_time,
                    "min_time": result.min_time,
                    "max_time": result.max_time,
                    "ops_per_second": result.ops_per_second,
                    "success_count": result.success_count,
                    "error_count": result.error_count,
                    "memory_usage_mb": result.memory_usage_mb,
                    "details": result.details,
                }
            )

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)


@pytest.fixture
def benchmark():
    """Create benchmark instance"""
    return PerformanceBenchmark()


@pytest_asyncio.fixture
async def perf_engine():
    """Create performance test database engine"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, pool_pre_ping=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def perf_session_factory(perf_engine):
    """Create async session factory"""
    return async_sessionmaker(perf_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def standard_adapter(perf_session_factory):
    """Create standard SQLAlchemy adapter"""
    return SQLAlchemyAdapter(
        model=PerformanceTestModel, session_factory=perf_session_factory, pk_field="id"
    )


@pytest_asyncio.fixture
async def optimized_adapter(perf_engine):
    """Create optimized SQLAlchemy adapter"""
    from fastapi_easy.core.optimization_config import OptimizationConfig

    config = OptimizationConfig(pool_size=20, max_overflow=30, cache_size=1000, cache_ttl=300)

    return OptimizedSQLAlchemyAdapter(
        model=PerformanceTestModel,
        database_url="sqlite+aiosqlite:///:memory:",
        optimization_config=config,
    )


@pytest_asyncio.fixture
async def sample_data(perf_session_factory):
    """Create sample data for testing"""
    async with perf_session_factory() as session:
        items = [
            PerformanceTestModel(
                name=f"item_{i}",
                description=f"Description for item {i}",
                price=float(i * 10 + 0.99),
                is_active=i % 2 == 0,
            )
            for i in range(1000)
        ]

        session.add_all(items)
        await session.commit()

        # Refresh to get IDs
        for item in items:
            await session.refresh(item)

        yield items


class TestDatabasePerformance:
    """Database operation performance tests"""

    @pytest.mark.asyncio
    async def test_create_performance(
        self, benchmark: PerformanceBenchmark, standard_adapter, optimized_adapter
    ):
        """Test create operation performance"""

        # Test standard adapter
        async def create_standard():
            await standard_adapter.create(
                {
                    "name": f"perf_test_{time.time()}",
                    "description": "Performance test item",
                    "price": 99.99,
                    "is_active": True,
                }
            )

        result_standard = await benchmark.measure_operation(
            create_standard, iterations=100, concurrency=5
        )
        result_standard.operation = "create_standard"
        benchmark.add_result(result_standard)

        # Test optimized adapter
        async def create_optimized():
            await optimized_adapter.create(
                {
                    "name": f"perf_test_{time.time()}",
                    "description": "Performance test item",
                    "price": 99.99,
                    "is_active": True,
                }
            )

        result_optimized = await benchmark.measure_operation(
            create_optimized, iterations=100, concurrency=5
        )
        result_optimized.operation = "create_optimized"
        benchmark.add_result(result_optimized)

        # Optimized should be faster
        improvement = (
            result_standard.avg_time - result_optimized.avg_time
        ) / result_standard.avg_time
        print(f"\nCreate performance improvement: {improvement*100:.1f}%")

    @pytest.mark.asyncio
    async def test_read_performance(
        self, benchmark: PerformanceBenchmark, standard_adapter, optimized_adapter, sample_data
    ):
        """Test read operation performance"""
        # Get a random ID from sample data
        test_id = sample_data[100].id

        # Test standard adapter
        async def read_standard():
            await standard_adapter.get_one(test_id)

        result_standard = await benchmark.measure_operation(
            read_standard, iterations=1000, concurrency=20
        )
        result_standard.operation = "read_standard"
        benchmark.add_result(result_standard)

        # Test optimized adapter
        async def read_optimized():
            await optimized_adapter.get_one(test_id)

        result_optimized = await benchmark.measure_operation(
            read_optimized, iterations=1000, concurrency=20
        )
        result_optimized.operation = "read_optimized"
        benchmark.add_result(result_optimized)

        # Calculate improvement
        improvement = (
            result_standard.avg_time - result_optimized.avg_time
        ) / result_standard.avg_time
        print(f"\nRead performance improvement: {improvement*100:.1f}%")

    @pytest.mark.asyncio
    async def test_query_with_filters_performance(
        self, benchmark: PerformanceBenchmark, standard_adapter, optimized_adapter, sample_data
    ):
        """Test query with filters performance"""

        # Test standard adapter
        async def query_standard():
            await standard_adapter.get_all(
                filters={"is_active": True, "price": {"gt": 100}},
                sorts={"name": "asc"},
                pagination={"skip": 0, "limit": 10},
            )

        result_standard = await benchmark.measure_operation(
            query_standard, iterations=100, concurrency=10
        )
        result_standard.operation = "query_filters_standard"
        benchmark.add_result(result_standard)

        # Test optimized adapter
        async def query_optimized():
            await optimized_adapter.get_all(
                filters={"is_active": True, "price": {"gt": 100}},
                sorts={"name": "asc"},
                pagination={"skip": 0, "limit": 10},
            )

        result_optimized = await benchmark.measure_operation(
            query_optimized, iterations=100, concurrency=10
        )
        result_optimized.operation = "query_filters_optimized"
        benchmark.add_result(result_optimized)

        # Calculate improvement
        improvement = (
            result_standard.avg_time - result_optimized.avg_time
        ) / result_standard.avg_time
        print(f"\nQuery performance improvement: {improvement*100:.1f}%")

    @pytest.mark.asyncio
    async def test_batch_operations_performance(self, benchmark: PerformanceBenchmark):
        """Test batch operation performance"""
        from fastapi_easy.core.optimized_database import OptimizedDatabaseManager

        # Create optimized manager
        manager = OptimizedDatabaseManager(
            database_url="sqlite+aiosqlite:///:memory:", batch_size=100
        )

        # Test batch insert
        batch_data = [
            {
                "name": f"batch_item_{i}",
                "description": f"Batch item {i}",
                "price": float(i * 5),
                "is_active": True,
            }
            for i in range(1000)
        ]

        async def batch_insert():
            async with manager.get_session() as session:
                for data in batch_data[:100]:  # Smaller batch for test
                    item = PerformanceTestModel(**data)
                    session.add(item)
                await session.commit()

        result = await benchmark.measure_operation(batch_insert, iterations=10, concurrency=3)
        result.operation = "batch_insert"
        benchmark.add_result(result)

        await manager.close()


class TestCachePerformance:
    """Cache performance tests"""

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, benchmark: PerformanceBenchmark):
        """Test cache hit rate performance"""
        cache = QueryCache(max_size=1000, default_ttl=60)

        # Pre-populate cache
        for i in range(100):
            await cache.set(f"key_{i}", f"value_{i}")

        # Test cache hits
        async def cache_hit():
            await cache.get("key_50")

        result_hit = await benchmark.measure_operation(cache_hit, iterations=10000, concurrency=50)
        result_hit.operation = "cache_hit"
        benchmark.add_result(result_hit)

        # Test cache misses
        async def cache_miss():
            await cache.get("nonexistent_key")

        result_miss = await benchmark.measure_operation(
            cache_miss, iterations=10000, concurrency=50
        )
        result_miss.operation = "cache_miss"
        benchmark.add_result(result_miss)

        # Verify cache metrics
        metrics = cache.size()
        print(f"\nCache size: {metrics}")

    @pytest.mark.asyncio
    async def test_cache_invalidation_performance(self, benchmark: PerformanceBenchmark):
        """Test cache invalidation performance"""
        cache = QueryCache(max_size=1000, default_ttl=60)

        # Pre-populate cache
        for i in range(500):
            await cache.set(f"user_{i}_data", f"data_for_user_{i}")

        async def invalidate_pattern():
            await cache.invalidate_pattern("user_")

        result = await benchmark.measure_operation(invalidate_pattern, iterations=10, concurrency=1)
        result.operation = "cache_invalidate_pattern"
        benchmark.add_result(result)


class TestAsyncUtilsPerformance:
    """Async utilities performance tests"""

    @pytest.mark.asyncio
    async def test_batch_processor_performance(self, benchmark: PerformanceBenchmark):
        """Test batch processor performance"""

        async def process_batch(batch: List[int]) -> List[int]:
            # Simulate processing
            await asyncio.sleep(0.001)
            return [x * 2 for x in batch]

        processor = AsyncBatchProcessor(
            batch_size=50, max_concurrency=10, process_func=process_batch
        )

        # Generate test data
        items = list(range(1000))

        async def batch_process():
            return await processor.process_items(items)

        result = await benchmark.measure_operation(batch_process, iterations=5, concurrency=1)
        result.operation = "batch_processor"
        benchmark.add_result(result)

    @pytest.mark.asyncio
    async def test_async_stream_performance(self, benchmark: PerformanceBenchmark):
        """Test async stream performance"""

        async def generate_items(count: int):
            for i in range(count):
                yield i
                await asyncio.sleep(0.001)

        async def process_items():
            count = 0
            async for batch in AsyncStream.batch(generate_items(1000), 50):
                count += len(batch)
            return count

        result = await benchmark.measure_operation(process_items, iterations=5, concurrency=2)
        result.operation = "async_stream"
        benchmark.add_result(result)

    @pytest.mark.asyncio
    async def test_rate_limiter_performance(self, benchmark: PerformanceBenchmark):
        """Test rate limiter performance"""
        limiter = AsyncRateLimiter(max_calls=100, time_window=1.0)

        async def limited_operation():
            await limiter.acquire()
            # Simulate some work
            await asyncio.sleep(0.001)

        result = await benchmark.measure_operation(
            limited_operation, iterations=100, concurrency=20
        )
        result.operation = "rate_limited_operation"
        benchmark.add_result(result)


class TestAPIPerformance:
    """API endpoint performance tests"""

    @pytest.fixture
    def optimized_app(self):
        """Create FastAPI app with optimized CRUD router"""
        app = FastAPI()

        # Mock model and adapter
        router = OptimizedCRUDRouter(
            schema=PerformanceTestSchema,
            model=PerformanceTestModel,
            enable_cache=True,
            cache_ttl=300,
            max_page_size=1000,
        )
        app.include_router(router)

        return app

    @pytest.mark.asyncio
    async def test_api_endpoint_performance(self, benchmark: PerformanceBenchmark, optimized_app):
        """Test API endpoint performance"""
        async with AsyncClient(app=optimized_app, base_url="http://test") as client:

            async def api_call():
                response = await client.get("/performancetestschema/")
                return response.status_code == 200

            result = await benchmark.measure_operation(api_call, iterations=100, concurrency=10)
            result.operation = "api_get_all"
            benchmark.add_result(result)

    @pytest.mark.asyncio
    async def test_api_concurrent_requests(self, benchmark: PerformanceBenchmark, optimized_app):
        """Test API concurrent request handling"""
        async with AsyncClient(app=optimized_app, base_url="http://test") as client:

            async def concurrent_requests():
                tasks = []
                for i in range(50):
                    task = client.get(f"/performancetestschema/{i}")
                    tasks.append(task)

                responses = await asyncio.gather(*tasks, return_exceptions=True)
                return sum(
                    1 for r in responses if hasattr(r, "status_code") and r.status_code != 404
                )

            result = await benchmark.measure_operation(
                concurrent_requests, iterations=5, concurrency=1
            )
            result.operation = "api_concurrent_requests"
            benchmark.add_result(result)


class TestMemoryEfficiency:
    """Memory usage efficiency tests"""

    @pytest.mark.asyncio
    async def test_memory_usage_scaling(self, benchmark: PerformanceBenchmark):
        """Test how memory usage scales with data volume"""
        from fastapi_easy.core.optimized_database import OptimizedDatabaseManager

        manager = OptimizedDatabaseManager(database_url="sqlite+aiosqlite:///:memory:")

        # Test different batch sizes
        for batch_size in [100, 500, 1000, 2000]:

            async def memory_test():
                async with manager.get_session() as session:
                    items = [
                        PerformanceTestModel(
                            name=f"item_{i}",
                            description=f"x" * 100,  # 100 bytes description
                            price=float(i),
                            is_active=i % 2 == 0,
                        )
                        for i in range(batch_size)
                    ]

                    session.add_all(items)
                    await session.commit()

            result = await benchmark.measure_operation(memory_test, iterations=1, concurrency=1)
            result.operation = f"memory_test_batch_{batch_size}"
            benchmark.add_result(result)

            # Force garbage collection
            gc.collect()

        await manager.close()

    @pytest.mark.asyncio
    async def test_cache_memory_usage(self, benchmark: PerformanceBenchmark):
        """Test cache memory usage"""
        cache = QueryCache(max_size=10000, default_ttl=3600)

        # Fill cache with large objects
        large_data = "x" * 1000  # 1KB per item

        async def fill_cache():
            for i in range(1000):
                await cache.set(f"large_key_{i}", f"{large_data}_{i}")

        result = await benchmark.measure_operation(fill_cache, iterations=1, concurrency=1)
        result.operation = "fill_large_cache"
        benchmark.add_result(result)

        print(f"\nCache size after filling: {cache.size()} items")


@pytest.mark.performance
class TestScalability:
    """Scalability tests"""

    @pytest.mark.asyncio
    async def test_connection_pool_scaling(self, benchmark: PerformanceBenchmark):
        """Test database connection pool scaling"""
        from fastapi_easy.core.optimized_database import OptimizedDatabaseManager

        # Test different pool sizes
        for pool_size in [10, 50, 100]:
            manager = OptimizedDatabaseManager(
                database_url="sqlite+aiosqlite:///:memory:",
                pool_size=pool_size,
                max_overflow=pool_size,
            )

            async def concurrent_operations():
                async def worker():
                    async with manager.get_session() as session:
                        result = await session.execute(text("SELECT 1"))
                        return result.scalar()

                tasks = [worker() for _ in range(pool_size * 2)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return sum(1 for r in results if r == 1)

            result = await benchmark.measure_operation(
                concurrent_operations, iterations=5, concurrency=1
            )
            result.operation = f"pool_size_{pool_size}"
            benchmark.add_result(result)

            await manager.close()


# Integration test that combines multiple optimizations
@pytest.mark.asyncio
async def test_full_optimization_pipeline(benchmark: PerformanceBenchmark):
    """Test the full optimization pipeline"""
    from fastapi_easy.core.optimized_database import OptimizedDatabaseManager
    from fastapi_easy.core.async_utils import monitor_async_performance

    # Create optimized manager
    manager = OptimizedDatabaseManager(
        database_url="sqlite+aiosqlite:///:memory:", pool_size=50, cache_size=5000
    )

    # Create performance metrics
    metrics = PerformanceMetrics()

    @monitor_async_performance(metrics)
    async def optimized_pipeline():
        # Insert data in batch
        async with manager.get_session() as session:
            items = [
                PerformanceTestModel(
                    name=f"pipeline_item_{i}",
                    description="Pipeline test item",
                    price=float(i),
                    is_active=True,
                )
                for i in range(100)
            ]
            session.add_all(items)
            await session.commit()

        # Query with caching
        async with manager.get_session() as session:
            result = await session.execute(
                select(PerformanceTestModel).where(PerformanceTestModel.is_active == True).limit(10)
            )
            return result.scalars().all()

    result = await benchmark.measure_operation(optimized_pipeline, iterations=20, concurrency=5)
    result.operation = "full_optimization_pipeline"
    benchmark.add_result(result)

    # Print performance metrics
    print(f"\nPipeline metrics: {metrics}")

    await manager.close()


if __name__ == "__main__":
    # Run performance tests with summary
    pytest.main([__file__, "-v", "-s", "--benchmark-only"])
