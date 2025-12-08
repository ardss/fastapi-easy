"""Connection pool manager for preventing async interface freezing and socket leaks"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional, AsyncGenerator, Callable, Awaitable
from contextlib import asynccontextmanager
from functools import wraps
import weakref
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConnectionConfig:
    """Configuration for connection management"""
    max_connections: int = 100
    connection_timeout: float = 30.0
    idle_timeout: float = 300.0  # 5 minutes
    max_lifetime: float = 3600.0  # 1 hour
    health_check_interval: float = 60.0
    retry_attempts: int = 3
    retry_delay: float = 1.0


@dataclass
class ConnectionInfo:
    """Information about a managed connection"""
    connection: Any
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    is_active: bool = True
    usage_count: int = 0
    task_id: Optional[str] = None


class ConnectionManager:
    """
    Manages database connections to prevent resource leaks and interface freezing.

    Features:
    - Connection pooling with proper cleanup
    - Automatic health checks
    - Connection timeout and retry logic
    - Leak detection and prevention
    - Graceful shutdown
    """

    def __init__(self, config: Optional[ConnectionConfig] = None):
        self.config = config or ConnectionConfig()
        self._connections: Dict[str, ConnectionInfo] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._connection_factory: Optional[Callable] = None
        self._lock = asyncio.Lock()

    def set_connection_factory(self, factory: Callable[[], Awaitable[Any]]):
        """Set the factory function for creating new connections"""
        self._connection_factory = factory

    async def get_connection(self, connection_id: Optional[str] = None) -> Any:
        """
        Get a connection from the pool or create a new one

        Args:
            connection_id: Optional identifier for the connection

        Returns:
            Connection object

        Raises:
            RuntimeError: If no connection factory is set
            asyncio.TimeoutError: If connection timeout is exceeded
        """
        if not self._connection_factory:
            raise RuntimeError("No connection factory set. Call set_connection_factory() first.")

        if connection_id is None:
            connection_id = f"conn_{int(time.time() * 1000000)}"

        async with self._lock:
            # Check if connection exists and is healthy
            if connection_id in self._connections:
                conn_info = self._connections[connection_id]
                if conn_info.is_active and self._is_connection_healthy(conn_info.connection):
                    conn_info.last_used = time.time()
                    conn_info.usage_count += 1
                    logger.debug(f"Reusing connection {connection_id}")
                    return conn_info.connection
                else:
                    # Remove stale connection
                    await self._close_connection(connection_id)

            # Create new connection with retry logic
            connection = await self._create_connection_with_retry()
            self._connections[connection_id] = ConnectionInfo(
                connection=connection,
                task_id=asyncio.current_task().get_name() if asyncio.current_task() else None
            )

            logger.debug(f"Created new connection {connection_id}")
            return connection

    async def _create_connection_with_retry(self) -> Any:
        """Create connection with retry logic"""
        for attempt in range(self.config.retry_attempts):
            try:
                conn = await asyncio.wait_for(
                    self._connection_factory(),
                    timeout=self.config.connection_timeout
                )
                return conn
            except Exception as e:
                if attempt == self.config.retry_attempts - 1:
                    logger.error(f"Failed to create connection after {self.config.retry_attempts} attempts: {e}")
                    raise
                logger.warning(f"Connection attempt {attempt + 1} failed, retrying in {self.config.retry_delay}s: {e}")
                await asyncio.sleep(self.config.retry_delay)

    def _is_connection_healthy(self, connection: Any) -> bool:
        """Check if connection is healthy"""
        try:
            # This is a basic health check - customize based on your database/library
            if hasattr(connection, 'closed') and connection.closed:
                return False
            if hasattr(connection, 'is_connected') and not connection.is_connected():
                return False
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    async def release_connection(self, connection_id: str):
        """Release a connection back to the pool"""
        async with self._lock:
            if connection_id in self._connections:
                conn_info = self._connections[connection_id]
                conn_info.last_used = time.time()
                logger.debug(f"Released connection {connection_id}")

    async def close_connection(self, connection_id: str):
        """Close and remove a specific connection"""
        async with self._lock:
            await self._close_connection(connection_id)

    async def _close_connection(self, connection_id: str):
        """Internal method to close connection"""
        if connection_id not in self._connections:
            return

        conn_info = self._connections.pop(connection_id)
        try:
            if hasattr(conn_info.connection, 'close'):
                if asyncio.iscoroutinefunction(conn_info.connection.close):
                    await conn_info.connection.close()
                else:
                    conn_info.connection.close()
            elif hasattr(conn_info.connection, 'disconnect'):
                if asyncio.iscoroutinefunction(conn_info.connection.disconnect):
                    await conn_info.connection.disconnect()
                else:
                    conn_info.connection.disconnect()
            logger.debug(f"Closed connection {connection_id}")
        except Exception as e:
            logger.error(f"Error closing connection {connection_id}: {e}")

    async def start_cleanup_task(self):
        """Start the background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started connection cleanup task")

    async def stop_cleanup_task(self):
        """Stop the background cleanup task"""
        self._shutdown_event.set()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped connection cleanup task")

    async def _cleanup_loop(self):
        """Background task to cleanup idle connections"""
        while not self._shutdown_event.is_set():
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self._cleanup_idle_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _cleanup_idle_connections(self):
        """Clean up idle and expired connections"""
        current_time = time.time()
        connections_to_close = []

        async with self._lock:
            for connection_id, conn_info in self._connections.items():
                # Check for idle timeout
                if current_time - conn_info.last_used > self.config.idle_timeout:
                    connections_to_close.append(connection_id)
                    continue

                # Check for maximum lifetime
                if current_time - conn_info.created_at > self.config.max_lifetime:
                    connections_to_close.append(connection_id)
                    continue

                # Check connection health
                if not self._is_connection_healthy(conn_info.connection):
                    connections_to_close.append(connection_id)

        # Close connections outside of lock
        for connection_id in connections_to_close:
            await self._close_connection(connection_id)
            logger.debug(f"Cleaned up connection {connection_id}")

    async def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        async with self._lock:
            stats = {
                "total_connections": len(self._connections),
                "active_connections": sum(1 for c in self._connections.values() if c.is_active),
                "total_usage": sum(c.usage_count for c in self._connections.values()),
                "oldest_connection": min((c.created_at for c in self._connections.values()), default=0),
                "newest_connection": max((c.created_at for c in self._connections.values()), default=0),
            }
        return stats

    async def shutdown(self):
        """Gracefully shutdown all connections"""
        logger.info("Shutting down connection manager")
        await self.stop_cleanup_task()

        async with self._lock:
            connection_ids = list(self._connections.keys())

        for connection_id in connection_ids:
            await self._close_connection(connection_id)

        logger.info("Connection manager shutdown complete")


