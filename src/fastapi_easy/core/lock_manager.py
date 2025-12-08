"""Distributed lock manager for cache consistency and avalanche prevention"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Dict, Optional


class AsyncLock:
    """Async lock with timeout support"""

    def __init__(self, timeout: float = 5.0):
        """Initialize async lock

        Args:
            timeout: Lock timeout in seconds
        """
        self.lock = asyncio.Lock()
        self.timeout = timeout
        self.acquired_at: Optional[datetime] = None

    async def acquire(self) -> bool:
        """Acquire lock with timeout

        Returns:
            True if lock acquired, False if timeout
        """
        try:
            await asyncio.wait_for(self.lock.acquire(), timeout=self.timeout)
            self.acquired_at = datetime.now()
            return True
        except asyncio.TimeoutError:
            return False

    def release(self) -> None:
        """Release lock"""
        if self.lock.locked():
            self.lock.release()

    def is_locked(self) -> bool:
        """Check if lock is locked

        Returns:
            True if locked
        """
        return self.lock.locked()


class LockManager:
    """Manages distributed locks for cache consistency"""

    def __init__(self, default_timeout: float = 5.0):
        """Initialize lock manager

        Args:
            default_timeout: Default lock timeout in seconds
        """
        self.locks: Dict[str, AsyncLock] = {}
        self.default_timeout = default_timeout

    async def acquire(self, key: str, timeout: Optional[float] = None) -> bool:
        """Acquire lock for key

        Args:
            key: Lock key
            timeout: Lock timeout in seconds

        Returns:
            True if lock acquired, False if timeout
        """
        if key not in self.locks:
            self.locks[key] = AsyncLock(timeout or self.default_timeout)

        return await self.locks[key].acquire()

    def release(self, key: str) -> None:
        """Release lock for key

        Args:
            key: Lock key
        """
        if key in self.locks:
            self.locks[key].release()

    def is_locked(self, key: str) -> bool:
        """Check if key is locked

        Args:
            key: Lock key

        Returns:
            True if locked
        """
        if key not in self.locks:
            return False
        return self.locks[key].is_locked()

    async def cleanup(self) -> None:
        """Clean up expired locks"""
        # Remove locks that are not held
        keys_to_remove = [key for key, lock in self.locks.items() if not lock.is_locked()]
        for key in keys_to_remove:
            del self.locks[key]


def create_lock_manager(default_timeout: float = 5.0) -> LockManager:
    """Create a lock manager

    Args:
        default_timeout: Default lock timeout in seconds

    Returns:
        Lock manager instance
    """
    return LockManager(default_timeout)
