"""Cache key generation with collision prevention

This module provides secure cache key generation using JSON serialization
and MD5 hashing to prevent key collisions.
"""

import hashlib
import json
import logging
from typing import Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class CacheKeyGenerator:
    """Generate consistent cache keys without collisions

    Uses LRU cache to avoid memory leaks from unlimited key caching.
    """

    def __init__(self):
        """Initialize with LRU cache for key generation"""
        self._generate_cached = lru_cache(maxsize=10000)(self._generate_impl)

    def generate(self, operation: str, **kwargs) -> str:
        """Generate a cache key from operation and parameters

        Uses JSON serialization with sorted keys to ensure consistency,
        then applies MD5 hashing for compact representation.

        Args:
            operation: Operation name (e.g., 'get_one', 'get_all')
            **kwargs: Operation parameters

        Returns:
            Unique cache key

        Example:
            >>> gen = CacheKeyGenerator()
            >>> key1 = gen.generate('get_one', id=1)
            >>> key2 = gen.generate('get_one', id=1)
            >>> assert key1 == key2
        """
        # Convert kwargs to JSON string for hashability
        # This handles nested dicts and lists
        try:
            params_json = json.dumps(kwargs, sort_keys=True, default=str)
        except (TypeError, ValueError) as e:
            # Use fallback serialization for non-serializable objects
            logger.warning(f"Failed to serialize params: {str(e)}, using fallback")
            try:
                params_json = json.dumps({"params": str(kwargs)}, sort_keys=True)
            except Exception as fallback_error:
                logger.error(f"Fallback serialization failed: {str(fallback_error)}")
                # Last resort: use string representation
                params_json = json.dumps({"params": repr(kwargs)}, sort_keys=True)

        return self._generate_cached(operation, params_json)

    @staticmethod
    def _generate_impl(operation: str, params_json: str) -> str:
        """Internal implementation for cached key generation

        Args:
            operation: Operation name
            params_json: Parameters as JSON string

        Returns:
            Cache key
        """
        # Build key string with operation and params
        key_str = f"{operation}:{params_json}"

        # Generate MD5 hash for compact key
        key_hash = hashlib.md5(key_str.encode()).hexdigest()

        # Return prefixed key for debugging
        return f"{operation}:{key_hash}"

    def generate_list_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for list operations

        Args:
            operation: Operation name (e.g., 'get_all')
            **kwargs: Operation parameters (filters, sorts, pagination)

        Returns:
            Unique cache key for list operation
        """
        return self.generate(operation, **kwargs)

    def generate_single_key(self, operation: str, item_id: Any) -> str:
        """Generate cache key for single item operations

        Args:
            operation: Operation name (e.g., 'get_one')
            item_id: Item ID

        Returns:
            Unique cache key for single item
        """
        return self.generate(operation, id=item_id)

    @staticmethod
    def get_pattern(operation: str) -> str:
        """Get pattern for cache key matching

        Useful for invalidating all keys for a specific operation.

        Args:
            operation: Operation name

        Returns:
            Pattern string (e.g., 'get_all:*')
        """
        return f"{operation}:*"


# Singleton instance
_generator = CacheKeyGenerator()


def generate_cache_key(operation: str, **kwargs) -> str:
    """Generate cache key (convenience function)

    Args:
        operation: Operation name
        **kwargs: Operation parameters

    Returns:
        Cache key
    """
    return _generator.generate(operation, **kwargs)
