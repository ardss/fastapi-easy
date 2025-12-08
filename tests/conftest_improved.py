"""
Improved pytest configuration with better cleanup and fixtures.
"""

import os
import sys
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
from typing import AsyncGenerator, Generator
import pytest
import warnings

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import create_engine, MetaData
from fastapi_easy.migrations.distributed_lock import get_lock_provider


@pytest.fixture(scope="session", autouse=True)
def cleanup_lock_files():
    """Clean up any existing lock files before and after test session"""
    lock_files = [
        ".fastapi_easy_migration.lock",
        ".fastapi_easy_test.lock",
        ".fastapi_easy_performance.lock",
    ]

    # Clean up before tests
    for lock_file in lock_files:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except (OSError, IOError):
                pass

    yield

    # Clean up after tests
    for lock_file in lock_files:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except (OSError, IOError):
                pass


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests"""
    temp_path = Path(tempfile.mkdtemp())
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def in_memory_engine():
    """Create an in-memory SQLite engine for testing"""
    return create_engine("sqlite:///:memory:", echo=False)


@pytest.fixture
def mock_engine():
    """Create a mock database engine for testing"""
    engine = Mock()
    engine.dialect.name = "sqlite"
    engine.url = Mock()
    engine.url.database = ":memory:"
    return engine


@pytest.fixture
def migration_engine(in_memory_engine):
    """Create a migration engine for testing with proper cleanup"""
    from fastapi_easy.migrations.engine import MigrationEngine

    metadata = MetaData()
    engine = MigrationEngine(in_memory_engine, metadata)

    # Force cleanup of any existing locks
    if hasattr(engine.lock, "force_release"):
        engine.lock.force_release()

    yield engine

    # Cleanup after test
    if hasattr(engine.lock, "force_release"):
        engine.lock.force_release()


@pytest.fixture
def isolated_lock_engine():
    """Create a migration engine with isolated lock for parallel testing"""
    from fastapi_easy.migrations.engine import MigrationEngine

    # Use a unique temporary database for each test
    engine = create_engine("sqlite:///:memory:", echo=False)
    metadata = MetaData()
    migration_engine = MigrationEngine(engine, metadata)

    # Mock the lock to avoid file system conflicts
    with patch.object(migration_engine, "lock") as mock_lock:
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock(return_value=True)
        yield migration_engine


@pytest.fixture
async def async_migration_engine():
    """Async version of migration engine fixture"""
    from fastapi_easy.migrations.engine import MigrationEngine

    engine = create_engine("sqlite:///:memory:", echo=False)
    metadata = MetaData()
    migration_engine = MigrationEngine(engine, metadata)

    # Mock lock to avoid concurrency issues
    with patch.object(migration_engine, "lock") as mock_lock:
        mock_lock.acquire = AsyncMock(return_value=True)
        mock_lock.release = AsyncMock(return_value=True)
        yield migration_engine


# Improved async testing utilities
@pytest.fixture
def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Test markers for better organization
pytest_plugins = []


# Custom markers
def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "performance: mark test as a performance test")
    config.addinivalue_line("markers", "migration: mark test as a migration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "async_test: mark test as async")


# Performance testing utilities
@pytest.fixture
def performance_monitor():
    """Monitor test performance"""
    import time
    import psutil
    import os

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.process = psutil.Process(os.getpid())

        def start(self):
            self.start_time = time.perf_counter()
            self.start_memory = self.process.memory_info().rss

        def stop(self):
            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss
            return {
                "duration": end_time - self.start_time,
                "memory_delta": end_memory - self.start_memory,
                "peak_memory": end_memory,
            }

    return PerformanceMonitor()


# Mock utilities
@pytest.fixture
def mock_logger():
    """Create a mock logger for testing"""
    with patch("fastapi_easy.migrations.engine.logger") as mock:
        yield mock


@pytest.fixture
def mock_detector():
    """Create a mock schema detector"""
    with patch("fastapi_easy.migrations.detector.SchemaDetector") as mock:
        yield mock


@pytest.fixture
def mock_executor():
    """Create a mock migration executor"""
    with patch("fastapi_easy.migrations.executor.MigrationExecutor") as mock:
        yield mock


@pytest.fixture
def mock_storage():
    """Create a mock migration storage"""
    with patch("fastapi_easy.migrations.storage.MigrationStorage") as mock:
        yield mock


# AsyncMock import for older Python versions
try:
    from unittest.mock import AsyncMock
except ImportError:
    # Fallback for Python < 3.8
    class AsyncMock:
        def __init__(self, return_value=None, side_effect=None):
            self.return_value = return_value
            self.side_effect = side_effect
            self.call_count = 0
            self.call_args = None
            self.call_args_list = []

        async def __call__(self, *args, **kwargs):
            self.call_count += 1
            self.call_args = (args, kwargs)
            self.call_args_list.append((args, kwargs))

            if self.side_effect:
                if callable(self.side_effect):
                    return await self.side_effect(*args, **kwargs)
                else:
                    raise self.side_effect

            if asyncio.iscoroutine(self.return_value):
                return await self.return_value
            return self.return_value

        def assert_called_once(self):
            if self.call_count != 1:
                raise AssertionError(f"Expected to be called once, called {self.call_count} times")

        def assert_called(self):
            if self.call_count == 0:
                raise AssertionError("Expected to be called, but was not")

        def assert_not_called(self):
            if self.call_count != 0:
                raise AssertionError(
                    f"Expected to not be called, but was called {self.call_count} times"
                )


# Suppress warnings for cleaner test output
@pytest.fixture(autouse=True)
def suppress_warnings():
    """Suppress certain warnings during testing"""
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
    warnings.filterwarnings("ignore", message=".*pytest.*")
    yield


# Test data factories
@pytest.fixture
def sample_migration():
    """Create a sample migration for testing"""
    from fastapi_easy.migrations.types import Migration, RiskLevel

    return Migration(
        version="20240101_001",
        description="Test migration",
        upgrade_sql="CREATE TABLE test (id INTEGER);",
        downgrade_sql="DROP TABLE test;",
        risk_level=RiskLevel.SAFE,
    )


@pytest.fixture
def sample_migrations():
    """Create multiple sample migrations for testing"""
    from fastapi_easy.migrations.types import Migration, RiskLevel

    return [
        Migration(
            version="20240101_001",
            description="First migration",
            upgrade_sql="CREATE TABLE test1 (id INTEGER);",
            downgrade_sql="DROP TABLE test1;",
            risk_level=RiskLevel.SAFE,
        ),
        Migration(
            version="20240101_002",
            description="Second migration",
            upgrade_sql="CREATE TABLE test2 (id INTEGER);",
            downgrade_sql="DROP TABLE test2;",
            risk_level=RiskLevel.UNSAFE,
        ),
    ]


# Database setup utilities
@pytest.fixture
def test_database():
    """Create a test database with proper cleanup"""
    db_path = tempfile.mktemp(suffix=".db")
    engine = create_engine(f"sqlite:///{db_path}", echo=False)

    yield engine

    # Cleanup
    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


# Parallel test support
@pytest.fixture
def worker_id(request):
    """Get worker ID for parallel testing"""
    if hasattr(request.config, "workerinput"):
        return request.config.workerinput.get("workerid", "main")
    return "main"


# Improved error handling
@pytest.fixture(autouse=True)
def handle_test_errors():
    """Handle test errors gracefully"""
    yield

    # Force cleanup of any hanging resources
    # This is especially important for async tests and database connections


# Coverage utilities
@pytest.fixture
def coverage_monitor():
    """Monitor test coverage"""

    # This would integrate with coverage.py if needed
    class CoverageMonitor:
        def __init__(self):
            self.covered_lines = set()
            self.missing_lines = set()

        def record_coverage(self, module_name, line_number):
            self.covered_lines.add((module_name, line_number))

        def get_coverage_report(self):
            return {
                "covered": len(self.covered_lines),
                "missing": len(self.missing_lines),
                "percentage": (
                    len(self.covered_lines)
                    / (len(self.covered_lines) + len(self.missing_lines))
                    * 100
                    if self.covered_lines or self.missing_lines
                    else 0
                ),
            }

    return CoverageMonitor()
