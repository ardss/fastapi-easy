"""Tests for reentrant locks"""

import pytest
import asyncio
from fastapi_easy.core.reentrant_lock import (
    ReentrantAsyncLock,
    ReentrantLockManager,
    get_lock_manager,
)


class TestReentrantAsyncLock:
    """Test reentrant async lock"""
    
    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        """Test basic acquire and release"""
        lock = ReentrantAsyncLock()
        
        acquired = await lock.acquire()
        assert acquired is True
        
        released = lock.release()
        assert released is True
    
    @pytest.mark.asyncio
    async def test_reentrant_acquire(self):
        """Test reentrant acquisition"""
        lock = ReentrantAsyncLock()
        
        # Acquire twice
        acquired1 = await lock.acquire()
        acquired2 = await lock.acquire()
        
        assert acquired1 is True
        assert acquired2 is True
        
        # Release twice
        released1 = lock.release()
        released2 = lock.release()
        
        assert released1 is True
        assert released2 is True
    
    @pytest.mark.asyncio
    async def test_reentrant_no_timeout(self):
        """Test that reentrant acquire doesn't timeout"""
        lock = ReentrantAsyncLock()
        
        # Acquire lock
        await lock.acquire()
        
        # Reentrant acquire should succeed immediately
        result = await lock.acquire(timeout=0.1)
        assert result is True
        
        # Release twice
        lock.release()
        lock.release()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test context manager"""
        lock = ReentrantAsyncLock()
        
        async with lock:
            assert lock.is_locked()
        
        assert not lock.is_locked()
    
    def test_is_locked(self):
        """Test is_locked check"""
        lock = ReentrantAsyncLock()
        
        assert not lock.is_locked()
    
    @pytest.mark.asyncio
    async def test_get_owner(self):
        """Test getting lock owner"""
        lock = ReentrantAsyncLock()
        
        assert lock.get_owner() is None
        
        await lock.acquire()
        assert lock.get_owner() is not None
        
        lock.release()
        assert lock.get_owner() is None


class TestReentrantLockManager:
    """Test reentrant lock manager"""
    
    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        """Test acquire and release"""
        manager = ReentrantLockManager()
        
        acquired = await manager.acquire("key1")
        assert acquired is True
        
        released = manager.release("key1")
        assert released is True
    
    @pytest.mark.asyncio
    async def test_multiple_keys(self):
        """Test multiple keys"""
        manager = ReentrantLockManager()
        
        acquired1 = await manager.acquire("key1")
        acquired2 = await manager.acquire("key2")
        
        assert acquired1 is True
        assert acquired2 is True
        
        released1 = manager.release("key1")
        released2 = manager.release("key2")
        
        assert released1 is True
        assert released2 is True
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup"""
        manager = ReentrantLockManager()
        
        # Create some locks
        await manager.acquire("key1")
        await manager.acquire("key2")
        
        # Release them
        manager.release("key1")
        manager.release("key2")
        
        # Cleanup
        cleaned = await manager.cleanup()
        
        assert cleaned >= 0
    
    def test_get_stats(self):
        """Test getting statistics"""
        manager = ReentrantLockManager()
        
        stats = manager.get_stats()
        
        assert "total_acquisitions" in stats
        assert "total_releases" in stats
        assert "timeouts" in stats
        assert "active_locks" in stats
        assert "held_locks" in stats
    
    @pytest.mark.asyncio
    async def test_reentrant_acquire_tracking(self):
        """Test reentrant acquire tracking"""
        manager = ReentrantLockManager()
        
        # Acquire lock
        acquired1 = await manager.acquire("key1")
        assert acquired1 is True
        
        # Reentrant acquire should succeed
        acquired2 = await manager.acquire("key1")
        assert acquired2 is True
        
        # Release twice
        released1 = manager.release("key1")
        released2 = manager.release("key1")
        
        assert released1 is True
        assert released2 is True


class TestLockManagerSingleton:
    """Test lock manager singleton"""
    
    def test_get_manager(self):
        """Test getting manager instance"""
        manager1 = get_lock_manager()
        manager2 = get_lock_manager()
        
        assert manager1 is manager2


class TestDeadlockPrevention:
    """Test deadlock prevention"""
    
    @pytest.mark.asyncio
    async def test_no_deadlock_with_reentrant(self):
        """Test that reentrant lock prevents deadlock"""
        lock = ReentrantAsyncLock()
        
        async def recursive_acquire(depth):
            if depth == 0:
                return True
            
            acquired = await lock.acquire()
            if not acquired:
                return False
            
            result = await recursive_acquire(depth - 1)
            
            lock.release()
            return result
        
        # Should not deadlock
        result = await asyncio.wait_for(recursive_acquire(5), timeout=5.0)
        assert result is True
