"""Multi-layer cache implementation for advanced performance optimization"""

from typing import Any, Optional
from .cache import QueryCache


class MultiLayerCache:
    """Two-layer cache architecture (L1 hot data, L2 cold data)"""
    
    def __init__(
        self,
        l1_size: int = 1000,
        l1_ttl: int = 60,
        l2_size: int = 10000,
        l2_ttl: int = 600,
    ):
        """Initialize multi-layer cache
        
        Args:
            l1_size: L1 cache max size (hot data)
            l1_ttl: L1 cache TTL in seconds (short)
            l2_size: L2 cache max size (cold data)
            l2_ttl: L2 cache TTL in seconds (long)
        """
        # L1: Hot data cache (short TTL)
        self.l1_cache = QueryCache(max_size=l1_size, default_ttl=l1_ttl)
        
        # L2: Cold data cache (long TTL)
        self.l2_cache = QueryCache(max_size=l2_size, default_ttl=l2_ttl)
        
        # Statistics
        self.l1_hits = 0
        self.l2_hits = 0
        self.misses = 0
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 first, then L2)
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        # Try L1 first (hot data)
        result = await self.l1_cache.get(key)
        if result is not None:
            self.l1_hits += 1
            return result
        
        # Try L2 (cold data)
        result = await self.l2_cache.get(key)
        if result is not None:
            self.l2_hits += 1
            # Promote to L1
            await self.l1_cache.set(key, result)
            return result
        
        # Cache miss
        self.misses += 1
        return None
    
    async def set(self, key: str, value: Any, tier: str = "l1") -> None:
        """Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            tier: Which tier to set ("l1" or "l2")
        """
        if tier == "l1":
            await self.l1_cache.set(key, value)
        elif tier == "l2":
            await self.l2_cache.set(key, value)
        else:
            # Default: set in both tiers
            await self.l1_cache.set(key, value)
            await self.l2_cache.set(key, value)
    
    async def delete(self, key: str) -> None:
        """Delete value from both caches
        
        Args:
            key: Cache key
        """
        await self.l1_cache.delete(key)
        await self.l2_cache.delete(key)
    
    async def clear(self) -> None:
        """Clear all caches"""
        await self.l1_cache.clear()
        await self.l2_cache.clear()
    
    async def cleanup_expired(self) -> int:
        """Clean up expired entries from both caches
        
        Returns:
            Total number of entries removed
        """
        l1_removed = await self.l1_cache.cleanup_expired()
        l2_removed = await self.l2_cache.cleanup_expired()
        return l1_removed + l2_removed
    
    def get_stats(self) -> dict:
        """Get cache statistics
        
        Returns:
            Statistics dictionary
        """
        total_requests = self.l1_hits + self.l2_hits + self.misses
        hit_rate = (
            (self.l1_hits + self.l2_hits) / total_requests * 100
            if total_requests > 0
            else 0
        )
        
        return {
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "misses": self.misses,
            "total_requests": total_requests,
            "hit_rate": f"{hit_rate:.1f}%",
            "l1_stats": self.l1_cache.get_stats(),
            "l2_stats": self.l2_cache.get_stats(),
        }


def create_multilayer_cache(
    l1_size: int = 1000,
    l1_ttl: int = 60,
    l2_size: int = 10000,
    l2_ttl: int = 600,
) -> MultiLayerCache:
    """Create a multi-layer cache instance
    
    Args:
        l1_size: L1 cache max size
        l1_ttl: L1 cache TTL in seconds
        l2_size: L2 cache max size
        l2_ttl: L2 cache TTL in seconds
        
    Returns:
        Multi-layer cache instance
    """
    return MultiLayerCache(l1_size, l1_ttl, l2_size, l2_ttl)
