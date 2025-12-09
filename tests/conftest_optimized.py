"""
Optimized pytest configuration with high-performance fixtures,
connection pooling, and comprehensive monitoring.
"""

import os
import sys
import asyncio
import tempfile
import shutil
import time
import threading
import warnings
from pathlib import Path
from contextlib import asynccontextmanager
from unittest.mock import Mock, AsyncMock, patch
from typing import AsyncGenerator, Generator, Dict, Any, Optional
import pytest
import psutil
import json

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Database imports
from sqlalchemy import create_engine, MetaData, event
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session

# FastAPI imports
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Project imports
from fastapi_easy.core.config import CRUDConfig
from fastapi_easy.core.adapters import ORMAdapter
from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter


# ============================================================================
# PERFORMANCE MONITORING FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def performance_tracker():
    """Track performance metrics across the test session"""

    class PerformanceTracker:
        def __init__(self):
            self.metrics = {
                "test_durations": [],
                "memory_usage": [],
                "cpu_usage": [],
                "test_counts": {},
                "slow_tests": [],
            }
            self.start_times = {}
            self.process = psutil.Process()
            self.baseline_memory = self.process.memory_info().rss

        def start_test(self, test_name: str):
            """Start timing a test"""
            self.start_times[test_name] = {
                "start": time.perf_counter(),
                "memory": self.process.memory_info().rss,
                "cpu": self.process.cpu_percent()
            }

        def end_test(self, test_name: str):
            """End timing a test and record metrics"""
            if test_name in self.start_times:
                start_data = self.start_times.pop(test_name)
                duration = time.perf_counter() - start_data["start"]
                current_memory = self.process.memory_info().rss
                memory_delta = current_memory - start_data["memory"]

                self.metrics["test_durations"].append({
                    "test": test_name,
                    "duration": duration,
                    "memory_delta": memory_delta
                })

                if duration > 1.0:  # Track slow tests (>1 second)
                    self.metrics["slow_tests"].append({
                        "test": test_name,
                        "duration": duration
                    })

        def get_summary(self) -> Dict[str, Any]:
            """Get performance summary"""
            if not self.metrics["test_durations"]:
                return {}

            durations = [m["duration"] for m in self.metrics["test_durations"]]
            return {
                "total_tests": len(durations),
                "avg_duration": sum(durations) / len(durations),
                "max_duration": max(durations),
                "min_duration": min(durations),
                "slow_tests_count": len(self.metrics["slow_tests"]),
                "memory_baseline_mb": self.baseline_memory / 1024 / 1024,
            }

    return PerformanceTracker()


@pytest.fixture(autouse=True)
def track_test_performance(request, performance_tracker):
    """Automatically track test performance"""
    test_name = f"{request.cls.__name__ if request.cls else 'Module'}.{request.node.name}"
    performance_tracker.start_test(test_name)

    yield

    performance_tracker.end_test(test_name)


# ============================================================================
# HIGH-PERFORMANCE DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def db_engine_config():
    """Database engine configuration for optimal performance"""
    return {
        "poolclass": StaticPool,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "echo": False,
        "future": True,
        "connect_args": {
            "check_same_thread": False,
            "timeout": 20,
            "isolation_level": "AUTOCOMMIT"
        }
    }


@pytest.fixture(scope="session")
def async_db_engine_config():
    """Async database engine configuration"""
    return {
        "poolclass": StaticPool,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "echo": False,
        "future": True,
        "connect_args": {
            "check_same_thread": False,
            "timeout": 20
        }
    }


