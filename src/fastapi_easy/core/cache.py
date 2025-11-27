"""Caching support for FastAPI-Easy"""

from typing import Any, Dict, Optional, Protocol
from abc import ABC, abstractmethod
import time
from datetime import datetime, timedelta


class CacheEntry:
    """Cache entry with TTL support"""
    
    def __init__(self, value: Any, ttl: Optional[int] = None):
        """Initialize cache entry
        
        Args:
            value: Cached value
            ttl: Time to live in seconds
        """
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Check if entry is expired
        
        Returns:
            True if expired
        """
        if self.ttl is None:
            return False
        
        return time.time() - self.created_at > self.ttl
    
    def get(self) -> Optional[Any]:
        """Get value if not expired
        
        Returns:
            Value or None if expired
        """
        if self.is_expired():
            return None
        
        return self.value


class BaseCache(ABC):
    """Base cache class"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache
        
        Args:
            key: Cache key
        """
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache"""
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        pass


class MemoryCache(BaseCache):
    """In-memory cache implementation"""
    
    def __init__(self, max_size: int = 1000):
        """Initialize memory cache
        
        Args:
            max_size: Maximum cache size
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        value = entry.get()
        
        if value is None:
            del self.cache[key]
            self.misses += 1
            return None
        
        self.hits += 1
        return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        # Evict oldest entry if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
            del self.cache[oldest_key]
        
        self.cache[key] = CacheEntry(value, ttl)
    
    async def delete(self, key: str) -> None:
        """Delete value from cache
        
        Args:
            key: Cache key
        """
        if key in self.cache:
            del self.cache[key]
    
    async def clear(self) -> None:
        """Clear all cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists
        """
        if key not in self.cache:
            return False
        
        entry = self.cache[key]
        return entry.get() is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics
        
        Returns:
            Statistics dictionary
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }


class NoCache(BaseCache):
    """No-op cache implementation"""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (always returns None)
        
        Args:
            key: Cache key
            
        Returns:
            None
        """
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache (no-op)
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
        """
        pass
    
    async def delete(self, key: str) -> None:
        """Delete value from cache (no-op)
        
        Args:
            key: Cache key
        """
        pass
    
    async def clear(self) -> None:
        """Clear all cache (no-op)"""
        pass
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache (always returns False)
        
        Args:
            key: Cache key
            
        Returns:
            False
        """
        return False


class CacheKey:
    """Cache key builder"""
    
    @staticmethod
    def build(prefix: str, *args: Any, **kwargs: Any) -> str:
        """Build cache key
        
        Args:
            prefix: Key prefix
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key
        """
        parts = [prefix]
        
        for arg in args:
            parts.append(str(arg))
        
        for key, value in sorted(kwargs.items()):
            parts.append(f"{key}={value}")
        
        return ":".join(parts)


class CachedOperation:
    """Decorator for caching operation results"""
    
    def __init__(self, cache: BaseCache, ttl: Optional[int] = None, prefix: str = ""):
        """Initialize cached operation
        
        Args:
            cache: Cache instance
            ttl: Time to live in seconds
            prefix: Cache key prefix
        """
        self.cache = cache
        self.ttl = ttl
        self.prefix = prefix
    
    def __call__(self, func):
        """Decorate function
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function
        """
        import asyncio
        import inspect
        
        if inspect.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # Build cache key
                cache_key = CacheKey.build(self.prefix or func.__name__, *args, **kwargs)
                
                # Try to get from cache
                cached_value = await self.cache.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Store in cache
                await self.cache.set(cache_key, result, self.ttl)
                
                return result
            
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # Build cache key
                cache_key = CacheKey.build(self.prefix or func.__name__, *args, **kwargs)
                
                # Try to get from cache
                # For sync functions, we need to run async cache operations in event loop
                loop = asyncio.new_event_loop()
                try:
                    cached_value = loop.run_until_complete(self.cache.get(cache_key))
                    if cached_value is not None:
                        return cached_value
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Store in cache
                    loop.run_until_complete(self.cache.set(cache_key, result, self.ttl))
                    
                    return result
                finally:
                    loop.close()
            
            return sync_wrapper


class CacheConfig:
    """Configuration for caching"""
    
    def __init__(
        self,
        enabled: bool = True,
        backend: str = "memory",
        ttl: Optional[int] = 3600,
        max_size: int = 1000,
    ):
        """Initialize cache configuration
        
        Args:
            enabled: Enable caching
            backend: Cache backend ("memory", "none")
            ttl: Default time to live in seconds
            max_size: Maximum cache size
        """
        self.enabled = enabled
        self.backend = backend
        self.ttl = ttl
        self.max_size = max_size


def create_cache(config: CacheConfig) -> BaseCache:
    """Create cache instance based on configuration
    
    Args:
        config: Cache configuration
        
    Returns:
        Cache instance
    """
    if not config.enabled:
        return NoCache()
    
    if config.backend == "memory":
        return MemoryCache(max_size=config.max_size)
    
    return NoCache()


# Global cache instance
_cache: Optional[BaseCache] = None


def get_cache(config: Optional[CacheConfig] = None) -> BaseCache:
    """Get global cache instance
    
    Args:
        config: Cache configuration
        
    Returns:
        Cache instance
    """
    global _cache
    
    if _cache is None:
        if config is None:
            config = CacheConfig()
        
        _cache = create_cache(config)
    
    return _cache
