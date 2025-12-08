"""
Test performance optimization strategies and benchmark utilities.
"""

import asyncio
import time
import gc
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Any, Callable
import pytest
import psutil
import memory_profiler

from fastapi_easy.migrations.engine import MigrationEngine
from fastapi_easy.migrations.detector import SchemaDetector
from fastapi_easy.utils.query_params import QueryParams
from sqlalchemy import create_engine, MetaData


@pytest.fixture
def performance_monitor():
    """Monitor system performance during tests"""

    class PerformanceMonitor:
        def __init__(self):
            self.process = psutil.Process()
            self.start_time = None
            self.start_memory = None
            self.start_cpu = None
            self.peak_memory = 0

        def start(self):
            """Start monitoring"""
            gc.collect()  # Force garbage collection
            self.start_time = time.perf_counter()
            self.start_memory = self.process.memory_info().rss
            self.start_cpu = self.process.cpu_percent()
            self.peak_memory = self.start_memory

        def stop(self) -> Dict[str, Any]:
            """Stop monitoring and return metrics"""
            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss
            end_cpu = self.process.cpu_percent()

            return {
                "duration": end_time - self.start_time,
                "memory_delta": end_memory - self.start_memory,
                "peak_memory": self.peak_memory,
                "memory_mb": end_memory / 1024 / 1024,
                "cpu_usage": end_cpu,
                "gc_collections": gc.collect(),  # Force final GC
            }

        def update_peak(self):
            """Update peak memory usage"""
            current_memory = self.process.memory_info().rss
            self.peak_memory = max(self.peak_memory, current_memory)

    return PerformanceMonitor()


@pytest.fixture
def parallel_test_runner():
    """Run tests in parallel for performance comparison"""

    class ParallelTestRunner:
        def __init__(self):
            self.results = {}

        async def run_async_tasks(self, tasks: List[Callable], max_workers: int = None):
            """Run async tasks in parallel"""
            if max_workers is None:
                max_workers = min(32, (os.cpu_count() or 1) + 4)

            semaphore = asyncio.Semaphore(max_workers)

            async def limited_task(task):
                async with semaphore:
                    start_time = time.perf_counter()
                    result = await task()
                    duration = time.perf_counter() - start_time
                    return {"result": result, "duration": duration}

            return await asyncio.gather(*[limited_task(task) for task in tasks])

        def run_threaded_tasks(self, tasks: List[Callable], max_workers: int = None):
            """Run tasks in thread pool"""
            if max_workers is None:
                max_workers = os.cpu_count() or 1

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self._time_task, task) for task in tasks]
                return [future.result() for future in futures]

        def run_process_tasks(self, tasks: List[Callable], max_workers: int = None):
            """Run tasks in process pool"""
            if max_workers is None:
                max_workers = os.cpu_count() or 1

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self._time_task, task) for task in tasks]
                return [future.result() for future in futures]

        def _time_task(self, task):
            """Time a single task execution"""
            start_time = time.perf_counter()
            result = task()
            duration = time.perf_counter() - start_time
            return {"result": result, "duration": duration}

    return ParallelTestRunner()


@pytest.mark.performance
class TestQueryParamsPerformance:
    """Test query parameter processing performance"""

    @pytest.mark.benchmark
    def test_query_params_parsing_performance(self, performance_monitor):
        """Benchmark query parameter parsing performance"""
        from pydantic import BaseModel

        class ComplexQuery(BaseModel):
            name: str
            age: int
            tags: List[str] = []
            metadata: Dict[str, Any] = {}
            page: int = 1
            limit: int = 10

        dependency = QueryParams(ComplexQuery)

        # Test with complex data
        test_params = {
            "name": "John Doe",
            "age": "30",
            "tags": '["tag1", "tag2", "tag3"]',
            "metadata": '{"key1": "value1", "key2": 123}',
            "page": "2",
            "limit": "50",
        }

        performance_monitor.start()

        # Run many iterations
        for _ in range(10000):
            result = dependency(**test_params)
            assert result.name == "John Doe"

        metrics = performance_monitor.stop()

        # Performance assertions
        assert metrics["duration"] < 1.0  # Should complete within 1 second
        assert metrics["memory_delta"] < 50 * 1024 * 1024  # Less than 50MB memory increase

    def test_query_params_concurrent_parsing(self, parallel_test_runner):
        """Test concurrent query parameter parsing"""
        from pydantic import BaseModel

        class SimpleQuery(BaseModel):
            name: str
            value: int

        dependency = QueryParams(SimpleQuery)
        test_params = {"name": "test", "value": "42"}

        async def parse_params():
            return dependency(**test_params)

        # Run in parallel
        tasks = [parse_params() for _ in range(1000)]
        results = await parallel_test_runner.run_async_tasks(tasks)

        # All should succeed
        assert len(results) == 1000
        assert all(r["result"].name == "test" for r in results)

        # Performance should be reasonable
        total_duration = sum(r["duration"] for r in results)
        avg_duration = total_duration / len(results)
        assert avg_duration < 0.001  # Average < 1ms per operation


