"""Configuration validation for optimization settings

Ensures all configuration values are valid before use.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validate optimization configuration"""

    @staticmethod
    def validate_cache_config(config: Dict[str, Any]) -> bool:
        """Validate cache configuration

        Args:
            config: Cache configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate L1 cache size
            l1_size = config.get("l1_size", 1000)
            if not isinstance(l1_size, int) or l1_size <= 0:
                logger.error(f"Invalid l1_size: {l1_size}. Must be positive integer.")
                return False

            # Validate L1 TTL
            l1_ttl = config.get("l1_ttl", 60)
            if not isinstance(l1_ttl, int) or l1_ttl <= 0:
                logger.error(f"Invalid l1_ttl: {l1_ttl}. Must be positive integer.")
                return False

            # Validate L2 cache size
            l2_size = config.get("l2_size", 10000)
            if not isinstance(l2_size, int) or l2_size <= 0:
                logger.error(f"Invalid l2_size: {l2_size}. Must be positive integer.")
                return False

            # Validate L2 TTL
            l2_ttl = config.get("l2_ttl", 600)
            if not isinstance(l2_ttl, int) or l2_ttl <= 0:
                logger.error(f"Invalid l2_ttl: {l2_ttl}. Must be positive integer.")
                return False

            # Validate L2 >= L1
            if l2_size < l1_size:
                logger.warning(f"L2 size ({l2_size}) should be >= L1 size ({l1_size})")

            return True
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Cache config validation error: {e!s}")
            return False
        except Exception as e:
            logger.error(f"Cache config validation failed: {e!s}")
            return False

    @staticmethod
    def validate_async_config(config: Dict[str, Any]) -> bool:
        """Validate async configuration

        Args:
            config: Async configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate max concurrent
            max_concurrent = config.get("max_concurrent", 10)
            if not isinstance(max_concurrent, int) or max_concurrent <= 0:
                logger.error(f"Invalid max_concurrent: {max_concurrent}. Must be positive integer.")
                return False

            # Validate batch size
            batch_size = config.get("batch_size", 100)
            if not isinstance(batch_size, int) or batch_size <= 0:
                logger.error(f"Invalid batch_size: {batch_size}. Must be positive integer.")
                return False

            return True
        except Exception as e:
            logger.error(f"Async config validation failed: {e!s}")
            return False

    @staticmethod
    def validate_timeout(timeout: float) -> bool:
        """Validate query timeout

        Args:
            timeout: Timeout in seconds

        Returns:
            True if valid, False otherwise
        """
        try:
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                logger.error(f"Invalid timeout: {timeout}. Must be positive number.")
                return False

            if timeout > 3600:  # Max 1 hour
                logger.warning(f"Timeout {timeout}s is very large")

            return True
        except Exception as e:
            logger.error(f"Timeout validation failed: {e!s}")
            return False

    @staticmethod
    def validate_optimization_config(config: Dict[str, Any]) -> bool:
        """Validate optimization configuration

        Args:
            config: Optimization configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate L1 size <= L2 size
            l1_size = config.get("l1_size", 1000)
            l2_size = config.get("l2_size", 10000)
            if l1_size > l2_size:
                logger.error(f"L1 size ({l1_size}) should be <= L2 size ({l2_size})")
                return False

            # Validate L1 TTL <= L2 TTL
            l1_ttl = config.get("l1_ttl", 60)
            l2_ttl = config.get("l2_ttl", 600)
            if l1_ttl > l2_ttl:
                logger.error(f"L1 TTL ({l1_ttl}) should be <= L2 TTL ({l2_ttl})")
                return False

            # Validate hit_rate_threshold
            threshold = config.get("hit_rate_threshold", 50.0)
            if not (0 <= threshold <= 100):
                logger.error(f"hit_rate_threshold ({threshold}) should be between 0 and 100")
                return False

            # Validate max_concurrent
            max_concurrent = config.get("max_concurrent", 10)
            if max_concurrent < 1 or max_concurrent > 1000:
                logger.error(f"max_concurrent ({max_concurrent}) should be between 1 and 1000")
                return False

            return True
        except Exception as e:
            logger.error(f"Optimization config validation failed: {e!s}")
            return False
