"""Tests for database connection pool configuration"""

from fastapi_easy.core.pool import (
    PoolConfig,
    PoolConfigBuilder,
    development_pool_config,
    production_pool_config,
    high_performance_pool_config,
    testing_pool_config,
)


class TestPoolConfig:
    """Test PoolConfig class"""

    def test_pool_config_defaults(self):
        """Test default pool configuration"""
        config = PoolConfig()
        assert config.pool_size == 20
        assert config.max_overflow == 10
        assert config.pool_timeout == 30
        assert config.connect_timeout == 10
        assert config.pool_recycle == 3600
        assert config.pool_pre_ping is True

    def test_pool_config_to_dict(self):
        """Test converting config to dictionary"""
        config = PoolConfig(pool_size=30, max_overflow=15)
        config_dict = config.to_dict()

        assert config_dict["pool_size"] == 30
        assert config_dict["max_overflow"] == 15
        assert config_dict["pool_timeout"] == 30
        assert config_dict["pool_recycle"] == 3600


class TestPoolConfigBuilder:
    """Test PoolConfigBuilder class"""

    def test_builder_with_pool_size(self):
        """Test builder with pool size"""
        builder = PoolConfigBuilder()
        config = builder.with_pool_size(50).build()
        assert config.pool_size == 50

    def test_builder_with_max_overflow(self):
        """Test builder with max overflow"""
        builder = PoolConfigBuilder()
        config = builder.with_max_overflow(20).build()
        assert config.max_overflow == 20

    def test_builder_with_pool_timeout(self):
        """Test builder with pool timeout"""
        builder = PoolConfigBuilder()
        config = builder.with_pool_timeout(60).build()
        assert config.pool_timeout == 60

    def test_builder_with_connect_timeout(self):
        """Test builder with connect timeout"""
        builder = PoolConfigBuilder()
        config = builder.with_connect_timeout(20).build()
        assert config.connect_timeout == 20

    def test_builder_with_pool_recycle(self):
        """Test builder with pool recycle"""
        builder = PoolConfigBuilder()
        config = builder.with_pool_recycle(7200).build()
        assert config.pool_recycle == 7200

    def test_builder_with_pool_pre_ping(self):
        """Test builder with pool pre-ping"""
        builder = PoolConfigBuilder()
        config = builder.with_pool_pre_ping(False).build()
        assert config.pool_pre_ping is False

    def test_builder_with_echo(self):
        """Test builder with echo"""
        builder = PoolConfigBuilder()
        config = builder.with_echo(True).build()
        assert config.echo is True

    def test_builder_with_echo_pool(self):
        """Test builder with echo pool"""
        builder = PoolConfigBuilder()
        config = builder.with_echo_pool(True).build()
        assert config.echo_pool is True

    def test_builder_chaining(self):
        """Test builder method chaining"""
        config = (
            PoolConfigBuilder()
            .with_pool_size(40)
            .with_max_overflow(15)
            .with_pool_timeout(45)
            .with_connect_timeout(15)
            .build()
        )

        assert config.pool_size == 40
        assert config.max_overflow == 15
        assert config.pool_timeout == 45
        assert config.connect_timeout == 15


class TestPredefinedConfigs:
    """Test predefined pool configurations"""

    def test_development_pool_config(self):
        """Test development pool configuration"""
        config = development_pool_config()
        assert config.pool_size == 5
        assert config.max_overflow == 5
        assert config.pool_timeout == 10
        assert config.connect_timeout == 5
        assert config.pool_recycle == 1800

    def test_production_pool_config(self):
        """Test production pool configuration"""
        config = production_pool_config()
        assert config.pool_size == 20
        assert config.max_overflow == 10
        assert config.pool_timeout == 30
        assert config.connect_timeout == 10
        assert config.pool_recycle == 3600

    def test_high_performance_pool_config(self):
        """Test high-performance pool configuration"""
        config = high_performance_pool_config()
        assert config.pool_size == 50
        assert config.max_overflow == 20
        assert config.pool_timeout == 60
        assert config.connect_timeout == 15
        assert config.pool_recycle == 7200

    def test_testing_pool_config(self):
        """Test testing pool configuration"""
        config = testing_pool_config()
        assert config.pool_size == 2
        assert config.max_overflow == 2
        assert config.pool_timeout == 5
        assert config.connect_timeout == 3
        assert config.pool_recycle == 300

    def test_config_hierarchy(self):
        """Test configuration hierarchy by size"""
        dev = development_pool_config()
        prod = production_pool_config()
        perf = high_performance_pool_config()

        # Pool size should increase: dev < prod < perf
        assert dev.pool_size < prod.pool_size < perf.pool_size

        # Timeout should increase: dev < prod < perf
        assert dev.pool_timeout < prod.pool_timeout < perf.pool_timeout
