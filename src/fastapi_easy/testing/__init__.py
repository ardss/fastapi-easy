"""
FastAPI-Easy Testing Infrastructure

A comprehensive testing suite providing:
- High-performance test execution with parallel processing
- Intelligent caching mechanisms
- Advanced performance monitoring
- Optimized database utilities
- Comprehensive test reporting
"""

# Core components
from .performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    BenchmarkResult,
    LoadTester,
    performance_monitor,
    performance_test,
)

from .test_cache import (
    TestCache,
    CacheEntry,
    DatabaseCache,
    test_cache,
    db_cache,
    cached,
    cache_context,
    cache_test_data,
    cache_expensive_operation,
)

from .database_utils import (
    TransactionMetrics,
    OptimizedTransactionManager,
    TestDatabaseFactory,
    TestDataManager,
    database_test,
    performance_database_test,
    PerformanceWarning,
    test_data_manager,
)

from .test_reporter import (
    TestTiming,
    TestSuiteReport,
    TestReporter,
    test_reporter,
)

# Version and metadata
__version__ = "1.0.0"
__author__ = "FastAPI-Easy Team"

# Public API
__all__ = [
    # Performance Monitoring
    "PerformanceMonitor",
    "PerformanceMetrics",
    "BenchmarkResult",
    "LoadTester",
    "performance_monitor",
    "performance_test",

    # Test Caching
    "TestCache",
    "CacheEntry",
    "DatabaseCache",
    "test_cache",
    "db_cache",
    "cached",
    "cache_context",
    "cache_test_data",
    "cache_expensive_operation",

    # Database Utilities
    "TransactionMetrics",
    "OptimizedTransactionManager",
    "TestDatabaseFactory",
    "TestDataManager",
    "database_test",
    "performance_database_test",
    "PerformanceWarning",
    "test_data_manager",

    # Test Reporting
    "TestTiming",
    "TestSuiteReport",
    "TestReporter",
    "test_reporter",
]

# Utility functions for easy access
def setup_optimized_testing():
    """
    One-time setup for optimized testing infrastructure.
    Call this in your conftest.py or test setup.
    """
    import warnings

    # Configure warnings for testing
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)

    # Initialize performance monitor
    performance_monitor._load_baseline()

    # Clean up expired cache entries
    test_cache.cleanup_expired()

    return True

def get_test_infrastructure_summary():
    """
    Get summary of the testing infrastructure capabilities.
    """
    return {
        "version": __version__,
        "features": [
            "Parallel test execution with intelligent distribution",
            "Multi-level caching (memory, disk, Redis)",
            "Performance monitoring and regression detection",
            "Optimized database operations with connection pooling",
            "Comprehensive test reporting with visualizations",
            "Load testing and benchmarking utilities",
        ],
        "cache_backends": ["memory", "disk"] + (["redis"] if test_cache._redis_client else []),
        "supported_formats": ["json", "html", "csv"],
    }

# Initialize when module is imported
setup_optimized_testing()