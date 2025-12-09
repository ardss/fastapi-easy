"""Optimization configuration management.

This module provides comprehensive configuration management for performance
optimization features in FastAPI-Easy. It supports environment variable
configuration, JSON file loading, and runtime configuration updates.

The configuration controls:
- Cache settings (L1/L2 cache sizes and TTL)
- Async operation limits
- Database connection pooling
- Performance monitoring thresholds
- Memory optimization parameters

Example:
    ```python
    # Load from environment variables
    config = OptimizationConfig.from_env()

    # Or create with custom settings
    config = OptimizationConfig(
        enable_cache=True,
        l1_size=5000,
        l1_ttl=300,
        hit_rate_threshold=80.0
    )
    ```
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class OptimizationConfig:
    """Configuration for performance optimizations.

    Centralizes all performance-related configuration options in a single
    class for easy management and validation. Supports initialization from
    environment variables, JSON files, or direct parameter setting.

    Attributes:
        enable_cache: Enable caching system
        enable_async: Enable async optimizations
        l1_size: L1 (in-memory) cache size
        l1_ttl: L1 cache TTL in seconds
        l2_size: L2 (distributed) cache size
        l2_ttl: L2 cache TTL in seconds
        max_concurrent: Maximum concurrent async operations
        enable_monitoring: Enable performance monitoring
        hit_rate_threshold: Cache hit rate threshold for alerts
        pool_size: Database connection pool size
        max_overflow: Maximum overflow connections
        pool_timeout: Pool acquisition timeout in seconds
        pool_recycle: Connection recycle time in seconds
        query_timeout: Query execution timeout in seconds
        cache_size: General cache size (legacy)
        cache_ttl: General cache TTL in seconds (legacy)
    """

    def __init__(
        self,
        enable_cache: bool = True,
        enable_async: bool = True,
        l1_size: int = 1000,
        l1_ttl: int = 60,
        l2_size: int = 10000,
        l2_ttl: int = 600,
        max_concurrent: int = 10,
        enable_monitoring: bool = True,
        hit_rate_threshold: float = 50.0,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        query_timeout: int = 30,
        cache_size: int = 10000,
        cache_ttl: int = 600,
    ):
        """Initialize optimization config

        Args:
            enable_cache: Enable caching
            enable_async: Enable async optimization
            l1_size: L1 cache size
            l1_ttl: L1 cache TTL (seconds)
            l2_size: L2 cache size
            l2_ttl: L2 cache TTL (seconds)
            max_concurrent: Max concurrent operations
            enable_monitoring: Enable monitoring
            hit_rate_threshold: Cache hit rate threshold for alerts
            pool_size: Database connection pool size
            max_overflow: Max overflow connections for pool
            pool_timeout: Pool timeout in seconds
            pool_recycle: Database connection recycle time in seconds
            query_timeout: Database query timeout in seconds
            cache_size: General cache size
            cache_ttl: General cache TTL in seconds
        """
        self.enable_cache = enable_cache
        self.enable_async = enable_async
        self.l1_size = l1_size
        self.l1_ttl = l1_ttl
        self.l2_size = l2_size
        self.l2_ttl = l2_ttl
        self.max_concurrent = max_concurrent
        self.enable_monitoring = enable_monitoring
        self.hit_rate_threshold = hit_rate_threshold
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.query_timeout = query_timeout
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl

    @classmethod
    def from_env(cls) -> OptimizationConfig:
        """Load configuration from environment variables

        Supported variables:
        - FASTAPI_EASY_ENABLE_CACHE (true/false)
        - FASTAPI_EASY_ENABLE_ASYNC (true/false)
        - FASTAPI_EASY_L1_SIZE (int)
        - FASTAPI_EASY_L1_TTL (int)
        - FASTAPI_EASY_L2_SIZE (int)
        - FASTAPI_EASY_L2_TTL (int)
        - FASTAPI_EASY_MAX_CONCURRENT (int)
        - FASTAPI_EASY_ENABLE_MONITORING (true/false)
        - FASTAPI_EASY_HIT_RATE_THRESHOLD (float)

        Returns:
            Configuration instance
        """

        def parse_bool(value: str, default: bool) -> bool:
            if value.lower() in ("true", "1", "yes"):
                return True
            elif value.lower() in ("false", "0", "no"):
                return False
            return default

        return cls(
            enable_cache=parse_bool(os.getenv("FASTAPI_EASY_ENABLE_CACHE", "true"), True),
            enable_async=parse_bool(os.getenv("FASTAPI_EASY_ENABLE_ASYNC", "true"), True),
            l1_size=int(os.getenv("FASTAPI_EASY_L1_SIZE", "1000")),
            l1_ttl=int(os.getenv("FASTAPI_EASY_L1_TTL", "60")),
            l2_size=int(os.getenv("FASTAPI_EASY_L2_SIZE", "10000")),
            l2_ttl=int(os.getenv("FASTAPI_EASY_L2_TTL", "600")),
            max_concurrent=int(os.getenv("FASTAPI_EASY_MAX_CONCURRENT", "10")),
            enable_monitoring=parse_bool(os.getenv("FASTAPI_EASY_ENABLE_MONITORING", "true"), True),
            hit_rate_threshold=float(os.getenv("FASTAPI_EASY_HIT_RATE_THRESHOLD", "50.0")),
        )

    @classmethod
    def from_file(cls, path: str) -> OptimizationConfig:
        """Load configuration from JSON file

        Args:
            path: Path to JSON configuration file

        Returns:
            Configuration instance
        """
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with config_path.open() as f:
            config_dict = json.load(f)

        return cls(**config_dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary

        Returns:
            Configuration dictionary
        """
        return {
            "enable_cache": self.enable_cache,
            "enable_async": self.enable_async,
            "l1_size": self.l1_size,
            "l1_ttl": self.l1_ttl,
            "l2_size": self.l2_size,
            "l2_ttl": self.l2_ttl,
            "max_concurrent": self.max_concurrent,
            "enable_monitoring": self.enable_monitoring,
            "hit_rate_threshold": self.hit_rate_threshold,
        }

    def to_json(self) -> str:
        """Convert configuration to JSON string

        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(), indent=2)

    def save_to_file(self, path: str) -> None:
        """Save configuration to JSON file

        Args:
            path: Path to save configuration
        """
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with config_path.open("w") as f:
            f.write(self.to_json())


def create_optimization_config(
    enable_cache: bool = True,
    enable_async: bool = True,
    **kwargs: Any,
) -> OptimizationConfig:
    """Create optimization configuration

    Args:
        enable_cache: Enable caching
        enable_async: Enable async optimization
        **kwargs: Additional configuration parameters

    Returns:
        Configuration instance
    """
    return OptimizationConfig(
        enable_cache=enable_cache,
        enable_async=enable_async,
        **kwargs,
    )