@pytest.mark.performance
class TestMigrationEnginePerformance:
    """Test migration engine performance"""

    @pytest.mark.asyncio
    async def test_migration_engine_concurrent_detection(self, parallel_test_runner):
        """Test concurrent schema detection performance"""
        engines = []

        # Create multiple engines
        for i in range(5):
            engine = create_engine(f"sqlite:///:memory:")
            metadata = MetaData()
            migration_engine = MigrationEngine(engine, metadata)
            # Mock lock to avoid conflicts
            migration_engine.lock.acquire = AsyncMock(return_value=True)
            migration_engine.lock.release = AsyncMock(return_value=True)
            engines.append(migration_engine)

        async def detect_changes(engine):
            """Detect schema changes"""
            return await engine.detector.detect_changes()

        # Run detections in parallel
        tasks = [detect_changes(engine) for engine in engines]
        results = await parallel_test_runner.run_async_tasks(tasks, max_workers=3)

        # All should complete successfully
        assert len(results) == 5
        assert all(isinstance(r["result"], list) for r in results)

        # Performance check
        total_duration = sum(r["duration"] for r in results)
        assert total_duration < 5.0  # Should complete within 5 seconds

    @pytest.mark.asyncio
    async def test_migration_engine_memory_efficiency(self, performance_monitor):
        """Test migration engine memory efficiency"""
        engines = []

        performance_monitor.start()

        # Create many engines to test memory usage
        for i in range(100):
            engine = create_engine("sqlite:///:memory:")
            metadata = MetaData()
            migration_engine = MigrationEngine(engine, metadata)
            # Mock to avoid actual operations
            migration_engine.lock.acquire = AsyncMock(return_value=True)
            migration_engine.lock.release = AsyncMock(return_value=True)
            migration_engine.detector.detect_changes = AsyncMock(return_value=[])
            engines.append(migration_engine)

            # Update peak memory
            performance_monitor.update_peak()

        metrics = performance_monitor.stop()

        # Memory should be reasonable
        assert metrics["peak_memory"] < 200 * 1024 * 1024  # Less than 200MB peak
        assert metrics["memory_mb"] < 100  # Less than 100MB final usage

        # Cleanup
        for engine in engines:
            engine.engine.dispose()


@pytest.mark.performance
class TestDatabaseConnectionPooling:
    """Test database connection pooling performance"""

    def test_connection_pool_efficiency(self, performance_monitor):
        """Test database connection pool efficiency"""
        # Create engine with connection pooling
        engine = create_engine(
            "sqlite:///:memory:",
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

        performance_monitor.start()

        # Use many connections
        connections = []
        for i in range(50):
            conn = engine.connect()
            connections.append(conn)
            # Simple operation
            conn.execute("SELECT 1")

        # Close all connections
        for conn in connections:
            conn.close()

        metrics = performance_monitor.stop()

        # Should be efficient with pooling
        assert metrics["duration"] < 1.0
        assert len(engine.pool.status()) > 0

        engine.dispose()

    @pytest.mark.asyncio
    async def test_async_database_operations(self):
        """Test async database operation performance"""
        # This would require async database driver
        # For now, test with threading
        from concurrent.futures import ThreadPoolExecutor

        engine = create_engine("sqlite:///:memory:")

        def database_operation(i):
            """Simple database operation"""
            with engine.connect() as conn:
                result = conn.execute(f"SELECT {i}")
                return result.fetchone()[0]

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(database_operation, i) for i in range(100)]
            results = [f.result() for f in futures]

        assert results == list(range(100))
        engine.dispose()


@pytest.mark.performance
class TestMemoryOptimization:
    """Test memory optimization strategies"""

    def test_memory_usage_with_gc_optimization(self, performance_monitor):
        """Test memory usage with garbage collection optimization"""
        # Disable automatic GC for test
        gc.disable()
        gc.set_threshold(0)  # Disable automatic collection

        performance_monitor.start()

        # Create many objects
        objects = []
        for i in range(10000):
            obj = {"id": i, "data": "x" * 100, "nested": {"value": i}}  # 100 bytes per object
            objects.append(obj)

            # Periodically force GC
            if i % 1000 == 0:
                gc.collect()
                performance_monitor.update_peak()

        # Final cleanup
        del objects
        gc.collect()

        metrics = performance_monitor.stop()

        # Re-enable GC
        gc.enable()
        gc.set_threshold(700, 10, 10)

        # Memory should be reasonable
        assert metrics["peak_memory"] < 50 * 1024 * 1024  # Less than 50MB

    @pytest.mark.asyncio
    async def test_async_memory_cleanup(self, performance_monitor):
        """Test memory cleanup in async operations"""

        async def memory_intensive_task():
            """Task that uses a lot of memory temporarily"""
            # Create large object
            large_data = ["x"] * 1000000  # ~8MB
            await asyncio.sleep(0.01)  # Simulate async work
            # Data should be garbage collected when function exits
            return len(large_data)

        performance_monitor.start()

        # Run many tasks sequentially
        for i in range(10):
            result = await memory_intensive_task()
            assert result == 1000000

            # Periodically trigger GC
            if i % 3 == 0:
                gc.collect()
                performance_monitor.update_peak()

        metrics = performance_monitor.stop()

        # Memory should not accumulate
        assert metrics["memory_delta"] < 10 * 1024 * 1024  # Less than 10MB increase


