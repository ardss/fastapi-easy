"""Database connection pool configuration and management"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class PoolConfig:
    """Database connection pool configuration"""

    # Pool size settings
    pool_size: int = 20
    """Number of connections to maintain in the pool"""

    max_overflow: int = 10
    """Maximum number of connections to create beyond pool_size"""

    # Connection timeout settings
    pool_timeout: int = 30
    """Timeout for getting a connection from the pool (seconds)"""

    connect_timeout: int = 10
    """Timeout for establishing a new connection (seconds)"""

    # Connection lifecycle settings
    pool_recycle: int = 3600
    """Recycle connections after this many seconds (1 hour)"""

    pool_pre_ping: bool = True
    """Test connections before using them"""

    # Connection behavior
    echo: bool = False
    """Log all SQL statements"""

    echo_pool: bool = False
    """Log connection pool events"""

    # Advanced settings
    max_cached_statement_lifetime: int = 3600
    """Maximum lifetime of cached statements (seconds)"""

    max_overflow_recycle: int = 1800
    """Recycle overflow connections after this many seconds"""

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary

        Returns:
            Configuration dictionary
        """
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "connect_timeout": self.connect_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "echo": self.echo,
            "echo_pool": self.echo_pool,
            "max_cached_statement_lifetime": self.max_cached_statement_lifetime,
            "max_overflow_recycle": self.max_overflow_recycle,
        }


class PoolConfigBuilder:
    """Builder for creating pool configurations"""

    def __init__(self) -> None:
        """Initialize builder with default config"""
        self.config = PoolConfig()

    def with_pool_size(self, size: int) -> PoolConfigBuilder:
        """Set pool size

        Args:
            size: Number of connections in pool

        Returns:
            Self for chaining
        """
        self.config.pool_size = size
        return self

    def with_max_overflow(self, overflow: int) -> PoolConfigBuilder:
        """Set max overflow

        Args:
            overflow: Maximum overflow connections

        Returns:
            Self for chaining
        """
        self.config.max_overflow = overflow
        return self

    def with_pool_timeout(self, timeout: int) -> PoolConfigBuilder:
        """Set pool timeout

        Args:
            timeout: Timeout in seconds

        Returns:
            Self for chaining
        """
        self.config.pool_timeout = timeout
        return self

    def with_connect_timeout(self, timeout: int) -> PoolConfigBuilder:
        """Set connect timeout

        Args:
            timeout: Timeout in seconds

        Returns:
            Self for chaining
        """
        self.config.connect_timeout = timeout
        return self

    def with_pool_recycle(self, seconds: int) -> PoolConfigBuilder:
        """Set pool recycle time

        Args:
            seconds: Recycle time in seconds

        Returns:
            Self for chaining
        """
        self.config.pool_recycle = seconds
        return self

    def with_pool_pre_ping(self, enabled: bool) -> PoolConfigBuilder:
        """Enable/disable pool pre-ping

        Args:
            enabled: Whether to enable pre-ping

        Returns:
            Self for chaining
        """
        self.config.pool_pre_ping = enabled
        return self

    def with_echo(self, enabled: bool) -> PoolConfigBuilder:
        """Enable/disable SQL echo

        Args:
            enabled: Whether to enable echo

        Returns:
            Self for chaining
        """
        self.config.echo = enabled
        return self

    def with_echo_pool(self, enabled: bool) -> PoolConfigBuilder:
        """Enable/disable pool echo

        Args:
            enabled: Whether to enable pool echo

        Returns:
            Self for chaining
        """
        self.config.echo_pool = enabled
        return self

    def build(self) -> PoolConfig:
        """Build the configuration

        Returns:
            Pool configuration
        """
        return self.config


# Predefined configurations
def development_pool_config() -> PoolConfig:
    """Get development environment pool configuration

    Returns:
        Development pool configuration
    """
    return PoolConfig(
        pool_size=5,
        max_overflow=5,
        pool_timeout=10,
        connect_timeout=5,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False,
    )


def production_pool_config() -> PoolConfig:
    """Get production environment pool configuration

    Returns:
        Production pool configuration
    """
    return PoolConfig(
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        connect_timeout=10,
        pool_recycle=3600,
        pool_pre_ping=True,
        echo=False,
        echo_pool=False,
    )


def high_performance_pool_config() -> PoolConfig:
    """Get high-performance pool configuration

    Returns:
        High-performance pool configuration
    """
    return PoolConfig(
        pool_size=50,
        max_overflow=20,
        pool_timeout=60,
        connect_timeout=15,
        pool_recycle=7200,
        pool_pre_ping=True,
        echo=False,
        echo_pool=False,
    )


def testing_pool_config() -> PoolConfig:
    """Get testing environment pool configuration

    Returns:
        Testing pool configuration
    """
    return PoolConfig(
        pool_size=2,
        max_overflow=2,
        pool_timeout=5,
        connect_timeout=3,
        pool_recycle=300,
        pool_pre_ping=True,
        echo=False,
    )
