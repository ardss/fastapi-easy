"""
Performance Configuration System

This module provides comprehensive configuration for performance tuning:
- Environment-specific performance settings
- Dynamic configuration updates
- Performance profile presets
- Configuration validation
- Auto-optimization based on system resources
"""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


@dataclass
class LockConfig:
    """Configuration for distributed locks"""

    max_retries: int = 20
    base_retry_delay: float = 0.01  # 10ms
    max_retry_delay: float = 5.0
    connection_timeout: float = 5.0
    lock_timeout: int = 30
    cleanup_interval: int = 60
    jitter_enabled: bool = True
    jitter_factor: float = 0.1


@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pools"""

    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    health_check_interval: float = 30.0
    connection_max_age: float = 300.0


@dataclass
class CacheConfig:
    """Configuration for caching"""

    l1_cache_size: int = 1000
    l1_ttl: int = 300  # 5 minutes
    l2_cache_size: int = 10000
    l2_ttl: int = 3600  # 1 hour
    enable_compression: bool = True
    compression_threshold: int = 1024


@dataclass
class QueryOptimizationConfig:
    """Configuration for query optimization"""

    type_cache_size: int = 1000
    json_cache_size: int = 500
    validation_cache_size: int = 1000
    batch_size: int = 100
    batch_delay: float = 0.1
    enable_parallel_processing: bool = True
    max_workers: Optional[int] = None


@dataclass
class MemoryOptimizationConfig:
    """Configuration for memory optimization"""

    cleanup_interval: float = 60.0
    max_resource_age: float = 300.0
    enable_leak_detection: bool = True
    gc_threshold: int = 700
    memory_pool_size: int = 1000
    object_size: int = 1024


@dataclass
class AsyncOptimizationConfig:
    """Configuration for async optimization"""

    semaphore_limit: int = 10
    rate_limit: int = 100
    rate_period: float = 1.0
    batch_size: int = 50
    batch_wait_time: float = 0.1
    max_concurrent_batches: int = 5
    connection_pool_size: int = 10
    connection_min_size: int = 2


@dataclass
class MonitoringConfig:
    """Configuration for performance monitoring"""

    enabled: bool = True
    metrics_history: int = 1000
    resource_interval: float = 5.0
    export_interval: float = 60.0
    alert_cpu_threshold: float = 90.0
    alert_memory_threshold: float = 1000.0  # MB
    alert_response_time_threshold: float = 1000.0  # ms
    enable_profiling: bool = True


@dataclass
class PerformanceConfig:
    """Main performance configuration"""

    environment: str = "production"  # development, staging, production
    profile: str = "balanced"  # minimal, balanced, maximum

    # Component configurations
    lock: LockConfig = field(default_factory=LockConfig)
    connection_pool: ConnectionPoolConfig = field(default_factory=ConnectionPoolConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    query_optimization: QueryOptimizationConfig = field(default_factory=QueryOptimizationConfig)
    memory_optimization: MemoryOptimizationConfig = field(default_factory=MemoryOptimizationConfig)
    async_optimization: AsyncOptimizationConfig = field(default_factory=AsyncOptimizationConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    # Auto-optimization settings
    auto_optimize: bool = True
    optimize_for_cpu: bool = True
    optimize_for_memory: bool = True
    optimize_for_io: bool = True


class PerformanceProfileManager:
    """Manages performance profiles and presets"""

    PRESETS = {
        "minimal": {
            "lock": {"max_retries": 5, "base_retry_delay": 0.05},
            "connection_pool": {"pool_size": 2, "max_overflow": 5},
            "cache": {"l1_cache_size": 100, "l2_cache_size": 1000},
            "query_optimization": {"batch_size": 25, "enable_parallel_processing": False},
            "memory_optimization": {"enable_leak_detection": False},
            "async_optimization": {"semaphore_limit": 5, "rate_limit": 50},
            "monitoring": {"enabled": False},
        },
        "balanced": {
            "lock": {"max_retries": 15, "base_retry_delay": 0.02},
            "connection_pool": {"pool_size": 5, "max_overflow": 10},
            "cache": {"l1_cache_size": 500, "l2_cache_size": 5000},
            "query_optimization": {"batch_size": 50, "enable_parallel_processing": True},
            "memory_optimization": {"enable_leak_detection": True},
            "async_optimization": {"semaphore_limit": 10, "rate_limit": 100},
            "monitoring": {"enabled": True},
        },
        "maximum": {
            "lock": {"max_retries": 30, "base_retry_delay": 0.005},
            "connection_pool": {"pool_size": 10, "max_overflow": 20},
            "cache": {"l1_cache_size": 2000, "l2_cache_size": 20000},
            "query_optimization": {"batch_size": 200, "max_workers": None},
            "memory_optimization": {"gc_threshold": 500},
            "async_optimization": {"semaphore_limit": 20, "rate_limit": 200},
            "monitoring": {"enabled": True, "resource_interval": 1.0},
        },
    }

    ENVIRONMENT_OVERRIDES = {
        "development": {
            "lock": {"lock_timeout": 10},
            "cache": {"l1_ttl": 60, "l2_ttl": 300},
            "monitoring": {"export_interval": 30.0},
        },
        "staging": {
            "lock": {"lock_timeout": 20},
            "cache": {"l1_ttl": 180, "l2_ttl": 1800},
            "monitoring": {"export_interval": 60.0},
        },
        "production": {
            "lock": {"lock_timeout": 30},
            "cache": {"l1_ttl": 300, "l2_ttl": 3600},
            "monitoring": {"export_interval": 300.0},
        },
    }

    @classmethod
    def get_preset(cls, profile_name: str) -> Dict[str, Any]:
        """Get preset configuration"""
        return cls.PRESETS.get(profile_name, cls.PRESETS["balanced"])

    @classmethod
    def get_environment_overrides(cls, environment: str) -> Dict[str, Any]:
        """Get environment-specific overrides"""
        return cls.ENVIRONMENT_OVERRIDES.get(environment, {})


class SystemResourceAnalyzer:
    """Analyzes system resources for auto-optimization"""

    @staticmethod
    def get_cpu_info() -> Dict[str, Any]:
        """Get CPU information"""
        return {
            "count": multiprocessing.cpu_count(),
            "freq": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            "percent": psutil.cpu_percent(interval=1),
        }

    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """Get memory information"""
        virtual_memory = psutil.virtual_memory()
        return {
            "total_gb": virtual_memory.total / 1024 / 1024 / 1024,
            "available_gb": virtual_memory.available / 1024 / 1024 / 1024,
            "percent": virtual_memory.percent,
            "used_gb": virtual_memory.used / 1024 / 1024 / 1024,
        }

    @staticmethod
    def get_system_profile() -> str:
        """Determine system performance profile"""
        cpu_count = multiprocessing.cpu_count()
        memory_gb = psutil.virtual_memory().total / 1024 / 1024 / 1024

        if cpu_count >= 16 and memory_gb >= 32:
            return "maximum"
        elif cpu_count >= 8 and memory_gb >= 16:
            return "balanced"
        else:
            return "minimal"

    @staticmethod
    def optimize_config_for_system(config: PerformanceConfig) -> PerformanceConfig:
        """Auto-optimize configuration based on system resources"""
        cpu_info = SystemResourceAnalyzer.get_cpu_info()
        memory_info = SystemResourceAnalyzer.get_memory_info()

        # Optimize based on CPU cores
        cpu_cores = cpu_info["count"]
        config.async_optimization.semaphore_limit = min(cpu_cores * 2, 50)
        config.async_optimization.rate_limit = cpu_cores * 20
        config.connection_pool.pool_size = min(cpu_cores, 20)

        # Optimize based on available memory
        memory_gb = memory_info["total_gb"]
        if memory_gb < 4:
            # Low memory system
            config.cache.l1_cache_size = 100
            config.cache.l2_cache_size = 1000
            config.memory_optimization.gc_threshold = 500
            config.monitoring.metrics_history = 500
        elif memory_gb > 16:
            # High memory system
            config.cache.l1_cache_size = 2000
            config.cache.l2_cache_size = 20000
            config.monitoring.metrics_history = 2000

        # Optimize based on CPU usage
        if cpu_info["percent"] > 80:
            # High CPU load
            config.async_optimization.semaphore_limit = min(
                config.async_optimization.semaphore_limit, cpu_cores
            )
            config.query_optimization.enable_parallel_processing = False
        elif cpu_info["percent"] < 30:
            # Low CPU load
            config.async_optimization.semaphore_limit = cpu_cores * 3

        return config


class PerformanceConfigManager:
    """Manages performance configuration with validation and auto-optimization"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "performance_config.json"
        self.config = PerformanceConfig()
        self._validators: List[Callable[[PerformanceConfig], None]] = []
        self._update_callbacks: List[Callable[[PerformanceConfig], None]] = []

        # Load configuration
        self.load_config()

        # Add default validators
        self._add_default_validators()

    def _add_default_validators(self):
        """Add default configuration validators"""

        def validate_lock_config(config: PerformanceConfig):
            if config.lock.max_retries <= 0:
                raise ValueError("Lock max_retries must be positive")
            if config.lock.base_retry_delay < 0:
                raise ValueError("Lock base_retry_delay must be non-negative")

        def validate_pool_config(config: PerformanceConfig):
            if config.connection_pool.pool_size <= 0:
                raise ValueError("Connection pool size must be positive")
            if config.connection_pool.max_overflow < 0:
                raise ValueError("Connection pool overflow must be non-negative")

        def validate_cache_config(config: PerformanceConfig):
            if config.cache.l1_cache_size <= 0:
                raise ValueError("L1 cache size must be positive")
            if config.cache.l2_cache_size < config.cache.l1_cache_size:
                raise ValueError("L2 cache size must be >= L1 cache size")

        self._validators.extend([validate_lock_config, validate_pool_config, validate_cache_config])

    def load_config(self) -> PerformanceConfig:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file) as f:
                    config_data = json.load(f)

                # Apply profile presets
                profile = config_data.get("profile", "balanced")
                preset_data = PerformanceProfileManager.get_preset(profile)
                self._merge_config(config_data, preset_data)

                # Apply environment overrides
                environment = config_data.get("environment", "production")
                env_overrides = PerformanceProfileManager.get_environment_overrides(environment)
                self._merge_config(config_data, env_overrides)

                # Update config object
                self._update_config_from_dict(config_data)

                logger.info(f"Performance configuration loaded from {self.config_file}")
            else:
                # Use auto-optimization for new config
                self.auto_optimize()

        except Exception as e:
            logger.error(f"Failed to load performance config: {e}")
            logger.info("Using default configuration")

        return self.config

    def save_config(self):
        """Save configuration to file"""
        try:
            config_dict = asdict(self.config)
            with open(self.config_file, "w") as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"Performance configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save performance config: {e}")

    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Merge source config into target"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value

    def _update_config_from_dict(self, config_data: Dict[str, Any]):
        """Update config object from dictionary"""
        # Update main fields
        if "environment" in config_data:
            self.config.environment = config_data["environment"]
        if "profile" in config_data:
            self.config.profile = config_data["profile"]
        if "auto_optimize" in config_data:
            self.config.auto_optimize = config_data["auto_optimize"]

        # Update component configurations
        if "lock" in config_data:
            self._update_dataclass(self.config.lock, config_data["lock"])
        if "connection_pool" in config_data:
            self._update_dataclass(self.config.connection_pool, config_data["connection_pool"])
        if "cache" in config_data:
            self._update_dataclass(self.config.cache, config_data["cache"])
        if "query_optimization" in config_data:
            self._update_dataclass(
                self.config.query_optimization, config_data["query_optimization"]
            )
        if "memory_optimization" in config_data:
            self._update_dataclass(
                self.config.memory_optimization, config_data["memory_optimization"]
            )
        if "async_optimization" in config_data:
            self._update_dataclass(
                self.config.async_optimization, config_data["async_optimization"]
            )
        if "monitoring" in config_data:
            self._update_dataclass(self.config.monitoring, config_data["monitoring"])

    def _update_dataclass(self, obj: Any, data: Dict[str, Any]):
        """Update dataclass object from dictionary"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

    def validate_config(self, config: Optional[PerformanceConfig] = None) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        config = config or self.config

        for validator in self._validators:
            try:
                validator(config)
            except ValueError as e:
                errors.append(str(e))

        return errors

    def update_config(self, updates: Dict[str, Any], save: bool = True):
        """Update configuration with validation"""
        # Create copy for validation
        old_config = self.config
        self.config = PerformanceConfig(
            environment=old_config.environment, profile=old_config.profile
        )

        try:
            # Apply updates
            self._update_config_from_dict(updates)

            # Validate
            errors = self.validate_config()
            if errors:
                # Restore old config
                self.config = old_config
                raise ValueError(f"Configuration validation failed: {', '.join(errors)}")

            # Auto-optimize if enabled
            if self.config.auto_optimize:
                self.auto_optimize()

            # Notify callbacks
            for callback in self._update_callbacks:
                callback(self.config)

            # Save if requested
            if save:
                self.save_config()

            logger.info("Performance configuration updated successfully")

        except Exception as e:
            # Restore old config on error
            self.config = old_config
            logger.error(f"Failed to update configuration: {e}")
            raise

    def auto_optimize(self):
        """Auto-optimize configuration based on system resources"""
        if (
            self.config.optimize_for_cpu
            or self.config.optimize_for_memory
            or self.config.optimize_for_io
        ):
            self.config = SystemResourceAnalyzer.optimize_config_for_system(self.config)
            logger.info("Configuration auto-optimized for system resources")

    def set_profile(self, profile: str, save: bool = True):
        """Set performance profile"""
        if profile not in PerformanceProfileManager.PRESETS:
            raise ValueError(f"Unknown profile: {profile}")

        updates = {"profile": profile}
        self.update_config(updates, save)

    def set_environment(self, environment: str, save: bool = True):
        """Set environment"""
        if environment not in PerformanceProfileManager.ENVIRONMENT_OVERRIDES:
            logger.warning(f"Unknown environment: {environment}")

        updates = {"environment": environment}
        self.update_config(updates, save)

    def add_validator(self, validator: Callable[[PerformanceConfig], None]):
        """Add configuration validator"""
        self._validators.append(validator)

    def add_update_callback(self, callback: Callable[[PerformanceConfig], None]):
        """Add configuration update callback"""
        self._update_callbacks.append(callback)

    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            "environment": self.config.environment,
            "profile": self.config.profile,
            "auto_optimize": self.config.auto_optimize,
            "lock": {
                "max_retries": self.config.lock.max_retries,
                "timeout": self.config.lock.lock_timeout,
            },
            "connection_pool": {
                "size": self.config.connection_pool.pool_size,
                "overflow": self.config.connection_pool.max_overflow,
            },
            "cache": {
                "l1_size": self.config.cache.l1_cache_size,
                "l2_size": self.config.cache.l2_cache_size,
            },
            "monitoring": {
                "enabled": self.config.monitoring.enabled,
                "interval": self.config.monitoring.resource_interval,
            },
        }

    def export_config(self, filename: str):
        """Export configuration to file"""
        try:
            config_dict = asdict(self.config)
            with open(filename, "w") as f:
                json.dump(config_dict, f, indent=2, default=str)
            logger.info(f"Configuration exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")


# Global configuration manager instance
_global_config_manager: Optional[PerformanceConfigManager] = None


def get_performance_config_manager() -> PerformanceConfigManager:
    """Get or create global performance configuration manager"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = PerformanceConfigManager()
    return _global_config_manager


def get_performance_config() -> PerformanceConfig:
    """Get current performance configuration"""
    return get_performance_config_manager().config


def configure_performance(
    environment: Optional[str] = None,
    profile: Optional[str] = None,
    auto_optimize: Optional[bool] = None,
    config_file: Optional[str] = None,
) -> PerformanceConfig:
    """Configure performance settings"""
    manager = get_performance_config_manager()

    updates = {}
    if environment is not None:
        updates["environment"] = environment
    if profile is not None:
        updates["profile"] = profile
    if auto_optimize is not None:
        updates["auto_optimize"] = auto_optimize

    if updates:
        manager.update_config(updates)

    return manager.config


# Environment-based configuration helpers
def is_development() -> bool:
    """Check if running in development environment"""
    return get_performance_config().environment == "development"


def is_production() -> bool:
    """Check if running in production environment"""
    return get_performance_config().environment == "production"


def is_debug_enabled() -> bool:
    """Check if debugging is enabled"""
    return os.environ.get("DEBUG", "false").lower() == "true" or is_development()
