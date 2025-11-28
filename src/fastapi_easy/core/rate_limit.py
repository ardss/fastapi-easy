"""Rate limiting support for FastAPI-Easy"""

import asyncio
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta


class RateLimitEntry:
    """Rate limit entry with optimized time complexity"""
    
    def __init__(self, limit: int, window: int):
        """Initialize rate limit entry
        
        Args:
            limit: Maximum requests in window
            window: Time window in seconds
        """
        self.limit = limit
        self.window = window
        self.requests: deque = deque(maxlen=limit)  # 使用 deque 优化性能
    
    def is_allowed(self) -> bool:
        """Check if request is allowed (O(1) 时间复杂度)
        
        Returns:
            True if request is allowed
        """
        now = time.time()
        
        # 只检查最早的请求 - O(1) 而不是 O(n)
        while self.requests and now - self.requests[0] >= self.window:
            self.requests.popleft()
        
        # Check if limit exceeded
        if len(self.requests) >= self.limit:
            return False
        
        # Add new request
        self.requests.append(now)
        return True
    
    def get_remaining(self) -> int:
        """Get remaining requests
        
        Returns:
            Number of remaining requests
        """
        now = time.time()
        
        # 清理过期请求
        while self.requests and now - self.requests[0] >= self.window:
            self.requests.popleft()
        
        return max(0, self.limit - len(self.requests))
    
    def get_reset_time(self) -> float:
        """Get reset time
        
        Returns:
            Seconds until reset
        """
        if not self.requests:
            return 0
        
        oldest_request = self.requests[0]  # deque 的第一个元素
        reset_time = oldest_request + self.window
        now = time.time()
        
        return max(0, reset_time - now)


class BaseRateLimiter(ABC):
    """Base rate limiter class"""
    
    @abstractmethod
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed
        
        Args:
            key: Rate limit key (e.g., user_id, IP address)
            limit: Maximum requests in window
            window: Time window in seconds
            
        Returns:
            True if request is allowed
        """
        pass
    
    @abstractmethod
    async def get_remaining(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests
        
        Args:
            key: Rate limit key
            limit: Maximum requests in window
            window: Time window in seconds
            
        Returns:
            Number of remaining requests
        """
        pass
    
    @abstractmethod
    async def get_reset_time(self, key: str, limit: int, window: int) -> float:
        """Get reset time
        
        Args:
            key: Rate limit key
            limit: Maximum requests in window
            window: Time window in seconds
            
        Returns:
            Seconds until reset
        """
        pass


class MemoryRateLimiter(BaseRateLimiter):
    """In-memory rate limiter"""
    
    def __init__(self):
        """Initialize memory rate limiter"""
        self.limiters: Dict[str, RateLimitEntry] = {}
        self._lock = asyncio.Lock()  # 线程安全保护
    
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed
        
        Args:
            key: Rate limit key
            limit: Maximum requests in window
            window: Time window in seconds
            
        Returns:
            True if request is allowed
        """
        limiter_key = f"{key}:{limit}:{window}"
        
        async with self._lock:
            if limiter_key not in self.limiters:
                self.limiters[limiter_key] = RateLimitEntry(limit, window)
            
            return self.limiters[limiter_key].is_allowed()
    
    async def get_remaining(self, key: str, limit: int, window: int) -> int:
        """Get remaining requests
        
        Args:
            key: Rate limit key
            limit: Maximum requests in window
            window: Time window in seconds
            
        Returns:
            Number of remaining requests
        """
        limiter_key = f"{key}:{limit}:{window}"
        
        async with self._lock:
            if limiter_key not in self.limiters:
                return limit
            
            return self.limiters[limiter_key].get_remaining()
    
    async def get_reset_time(self, key: str, limit: int, window: int) -> float:
        """Get reset time
        
        Args:
            key: Rate limit key
            limit: Maximum requests in window
            window: Time window in seconds
            
        Returns:
            Seconds until reset
        """
        limiter_key = f"{key}:{limit}:{window}"
        
        async with self._lock:
            if limiter_key not in self.limiters:
                return 0
            
            return self.limiters[limiter_key].get_reset_time()
    
    async def cleanup(self) -> int:
        """Clean up expired entries
        
        Returns:
            Number of entries removed
        """
        async with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self.limiters.items()
                if entry and now - max(entry.requests or [0]) > entry.window
            ]
            for key in expired_keys:
                del self.limiters[key]
            return len(expired_keys)


class NoRateLimiter(BaseRateLimiter):
    """No-op rate limiter"""
    
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Always allow requests
        
        Args:
            key: Rate limit key
            limit: Maximum requests in window
            window: Time window in seconds
            
        Returns:
            True
        """
        return True
    
    async def get_remaining(self, key: str, limit: int, window: int) -> int:
        """Always return limit
        
        Args:
            key: Rate limit key
            limit: Maximum requests in window
            window: Time window in seconds
            
        Returns:
            limit
        """
        return limit
    
    async def get_reset_time(self, key: str, limit: int, window: int) -> float:
        """Always return 0
        
        Args:
            key: Rate limit key
            limit: Maximum requests in window
            window: Time window in seconds
            
        Returns:
            0
        """
        return 0


class RateLimitConfig:
    """Rate limit configuration"""
    
    def __init__(
        self,
        enabled: bool = True,
        backend: str = "memory",
        default_limit: int = 100,
        default_window: int = 60,
    ):
        """Initialize rate limit configuration
        
        Args:
            enabled: Enable rate limiting
            backend: Rate limiter backend ("memory", "none")
            default_limit: Default request limit
            default_window: Default time window in seconds
        """
        self.enabled = enabled
        self.backend = backend
        self.default_limit = default_limit
        self.default_window = default_window


def create_rate_limiter(config: RateLimitConfig) -> BaseRateLimiter:
    """Create rate limiter based on configuration
    
    Args:
        config: Rate limit configuration
        
    Returns:
        Rate limiter instance
    """
    if not config.enabled:
        return NoRateLimiter()
    
    if config.backend == "memory":
        return MemoryRateLimiter()
    
    return NoRateLimiter()


# Global rate limiter instance
_rate_limiter: Optional[BaseRateLimiter] = None


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> BaseRateLimiter:
    """Get global rate limiter instance
    
    Args:
        config: Rate limit configuration
        
    Returns:
        Rate limiter instance
    """
    global _rate_limiter
    
    if _rate_limiter is None:
        if config is None:
            config = RateLimitConfig()
        
        _rate_limiter = create_rate_limiter(config)
    
    return _rate_limiter