@pytest.fixture(scope="session")
def optimized_memory_db():
    """Create optimized in-memory database with connection pooling"""
    engine = create_engine(
        "sqlite:///:memory:",
        **db_engine_config()
    )

    # Performance optimizations
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        # Enable performance optimizations
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA cache_size = 10000")
        cursor.execute("PRAGMA temp_store = MEMORY")
        cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB
        cursor.close()

    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def optimized_async_db():
    """Create optimized async in-memory database"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        **async_db_engine_config()
    )

    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
def optimized_db_session(optimized_memory_db):
    """Create optimized database session with transaction handling"""
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=optimized_memory_db
    )

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture(scope="function")
async def optimized_async_session(optimized_async_db):
    """Create optimized async database session"""
    async_session = async_sessionmaker(
        optimized_async_db,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ============================================================================
# CONNECTION POOLING FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def connection_pool():
    """Database connection pool for performance testing"""
    pool = QueuePool(
        creator=lambda: create_engine("sqlite:///:memory:"),
        pool_size=5,
        max_overflow=10,
        timeout=30,
        recycle=3600
    )

    yield pool
    pool.dispose()


@pytest.fixture
async def pooled_connections(connection_pool):
    """Get pooled connections for concurrent operations"""
    connections = []

    try:
        # Get multiple connections from pool
        for _ in range(3):
            conn = connection_pool.connect()
            connections.append(conn)

        yield connections

    finally:
        # Return connections to pool
        for conn in connections:
            try:
                conn.close()
            except:
                pass


# ============================================================================
# CACHED FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
@pytest.mark.cache
def cached_test_data():
    """Cache frequently used test data"""

    # Generate test data once per session
    data = {
        "users": [
            {"id": i, "name": f"User_{i}", "email": f"user{i}@example.com"}
            for i in range(1, 101)
        ],
        "items": [
            {"id": i, "name": f"Item_{i}", "price": float(i * 10)}
            for i in range(1, 501)
        ],
        "categories": [
            {"id": i, "name": f"Category_{i}"}
            for i in range(1, 21)
        ]
    }

    return data


@pytest.fixture(scope="session")
def cached_schemas():
    """Cache Pydantic schemas for testing"""

    from pydantic import BaseModel, ConfigDict

    class UserSchema(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: int
        name: str
        email: str

    class ItemSchema(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: int
        name: str
        price: float

    class CategorySchema(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: int
        name: str

    return {
        "user": UserSchema,
        "item": ItemSchema,
        "category": CategorySchema
    }


# ============================================================================
# OPTIMIZED MOCK FIXTURES
# ============================================================================

@pytest.fixture
def optimized_mock_adapter():
    """High-performance mock adapter with caching"""

    class CachedMockAdapter:
        def __init__(self):
            self._cache = {}
            self.call_count = 0

        async def get_all(self, **kwargs):
            cache_key = f"get_all_{hash(str(sorted(kwargs.items())))}"
            if cache_key in self._cache:
                return self._cache[cache_key]

            self.call_count += 1
            result = []
            self._cache[cache_key] = result
            return result

        async def get_one(self, id: int):
            cache_key = f"get_one_{id}"
            if cache_key in self._cache:
                return self._cache[cache_key]

            self.call_count += 1
            result = {"id": id, "name": f"Item_{id}"}
            self._cache[cache_key] = result
            return result

        async def create(self, data: dict):
            self.call_count += 1
            result = {"id": self.call_count, **data}
            return result

        async def update(self, id: int, data: dict):
            self.call_count += 1
            result = {"id": id, **data}
            return result

        async def delete(self, id: int):
            self.call_count += 1
            return {"id": id}

        async def count(self, **kwargs):
            cache_key = f"count_{hash(str(sorted(kwargs.items())))}"
            if cache_key in self._cache:
                return self._cache[cache_key]

            self.call_count += 1
            result = 0
            self._cache[cache_key] = result
            return result

    return CachedMockAdapter()


# ============================================================================
# PERFORMANCE BENCHMARKING FIXTURES
# ============================================================================

@pytest.fixture
def benchmark_context():
    """Context manager for benchmarking code performance"""

    @asynccontextmanager
    async def async_benchmark():
        start_time = time.perf_counter()
        start_memory = psutil.Process().memory_info().rss

        try:
            yield
        finally:
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss

            metrics = {
                "duration": end_time - start_time,
                "memory_delta": end_memory - start_memory,
                "memory_mb": (end_memory - start_memory) / 1024 / 1024
            }

            # Log performance metrics
            print(f"\n[PERFORMANCE] Duration: {metrics['duration']:.4f}s, "
                  f"Memory: {metrics['memory_mb']:.2f}MB")

    return async_benchmark


@pytest.fixture
def memory_profiler():
    """Profile memory usage during tests"""

    class MemoryProfiler:
        def __init__(self):
            self.snapshots = []

        def snapshot(self, label: str = ""):
            """Take a memory snapshot"""
            memory_info = psutil.Process().memory_info()
            self.snapshots.append({
                "label": label,
                "rss": memory_info.rss,
                "vms": memory_info.vms,
                "timestamp": time.time()
            })

        def get_report(self) -> Dict[str, Any]:
            """Get memory usage report"""
            if not self.snapshots:
                return {}

            rss_values = [s["rss"] for s in self.snapshots]
            return {
                "snapshots": len(self.snapshots),
                "peak_rss_mb": max(rss_values) / 1024 / 1024,
                "avg_rss_mb": sum(rss_values) / len(rss_values) / 1024 / 1024,
                "rss_growth_mb": (rss_values[-1] - rss_values[0]) / 1024 / 1024
            }

    return MemoryProfiler()


# ============================================================================
# PARALLEL TESTING FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def parallel_test_config():
    """Configuration for parallel test execution"""

    # Get number of available CPUs
    cpu_count = os.cpu_count() or 4

    return {
        "max_workers": min(cpu_count, 8),  # Cap at 8 workers
        "chunk_size": 100,  # Process tests in chunks
        "timeout_per_test": 30,  # Timeout per individual test
        "worker_memory_limit_mb": 1024,  # Memory limit per worker
    }


@pytest.fixture
def worker_id(request):
    """Get worker ID for parallel test coordination"""
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput.get("workerid", "main")
    return "main"


# ============================================================================
# REGRESSION TESTING FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def performance_baseline():
    """Load or create performance baseline for regression testing"""

    baseline_file = Path(__file__).parent / ".performance_baseline.json"

    if baseline_file.exists():
        with open(baseline_file) as f:
            return json.load(f)

    # Create default baseline
    baseline = {
        "max_test_duration": 5.0,  # seconds
        "max_memory_growth_mb": 100,
        "max_cpu_usage_percent": 80,
        "max_slow_tests": 10,
    }

    # Save baseline
    with open(baseline_file, "w") as f:
        json.dump(baseline, f, indent=2)

    return baseline


@pytest.fixture(autouse=True)
def check_performance_regression(request, performance_tracker, performance_baseline):
    """Check for performance regressions after each test"""

    yield

    # Check after test completion
    if request.node.callspec:
        test_name = request.node.name

        # Get latest test metrics
        if performance_tracker.metrics["test_durations"]:
            latest_test = performance_tracker.metrics["test_durations"][-1]

            if latest_test["duration"] > performance_baseline["max_test_duration"]:
                pytest.warns(
                    UserWarning,
                    f"Test {test_name} exceeded duration baseline: "
                    f"{latest_test['duration']:.2f}s > {performance_baseline['max_test_duration']}s"
                )


# ============================================================================
# CONFIGURATION AND CLEANUP
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure the test environment for optimal performance"""

    # Set environment variables for testing
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["LOG_LEVEL"] = "WARNING"

    # Configure asyncio for better performance
    if hasattr(asyncio, "set_event_loop_policy"):
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())

    # Suppress warnings for cleaner output
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    yield

    # Cleanup
    os.environ.pop("TESTING", None)
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("LOG_LEVEL", None)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_resources():
    """Clean up test resources after session"""

    yield

    # Force garbage collection
    import gc
    gc.collect()

    # Clean up any temporary files
    temp_dir = Path(tempfile.gettempdir())
    for pattern in ["test_*.db", "*.tmp", "pytest_*"]:
        for file_path in temp_dir.glob(pattern):
            try:
                file_path.unlink()
            except:
                pass