@pytest.mark.performance
class TestCachePerformance:
    """Test caching performance"""

    def test_lru_cache_performance(self, performance_monitor):
        """Test LRU cache performance"""
        from functools import lru_cache

        @lru_cache(maxsize=128)
        def expensive_function(x):
            """Simulate expensive computation"""
            total = 0
            for i in range(1000):
                total += i * x
            return total

        performance_monitor.start()

        # First run (cache miss)
        for i in range(200):
            result = expensive_function(i)

        # Second run (cache hit for first 128)
        for i in range(200):
            result = expensive_function(i)

        metrics = performance_monitor.stop()

        # Second run should be faster due to caching
        assert metrics["duration"] < 0.5  # Should be very fast
        assert expensive_function.cache_info().hits > 100

    @pytest.mark.asyncio
    async def test_async_cache_performance(self, performance_monitor):
        """Test async cache performance"""
        cache = {}

        async def cached_async_function(key):
            """Async function with caching"""
            if key in cache:
                return cache[key]

            # Simulate expensive async operation
            await asyncio.sleep(0.001)
            result = f"result_for_{key}"
            cache[key] = result
            return result

        performance_monitor.start()

        # Run many operations with some repeats
        keys = [f"key_{i % 50}" for i in range(200)]
        for key in keys:
            result = await cached_async_function(key)

        metrics = performance_monitor.stop()

        # Should be efficient with caching
        assert len(cache) == 50  # Only 50 unique keys
        assert metrics["duration"] < 1.0


@pytest.mark.performance
class TestParallelExecutionOptimization:
    """Test parallel execution optimization"""

    def test_thread_vs_process_performance(self, parallel_test_runner):
        """Compare threading vs multiprocessing performance"""

        def cpu_bound_task(n):
            """CPU-bound task"""
            total = 0
            for i in range(n):
                total += i * i
            return total

        def io_bound_task():
            """IO-bound task simulation"""
            time.sleep(0.001)
            return "done"

        # Test CPU-bound with threads
        start_time = time.perf_counter()
        thread_results = parallel_test_runner.run_threaded_tasks(
            [lambda: cpu_bound_task(10000) for _ in range(10)], max_workers=4
        )
        thread_duration = time.perf_counter() - start_time

        # Test CPU-bound with processes
        start_time = time.perf_counter()
        process_results = parallel_test_runner.run_process_tasks(
            [lambda: cpu_bound_task(10000) for _ in range(10)], max_workers=4
        )
        process_duration = time.perf_counter() - start_time

        # For CPU-bound tasks, processes should be faster
        # (though this can vary by system)
        assert all(r["result"] == process_results[0]["result"] for r in process_results)

        # Test IO-bound with threads
        start_time = time.perf_counter()
        io_thread_results = parallel_test_runner.run_threaded_tasks(
            [io_bound_task for _ in range(20)], max_workers=10
        )
        io_thread_duration = time.perf_counter() - start_time

        # For IO-bound tasks, threads are usually better
        assert len(io_thread_results) == 20
        assert io_thread_duration < 0.1  # Should be very fast

    @pytest.mark.asyncio
    async def test_async_vs_sync_performance(self, performance_monitor):
        """Compare async vs sync performance for IO-bound tasks"""

        async def async_io_task():
            """Async IO task simulation"""
            await asyncio.sleep(0.001)
            return "async_done"

        def sync_io_task():
            """Sync IO task simulation"""
            time.sleep(0.001)
            return "sync_done"

        # Test async version
        performance_monitor.start()
        async_tasks = [async_io_task() for _ in range(100)]
        async_results = await asyncio.gather(*async_tasks)
        async_metrics = performance_monitor.stop()

        # Test sync version
        performance_monitor.start()
        sync_results = [sync_io_task() for _ in range(100)]
        sync_metrics = performance_monitor.stop()

        # Async should be faster for IO-bound tasks
        assert async_metrics["duration"] < sync_metrics["duration"]
        assert len(async_results) == len(sync_results)
