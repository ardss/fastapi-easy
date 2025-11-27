"""Rate limiting support for FastAPI-Easy"""

from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
import time
from collections import defaultdict
from datetime import datetime, timedelta


class RateLimitEntry:
    """Rate limit entry"""
    
    def __init__(self, limit: int, window: int):
        """Initialize rate limit entry
        
        Args:
            limit: Maximum requests in window
            window: Time window in seconds
        """
        self.limit = limit
        self.window = window
        self.requests: list[float] = []
    
    def is_allowed(self) -> bool:
        """Check if request is allowed
        
        Returns:
            True if request is allowed
        """
        now = time.time()
        
        # Remove old requests outside window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.window]
        
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
        self.requests = [req_time for req_time in self.requests if now - req_time < self.window]
        return max(0, self.limit - len(self.requests))
    
    def get_reset_time(self) -> float:
        """Get reset time
        
        Returns:
            Seconds until reset
        """
        if not self.requests:
            return 0
        
        oldest_request = min(self.requests)
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
        self.limiters: Dict[str, RateLimitEntry] = defaultdict(lambda: None)
    
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
        
        if limiter_key not in self.limiters or self.limiters[limiter_key] is None:
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
        
        if limiter_key not in self.limiters or self.limiters[limiter_key] is None:
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
        
        if limiter_key not in self.limiters or self.limiters[limiter_key] is None:
            return 0
        
        return self.limiters[limiter_key].get_reset_time()


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