# ============================================================================
# CUSTOM PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings"""

    # Add custom markers
    config.addinivalue_line("markers", "performance: Performance test")
    config.addinivalue_line("markers", "slow: Slow running test")
    config.addinivalue_line("markers", "cache: Test uses cached data")
    config.addinivalue_line("markers", "benchmark: Benchmark test")
    config.addinivalue_line("markers", "memory: Memory test")
    config.addinivalue_line("markers", "regression: Regression test")


def pytest_sessionfinish(session, exitstatus):
    """Generate performance report after test session"""

    # Try to get performance tracker from session
    if hasattr(session, "_performance_tracker"):
        tracker = session._performance_tracker
        summary = tracker.get_summary()

        if summary:
            print("\n" + "="*50)
            print("PERFORMANCE SUMMARY")
            print("="*50)
            print(f"Total tests: {summary['total_tests']}")
            print(f"Average duration: {summary['avg_duration']:.3f}s")
            print(f"Max duration: {summary['max_duration']:.3f}s")
            print(f"Min duration: {summary['min_duration']:.3f}s")
            print(f"Slow tests: {summary['slow_tests_count']}")
            print(f"Memory baseline: {summary['memory_baseline_mb']:.1f}MB")

            if summary["slow_tests"]:
                print("\nSLOW TESTS:")
                for test in summary["slow_tests"][:5]:  # Top 5 slowest
                    print(f"  {test['test']}: {test['duration']:.3f}s")
            print("="*50)


# Export for use in other modules
__all__ = [
    "performance_tracker",
    "optimized_memory_db",
    "optimized_async_db",
    "optimized_db_session",
    "optimized_async_session",
    "connection_pool",
    "pooled_connections",
    "cached_test_data",
    "cached_schemas",
    "optimized_mock_adapter",
    "benchmark_context",
    "memory_profiler",
    "parallel_test_config",
    "performance_baseline",
]