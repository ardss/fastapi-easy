"""Tests for lock manager"""

import pytest
import asyncio
from fastapi_easy.core.lock_manager import LockManager, create_lock_manager


class TestLockManager:
    """Test LockManager class"""

    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        """Test acquiring and releasing lock"""
        manager = LockManager()

        # Acquire lock
        acquired = await manager.acquire("key1")
        assert acquired is True
        assert manager.is_locked("key1")

        # Release lock
        manager.release("key1")
        assert not manager.is_locked("key1")

    @pytest.mark.asyncio
    async def test_concurrent_lock(self):
        """Test concurrent lock acquisition"""
        manager = LockManager(default_timeout=0.1)

        results = []

        # First task acquires lock
        async def task1():
            acquired = await manager.acquire("key1")
            results.append(("task1_acquire", acquired))
            await asyncio.sleep(0.3)
            manager.release("key1")
            results.append(("task1_release", True))

        # Second task tries to acquire same lock
        async def task2():
            await asyncio.sleep(0.05)
            acquired = await manager.acquire("key1")
            results.append(("task2_acquire", acquired))

        await asyncio.gather(task1(), task2())

        # task1 should acquire, task2 should fail due to timeout
        assert ("task1_acquire", True) in results
        assert ("task2_acquire", False) in results

    @pytest.mark.asyncio
    async def test_multiple_keys(self):
        """Test multiple independent locks"""
        manager = LockManager()

        # Acquire locks for different keys
        acquired1 = await manager.acquire("key1")
        acquired2 = await manager.acquire("key2")

        assert acquired1 is True
        assert acquired2 is True
        assert manager.is_locked("key1")
        assert manager.is_locked("key2")

        # Release one lock
        manager.release("key1")
        assert not manager.is_locked("key1")
        assert manager.is_locked("key2")

    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test lock timeout"""
        manager = LockManager(default_timeout=0.1)

        # Acquire lock
        await manager.acquire("key1")

        # Try to acquire same lock (should timeout)
        acquired = await manager.acquire("key1")
        assert acquired is False

    def test_cleanup(self):
        """Test cleanup of released locks"""
        manager = LockManager()

        # Create some locks
        asyncio.run(manager.acquire("key1"))
        asyncio.run(manager.acquire("key2"))

        # Release them
        manager.release("key1")
        manager.release("key2")

        # Cleanup
        asyncio.run(manager.cleanup())

        # Locks should be removed
        assert "key1" not in manager.locks or not manager.is_locked("key1")


class TestFactoryFunction:
    """Test factory function"""

    def test_create_lock_manager(self):
        """Test creating lock manager"""
        manager = create_lock_manager(default_timeout=10.0)
        assert isinstance(manager, LockManager)
        assert manager.default_timeout == 10.0
