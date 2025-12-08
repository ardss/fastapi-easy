"""Optimized distributed lock mechanism with improved performance"""

import asyncio
import logging
import os
import time
import weakref
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)


@dataclass
class LockConfig:
    """Configuration for lock performance optimization"""

    max_retries: int = 10
    base_retry_delay: float = 0.01  # Start with 10ms
    max_retry_delay: float = 1.0
    connection_timeout: float = 5.0
    lock_timeout: int = 30
    cleanup_interval: int = 60  # seconds

    def get_retry_delay(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter"""
        delay = min(self.base_retry_delay * (2**attempt), self.max_retry_delay)
        # Add jitter to prevent thundering herd
        jitter = delay * 0.1 * (0.5 - (hash(attempt) % 100) / 100)
        return delay + jitter


def is_test_environment() -> bool:
    """Optimized test environment detection"""
    return (
        "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "")
        or os.environ.get("TESTING") == "true"
        or "pytest" in sys.modules
    )


class OptimizedConnectionManager:
    """High-performance connection manager with proper resource cleanup"""

    def __init__(self, engine: Engine, config: LockConfig):
        """Initialize with performance optimization config"""
        self.engine = engine
        self.config = config
        self._connection_pool = asyncio.Queue(maxsize=10)
        self._pool_stats = {"created": 0, "reused": 0, "errors": 0, "timeouts": 0}

        # Register cleanup callback
        weakref.finalize(self, self._cleanup_resources)

    @asynccontextmanager
    async def get_connection(self, timeout: Optional[float] = None):
        """Get connection with timeout and pooling"""
        timeout = timeout or self.config.connection_timeout
        conn = None
        start_time = time.time()

        try:
            # Try to get from pool first
            try:
                conn = await asyncio.wait_for(
                    self._connection_pool.get(), timeout=min(timeout * 0.5, 2.0)
                )
                self._pool_stats["reused"] += 1
            except asyncio.TimeoutError:
                # Create new connection if pool is empty
                if hasattr(self.engine, "connect"):
                    conn = self.engine.connect()
                else:
                    # For async engines
                    async with self.engine.begin() as connection:
                        conn = connection
                self._pool_stats["created"] += 1

            # Test connection health
            if hasattr(conn, "execute"):
                await conn.execute(text("SELECT 1"))

            yield conn

        except asyncio.TimeoutError:
            self._pool_stats["timeouts"] += 1
            logger.error(f"Connection acquisition timeout after {timeout}s")
            raise
        except Exception as e:
            self._pool_stats["errors"] += 1
            logger.error(f"Connection error: {e}")
            raise
        finally:
            # Return connection to pool if healthy
            if conn:
                try:
                    # Quick health check
                    if time.time() - start_time < timeout:
                        await self._connection_pool.put(conn)
                    else:
                        conn.close()
                except Exception as e:
                    logger.warning(f"Error returning connection to pool: {e}")
                    try:
                        conn.close()
                    except:
                        pass

    def _cleanup_resources(self):
        """Cleanup all resources"""
        while not self._connection_pool.empty():
            try:
                conn = self._connection_pool.get_nowait()
                conn.close()
            except:
                break

    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return {
            **self._pool_stats,
            "pool_size": self._connection_pool.qsize(),
            "max_pool_size": self._connection_pool.maxsize,
        }


class OptimizedPostgresLockProvider:
    """High-performance PostgreSQL lock provider"""

    def __init__(self, engine: Engine, lock_id: int = 1, config: Optional[LockConfig] = None):
        self.engine = engine
        self.lock_id = lock_id
        self.config = config or LockConfig()
        self.connection_manager = OptimizedConnectionManager(engine, self.config)
        self._stats = {"acquired": 0, "failed": 0, "timeouts": 0, "avg_acquisition_time": 0.0}

    async def acquire(self, timeout: Optional[int] = None) -> bool:
        """Optimized lock acquisition with exponential backoff"""
        timeout = timeout or self.config.lock_timeout
        start_time = time.time()

        async with self.connection_manager.get_connection(timeout) as conn:
            for attempt in range(self.config.max_retries):
                try:
                    # Use advisory lock with timeout
                    result = await conn.execute(
                        text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": self.lock_id}
                    )
                    locked = result.scalar()

                    if locked:
                        acquisition_time = time.time() - start_time
                        self._stats["acquired"] += 1
                        self._update_avg_time(acquisition_time)
                        logger.debug(f"Lock acquired in {acquisition_time:.3f}s")
                        return True

                    # Check timeout
                    if time.time() - start_time > timeout:
                        self._stats["timeouts"] += 1
                        break

                    # Exponential backoff with jitter
                    delay = self.config.get_retry_delay(attempt)
                    await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"Lock acquisition error: {e}")
                    self._stats["failed"] += 1
                    if attempt == self.config.max_retries - 1:
                        raise

            self._stats["failed"] += 1
            return False

    async def release(self) -> bool:
        """Release lock with proper cleanup"""
        try:
            async with self.connection_manager.get_connection() as conn:
                result = await conn.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": self.lock_id}
                )
                released = result.scalar()
                return bool(released)
        except Exception as e:
            logger.error(f"Lock release error: {e}")
            return False

    def _update_avg_time(self, new_time: float):
        """Update running average of acquisition time"""
        total = self._stats["acquired"]
        if total == 1:
            self._stats["avg_acquisition_time"] = new_time
        else:
            # Exponential moving average
            alpha = 0.1
            self._stats["avg_acquisition_time"] = (
                alpha * new_time + (1 - alpha) * self._stats["avg_acquisition_time"]
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get lock performance statistics"""
        return {
            **self._stats,
            "connection_stats": self.connection_manager.get_stats(),
            "success_rate": (
                self._stats["acquired"] / max(1, self._stats["acquired"] + self._stats["failed"])
            )
            * 100,
        }


class OptimizedFileLockProvider:
    """High-performance file lock with memory mapping"""

    def __init__(self, lock_file: Optional[str] = None, config: Optional[LockConfig] = None):
        self.lock_file = lock_file or ".fastapi_easy_migration.lock"
        self.config = config or LockConfig()
        self._acquired = False
        self._lock_fd = None
        self._stats = {"acquired": 0, "failed": 0, "contentions": 0}

    async def acquire(self, timeout: Optional[int] = None) -> bool:
        """Optimized file lock with memory mapping"""
        timeout = timeout or self.config.lock_timeout
        start_time = time.time()

        # Try memory-mapped lock first (faster)
        try:
            import mmap
            import fcntl

            fd = os.open(self.lock_file, os.O_CREAT | os.O_RDWR, 0o644)

            # Set lock with timeout
            for attempt in range(self.config.max_retries):
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self._lock_fd = fd
                    self._acquired = True

                    # Write lock info
                    lock_data = f"{os.getpid()}:{time.time()}"
                    os.write(fd, lock_data.encode())

                    self._stats["acquired"] += 1
                    return True

                except BlockingIOError:
                    self._stats["contentions"] += 1

                    if time.time() - start_time > timeout:
                        break

                    delay = self.config.get_retry_delay(attempt)
                    await asyncio.sleep(delay)

        except ImportError:
            # Fallback to simple file-based lock
            return await self._fallback_acquire(timeout)

        self._stats["failed"] += 1
        return False

    async def _fallback_acquire(self, timeout: int) -> bool:
        """Fallback file lock implementation"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                self._lock_fd = fd
                self._acquired = True

                lock_data = f"{os.getpid()}:{time.time()}"
                os.write(fd, lock_data.encode())
                os.close(fd)

                self._stats["acquired"] += 1
                return True

            except FileExistsError:
                # Check if lock is stale
                if await self._is_lock_stale():
                    try:
                        os.remove(self.lock_file)
                    except OSError:
                        pass
                    continue

                delay = self.config.base_retry_delay
                await asyncio.sleep(delay)

        self._stats["failed"] += 1
        return False

    async def _is_lock_stale(self) -> bool:
        """Check if lock file is stale"""
        try:
            stat = os.stat(self.lock_file)
            age = time.time() - stat.st_mtime
            return age > (self.config.lock_timeout * 2)
        except OSError:
            return True

    async def release(self) -> bool:
        """Release file lock"""
        if not self._acquired:
            return False

        try:
            if self._lock_fd is not None:
                import fcntl

                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
            else:
                os.remove(self.lock_file)

            self._acquired = False
            return True
        except Exception as e:
            logger.error(f"File lock release error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get file lock statistics"""
        return {**self._stats, "acquired": self._acquired}


def get_optimized_lock_provider(engine: Engine, lock_file: Optional[str] = None) -> Any:
    """Get optimized lock provider based on database type"""
    dialect = engine.dialect.name.lower()

    if "postgresql" in dialect:
        return OptimizedPostgresLockProvider(engine)
    elif "mysql" in dialect:
        # TODO: Implement optimized MySQL provider
        pass
    else:
        return OptimizedFileLockProvider(lock_file)
