"""Cache key generation with collision prevention

This module provides secure cache key generation using JSON serialization
and MD5 hashing to prevent key collisions.
"""

import hashlib
import json
from typing import Any, Dict


class CacheKeyGenerator:
    """Generate consistent cache keys without collisions"""
    
    @staticmethod
    def generate(operation: str, **kwargs) -> str:
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
        # Build key dictionary with operation
        key_dict: Dict[str, Any] = {"op": operation}
        key_dict.update(kwargs)
        
        # Serialize to JSON with sorted keys for consistency
        try:
            key_str = json.dumps(key_dict, sort_keys=True, default=str)
        except (TypeError, ValueError) as e:
            # Fallback for non-serializable objects
            key_str = json.dumps(
                {
                    "op": operation,
                    "params": str(kwargs)
                },
                sort_keys=True
            )
        
        # Generate MD5 hash for compact key
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        
        # Return prefixed key for debugging
        return f"{operation}:{key_hash}"
    
    @staticmethod
    def generate_list_key(operation: str, **kwargs) -> str:
        """Generate cache key for list operations
        
        Args:
            operation: Operation name (e.g., 'get_all')
            **kwargs: Operation parameters (filters, sorts, pagination)
            
        Returns:
            Unique cache key for list operation
        """
        return CacheKeyGenerator.generate(operation, **kwargs)
    
    @staticmethod
    def generate_single_key(operation: str, item_id: Any) -> str:
        """Generate cache key for single item operations
        
        Args:
            operation: Operation name (e.g., 'get_one')
            item_id: Item ID
            
        Returns:
            Unique cache key for single item
        """
        return CacheKeyGenerator.generate(operation, id=item_id)
    
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
