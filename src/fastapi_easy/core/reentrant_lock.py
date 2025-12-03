"""Reentrant lock implementation for deadlock prevention

This module provides reentrant locks that allow the same task
to acquire the same lock multiple times without deadlock.
"""

import asyncio
from typing import Optional, Dict, Any
import logging


logger = logging.getLogger(__name__)


class ReentrantAsyncLock:
    """Reentrant async lock that prevents deadlock

    Allows the same task to acquire the lock multiple times.
    The lock is released only when all acquisitions are released.
    """

    def __init__(self):
        """Initialize reentrant lock"""
        self._lock = asyncio.Lock()
        self._owner: Optional[int] = None
        self._count = 0

    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """Acquire the lock

        Args:
            timeout: Timeout in seconds

        Returns:
            True if lock acquired, False if timeout
        """
        try:
            # Safely get current task
            current_task = asyncio.current_task()
            if current_task is None:
                logger.error("No current task available")
                return False

            current_task_id = id(current_task)

            # If already owned by current task, increment count
            if self._owner == current_task_id:
                self._count += 1
                return True

            # Try to acquire lock
            if timeout:
                await asyncio.wait_for(self._lock.acquire(), timeout=timeout)
            else:
                await self._lock.acquire()

            # Set owner and count
            self._owner = current_task_id
            self._count = 1
            return True
        except asyncio.TimeoutError:
            logger.warning("Lock acquisition timeout")
            return False
        except RuntimeError as e:
            logger.error(f"Runtime error acquiring lock: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error acquiring lock: {str(e)}")
            return False

    def release(self) -> bool:
        """Release the lock

        Returns:
            True if lock released, False if not owned
        """
        try:
            current_task = id(asyncio.current_task())

            # Check if owned by current task
            if self._owner != current_task:
                logger.warning("Attempted to release lock not owned by current task")
                return False

            # Decrement count
            self._count -= 1

            # If count reaches 0, release lock
            if self._count == 0:
                self._owner = None
                self._lock.release()

            return True
        except Exception as e:
            logger.error(f"Error releasing lock: {str(e)}")
            return False

    async def __aenter__(self):
        """Async context manager entry"""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.release()

    def is_locked(self) -> bool:
        """Check if lock is currently held

        Returns:
            True if lock is held
        """
        return self._owner is not None

    def get_owner(self) -> Optional[int]:
        """Get current lock owner

        Returns:
            Owner task ID or None
        """
        return self._owner


class ReentrantLockManager:
    """Manage reentrant locks for multiple keys"""

    def __init__(self, default_timeout: Optional[float] = 30.0):
        """Initialize lock manager

        Args:
            default_timeout: Default lock timeout in seconds
        """
        self.locks: Dict[str, ReentrantAsyncLock] = {}
        self.default_timeout = default_timeout
        self.stats = {
            "total_acquisitions": 0,
            "total_releases": 0,
            "timeouts": 0,
        }
        # Lock for cleanup operations to prevent race conditions
        self._cleanup_lock = asyncio.Lock()

    async def acquire(self, key: str, timeout: Optional[float] = None) -> bool:
        """Acquire lock for key

        Args:
            key: Lock key
            timeout: Timeout in seconds

        Returns:
            True if lock acquired
        """
        if key not in self.locks:
            self.locks[key] = ReentrantAsyncLock()

        timeout = timeout or self.default_timeout
        acquired = await self.locks[key].acquire(timeout=timeout)

        if acquired:
            self.stats["total_acquisitions"] += 1
        else:
            self.stats["timeouts"] += 1

        return acquired

    def release(self, key: str) -> bool:
        """Release lock for key

        Args:
            key: Lock key

        Returns:
            True if lock released
        """
        if key not in self.locks:
            logger.warning(f"Attempted to release non-existent lock: {key}")
            return False

        released = self.locks[key].release()

        if released:
            self.stats["total_releases"] += 1

        return released

    async def cleanup(self, max_age: float = 3600.0) -> int:
        """Clean up unused locks with race condition protection

        Args:
            max_age: Maximum age of unused locks in seconds

        Returns:
            Number of locks cleaned up
        """
        async with self._cleanup_lock:
            import time

            current_time = time.time()
            keys_to_remove = []

            # Safely iterate over locks
            for key, lock in list(self.locks.items()):
                # Remove locks that are not held
                if not lock.is_locked():
                    keys_to_remove.append(key)

            # Remove keys safely
            for key in keys_to_remove:
                self.locks.pop(key, None)

            logger.debug(f"Cleaned up {len(keys_to_remove)} unused locks")
            return len(keys_to_remove)

    def get_stats(self) -> Dict[str, Any]:
        """Get lock manager statistics

        Returns:
            Statistics dictionary
        """
        return {
            **self.stats,
            "active_locks": len(self.locks),
            "held_locks": sum(1 for lock in self.locks.values() if lock.is_locked()),
        }


# Singleton instance
_manager = ReentrantLockManager()


def get_lock_manager() -> ReentrantLockManager:
    """Get lock manager instance

    Returns:
        ReentrantLockManager instance
    """
    return _manager
