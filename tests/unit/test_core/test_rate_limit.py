"""Unit tests for rate limiting"""

import pytest
import asyncio
from fastapi_easy.core.rate_limit import (
    RateLimitEntry,
    MemoryRateLimiter,
    NoRateLimiter,
    RateLimitConfig,
    create_rate_limiter,
    get_rate_limiter,
)


class TestRateLimitEntry:
    """Test RateLimitEntry"""
    
    def test_entry_initialization(self):
        """Test entry initialization"""
        entry = RateLimitEntry(limit=10, window=60)
        
        assert entry.limit == 10
        assert entry.window == 60
        assert entry.requests == []
    
    def test_is_allowed_within_limit(self):
        """Test request allowed within limit"""
        entry = RateLimitEntry(limit=3, window=60)
        
        assert entry.is_allowed() is True
        assert entry.is_allowed() is True
        assert entry.is_allowed() is True
    
    def test_is_allowed_exceeds_limit(self):
        """Test request denied when limit exceeded"""
        entry = RateLimitEntry(limit=2, window=60)
        
        assert entry.is_allowed() is True
        assert entry.is_allowed() is True
        assert entry.is_allowed() is False
    
    def test_get_remaining(self):
        """Test getting remaining requests"""
        entry = RateLimitEntry(limit=5, window=60)
        
        entry.is_allowed()
        entry.is_allowed()
        
        remaining = entry.get_remaining()
        
        assert remaining == 3
    
    def test_get_reset_time(self):
        """Test getting reset time"""
        entry = RateLimitEntry(limit=1, window=1)
        
        entry.is_allowed()
        reset_time = entry.get_reset_time()
        
        assert reset_time > 0
        assert reset_time <= 1


class TestMemoryRateLimiter:
    """Test MemoryRateLimiter"""
    
    @pytest.mark.asyncio
    async def test_is_allowed_within_limit(self):
        """Test request allowed within limit"""
        limiter = MemoryRateLimiter()
        
        assert await limiter.is_allowed("user1", 3, 60) is True
        assert await limiter.is_allowed("user1", 3, 60) is True
        assert await limiter.is_allowed("user1", 3, 60) is True
    
    @pytest.mark.asyncio
    async def test_is_allowed_exceeds_limit(self):
        """Test request denied when limit exceeded"""
        limiter = MemoryRateLimiter()
        
        assert await limiter.is_allowed("user1", 2, 60) is True
        assert await limiter.is_allowed("user1", 2, 60) is True
        assert await limiter.is_allowed("user1", 2, 60) is False
    
    @pytest.mark.asyncio
    async def test_different_keys(self):
        """Test different keys have separate limits"""
        limiter = MemoryRateLimiter()
        
        assert await limiter.is_allowed("user1", 1, 60) is True
        assert await limiter.is_allowed("user1", 1, 60) is False
        
        assert await limiter.is_allowed("user2", 1, 60) is True
        assert await limiter.is_allowed("user2", 1, 60) is False
    
    @pytest.mark.asyncio
    async def test_get_remaining(self):
        """Test getting remaining requests"""
        limiter = MemoryRateLimiter()
        
        await limiter.is_allowed("user1", 5, 60)
        await limiter.is_allowed("user1", 5, 60)
        
        remaining = await limiter.get_remaining("user1", 5, 60)
        
        assert remaining == 3
    
    @pytest.mark.asyncio
    async def test_get_reset_time(self):
        """Test getting reset time"""
        limiter = MemoryRateLimiter()
        
        await limiter.is_allowed("user1", 1, 1)
        reset_time = await limiter.get_reset_time("user1", 1, 1)
        
        assert reset_time > 0
        assert reset_time <= 1
    
    @pytest.mark.asyncio
    async def test_window_expiration(self):
        """Test window expiration"""
        limiter = MemoryRateLimiter()
        
        assert await limiter.is_allowed("user1", 1, 1) is True
        assert await limiter.is_allowed("user1", 1, 1) is False
        
        # Wait for window to expire
        await asyncio.sleep(1.1)
        
        assert await limiter.is_allowed("user1", 1, 1) is True


class TestNoRateLimiter:
    """Test NoRateLimiter"""
    
    @pytest.mark.asyncio
    async def test_always_allowed(self):
        """Test always allows requests"""
        limiter = NoRateLimiter()
        
        for _ in range(100):
            assert await limiter.is_allowed("user1", 1, 60) is True
    
    @pytest.mark.asyncio
    async def test_always_returns_limit(self):
        """Test always returns limit as remaining"""
        limiter = NoRateLimiter()
        
        remaining = await limiter.get_remaining("user1", 10, 60)
        
        assert remaining == 10
    
    @pytest.mark.asyncio
    async def test_always_returns_zero_reset(self):
        """Test always returns 0 for reset time"""
        limiter = NoRateLimiter()
        
        reset_time = await limiter.get_reset_time("user1", 10, 60)
        
        assert reset_time == 0


class TestRateLimitConfig:
    """Test RateLimitConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = RateLimitConfig()
        
        assert config.enabled is True
        assert config.backend == "memory"
        assert config.default_limit == 100
        assert config.default_window == 60
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = RateLimitConfig(
            enabled=False,
            backend="redis",
            default_limit=50,
            default_window=30,
        )
        
        assert config.enabled is False
        assert config.backend == "redis"
        assert config.default_limit == 50
        assert config.default_window == 30


class TestCreateRateLimiter:
    """Test create_rate_limiter function"""
    
    def test_create_memory_limiter(self):
        """Test creating memory rate limiter"""
        config = RateLimitConfig(backend="memory")
        limiter = create_rate_limiter(config)
        
        assert isinstance(limiter, MemoryRateLimiter)
    
    def test_create_no_limiter(self):
        """Test creating no-op limiter when disabled"""
        config = RateLimitConfig(enabled=False)
        limiter = create_rate_limiter(config)
        
        assert isinstance(limiter, NoRateLimiter)


class TestGlobalRateLimiter:
    """Test global rate limiter"""
    
    def test_get_global_limiter(self):
        """Test getting global rate limiter"""
        limiter = get_rate_limiter()
        
        assert limiter is not None
        assert isinstance(limiter, MemoryRateLimiter)
    
    def test_global_limiter_singleton(self):
        """Test global rate limiter is singleton"""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        
        assert limiter1 is limiter2