# Global connection manager instance
_global_manager: Optional[ConnectionManager] = None


def get_connection_manager(config: Optional[ConnectionConfig] = None) -> ConnectionManager:
    """Get or create the global connection manager"""
    global _global_manager
    if _global_manager is None:
        _global_manager = ConnectionManager(config)
    return _global_manager


@asynccontextmanager
async def managed_connection(
    connection_id: Optional[str] = None,
    manager: Optional[ConnectionManager] = None
) -> AsyncGenerator[Any, None]:
    """
    Context manager for managing connections with automatic cleanup

    Usage:
        async with managed_connection("my_conn") as conn:
            result = await conn.fetch("SELECT * FROM table")
    """
    if manager is None:
        manager = get_connection_manager()

    conn = None
    try:
        conn = await manager.get_connection(connection_id)
        yield conn
    finally:
        if connection_id and manager:
            await manager.release_connection(connection_id)
        elif conn and hasattr(conn, 'close'):
            # Fallback cleanup
            try:
                if asyncio.iscoroutinefunction(conn.close):
                    await conn.close()
                else:
                    conn.close()
            except Exception as e:
                logger.error(f"Error in fallback connection cleanup: {e}")


def with_connection_manager(
    connection_factory: Callable[[], Awaitable[Any]],
    config: Optional[ConnectionConfig] = None
):
    """
    Decorator to add connection management to FastAPI dependencies

    Usage:
        @with_connection_manager(create_db_connection)
        async def get_database():
            # Connection automatically managed
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            manager = get_connection_manager(config)
            manager.set_connection_factory(connection_factory)

            # Start cleanup task if not already running
            await manager.start_cleanup_task()

            try:
                return await func(*args, **kwargs, connection_manager=manager)
            finally:
                # Cleanup on request completion
                pass  # Let the background task handle cleanup

        return wrapper
    return decorator


# Example usage
if __name__ == "__main__":
    async def example_connection_factory():
        """Example connection factory"""
        import asyncpg
        return await asyncpg.connect("postgresql://user:pass@localhost/db")

    async def main():
        # Create manager
        manager = ConnectionManager()
        manager.set_connection_factory(example_connection_factory)
        await manager.start_cleanup_task()

        try:
            # Use managed connection
            async with managed_connection("example") as conn:
                result = await conn.fetch("SELECT 1")
                print(result)

            # Get stats
            stats = await manager.get_stats()
            print(f"Connection stats: {stats}")

        finally:
            await manager.shutdown()

    if __name__ == "__main__":
        asyncio.run(main())