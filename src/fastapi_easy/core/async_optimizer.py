"""
Async Performance Optimization Module

This module provides comprehensive async optimization features:
- Optimized async/await patterns
- Async context managers for resource management
- Batch operations for improved throughput
- Async semaphore and rate limiting
- Connection pooling for async operations
- Performance monitoring for async operations
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Deque,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    TypeVar,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class AsyncMetrics:
    """Metrics for async operations"""

    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_wait_time: float = 0.0
    avg_wait_time: float = 0.0
    peak_wait_time: float = 0.0
    concurrent_operations: int = 0
    max_concurrent: int = 0
    queue_overflows: int = 0
    timeouts: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        return (
            (self.successful_operations / self.total_operations * 100)
            if self.total_operations > 0
            else 0.0
        )

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage"""
        return (
            (self.failed_operations / self.total_operations * 100)
            if self.total_operations > 0
            else 0.0
        )


class AsyncSemaphore:
    """Optimized async semaphore with metrics and queue management"""

    def __init__(self, value: int = 1, max_queue_size: int = 0):
        self.value = value
        self.max_queue_size = max_queue_size
        self._waiters: Deque[asyncio.Future] = deque()
        self._lock = asyncio.Lock()
        self._current_value = value
        self._metrics = AsyncMetrics()

    @asynccontextmanager
    async def acquire(self, timeout: Optional[float] = None):
        """Acquire semaphore with timeout and metrics"""
        start_time = time.time()
        future = asyncio.Future()

        async with self._lock:
            if self._current_value > 0:
                self._current_value -= 1
                future.set_result(True)
                self._metrics.total_operations += 1
                self._metrics.successful_operations += 1
            else:
                if self.max_queue_size > 0 and len(self._waiters) >= self.max_queue_size:
                    self._metrics.queue_overflows += 1
                    raise asyncio.QueueFull("Semaphore queue is full")

                self._waiters.append(future)
                self._metrics.total_operations += 1

        try:
            # Wait for acquisition
            if timeout:
                await asyncio.wait_for(future, timeout)
            else:
                await future

            # Update metrics
            wait_time = time.time() - start_time
            self._metrics.total_wait_time += wait_time
            self._metrics.avg_wait_time = (
                self._metrics.total_wait_time / self._metrics.total_operations
            )
            if wait_time > self._metrics.peak_wait_time:
                self._metrics.peak_wait_time = wait_time

            # Track concurrent operations
            self._metrics.concurrent_operations += 1
            if self._metrics.concurrent_operations > self._metrics.max_concurrent:
                self._metrics.max_concurrent = self._metrics.concurrent_operations

            yield self

        except asyncio.TimeoutError:
            self._metrics.timeouts += 1
            self._metrics.failed_operations += 1

            # Remove from queue if still there
            async with self._lock:
                if future in self._waiters:
                    self._waiters.remove(future)
                    future.cancel()

            raise

        except Exception:
            self._metrics.failed_operations += 1
            raise

        finally:
            # Release semaphore
            async with self._lock:
                if future.done() and not future.cancelled():
                    self._metrics.concurrent_operations -= 1

                    # Wake next waiter
                    if self._waiters:
                        next_future = self._waiters.popleft()
                        if not next_future.done():
                            next_future.set_result(True)
                    else:
                        self._current_value += 1

    async def acquire_nowait(self) -> bool:
        """Try to acquire without waiting"""
        async with self._lock:
            if self._current_value > 0:
                self._current_value -= 1
                self._metrics.total_operations += 1
                self._metrics.successful_operations += 1
                self._metrics.concurrent_operations += 1
                return True
            return False

    async def release(self):
        """Release semaphore (for manual acquire/release)"""
        async with self._lock:
            if self._waiters:
                next_future = self._waiters.popleft()
                if not next_future.done():
                    next_future.set_result(True)
            else:
                if self._current_value < self.value:
                    self._current_value += 1

    def get_metrics(self) -> AsyncMetrics:
        """Get semaphore metrics"""
        return self._metrics


class AsyncRateLimiter:
    """Rate limiter for async operations"""

    def __init__(self, rate_limit: float, period: float = 1.0):
        """
        Initialize rate limiter

        Args:
            rate_limit: Maximum number of operations per period
            period: Time period in seconds
        """
        self.rate_limit = rate_limit
        self.period = period
        self.min_interval = period / rate_limit
        self._last_call = 0.0
        self._lock = asyncio.Lock()
        self._tokens = rate_limit
        self._last_refill = time.time()

    async def acquire(self):
        """Acquire permission to proceed"""
        async with self._lock:
            current_time = time.time()

            # Refill tokens based on elapsed time
            elapsed = current_time - self._last_refill
            if elapsed >= self.period:
                self._tokens = self.rate_limit
                self._last_refill = current_time
            else:
                # Add tokens proportionally
                tokens_to_add = (elapsed / self.period) * self.rate_limit
                self._tokens = min(self.rate_limit, self._tokens + tokens_to_add)

            if self._tokens >= 1:
                self._tokens -= 1
                return

            # Calculate wait time
            wait_time = (1 - self._tokens) * self.min_interval

        # Wait outside of lock
        await asyncio.sleep(wait_time)

    @asynccontextmanager
    async def limit(self):
        """Context manager for rate limiting"""
        await self.acquire()
        yield


class AsyncBatchProcessor(Generic[T, R]):
    """Batch processor for async operations"""

    def __init__(
        self,
        processor: Callable[[List[T]], Awaitable[List[R]]],
        batch_size: int = 100,
        max_wait_time: float = 0.1,
        max_concurrent_batches: int = 5,
    ):
        self.processor = processor
        self.batch_size = batch_size
        self.max_wait_time = max_wait_time
        self.max_concurrent_batches = max_concurrent_batches

        self._pending: List[Tuple[T, asyncio.Future]] = []
        self._batch_semaphore = AsyncSemaphore(max_concurrent_batches)
        self._lock = asyncio.Lock()
        self._processor_task: Optional[asyncio.Task] = None
        self._shutdown = False

        self._metrics = {
            "items_processed": 0,
            "batches_processed": 0,
            "total_processing_time": 0.0,
            "avg_batch_time": 0.0,
        }

    async def process_item(self, item: T) -> R:
        """Add item to batch and wait for processing"""
        if self._shutdown:
            raise RuntimeError("Batch processor is shutdown")

        future = asyncio.Future()

        async with self._lock:
            self._pending.append((item, future))

            # Start processor if needed
            if self._processor_task is None or self._processor_task.done():
                self._processor_task = asyncio.create_task(self._process_loop())

            # Trigger immediate processing if batch is full
            if len(self._pending) >= self.batch_size:
                # Cancel current task to trigger immediate processing
                if self._processor_task and not self._processor_task.done():
                    self._processor_task.cancel()
                    try:
                        await self._processor_task
                    except asyncio.CancelledError:
                        pass
                self._processor_task = asyncio.create_task(self._process_immediate())

        return await future

    async def _process_loop(self):
        """Main processing loop"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.max_wait_time)

                async with self._lock:
                    if not self._pending:
                        break

                    batch = self._pending[:]
                    self._pending.clear()

                if batch:
                    await self._process_batch(batch)

            except asyncio.CancelledError:
                # Process remaining items
                async with self._lock:
                    batch = self._pending[:]
                    self._pending.clear()

                if batch:
                    await self._process_batch(batch)
                break

            except Exception as e:
                logger.error(f"Batch processing loop error: {e}")

    async def _process_immediate(self):
        """Process immediately when batch is full"""
        async with self._lock:
            batch = self._pending[:]
            self._pending.clear()

        if batch:
            await self._process_batch(batch)

    async def _process_batch(self, batch: List[Tuple[T, asyncio.Future]]):
        """Process a single batch"""
        start_time = time.time()

        async with self._batch_semaphore.acquire():
            try:
                # Extract items
                items = [item for item, _ in batch]
                futures = [future for _, future in batch]

                # Process items
                results = await self.processor(items)

                # Set results
                for future, result in zip(futures, results):
                    if not future.done():
                        future.set_result(result)

                # Update metrics
                processing_time = time.time() - start_time
                self._metrics["items_processed"] += len(batch)
                self._metrics["batches_processed"] += 1
                self._metrics["total_processing_time"] += processing_time
                self._metrics["avg_batch_time"] = (
                    self._metrics["total_processing_time"] / self._metrics["batches_processed"]
                )

            except Exception as e:
                # Set exception for all futures in batch
                for _, future in batch:
                    if not future.done():
                        future.set_exception(e)

    async def shutdown(self, wait_for_completion: bool = True):
        """Shutdown batch processor"""
        self._shutdown = True

        if wait_for_completion and self._processor_task:
            # Process remaining items
            async with self._lock:
                batch = self._pending[:]
                self._pending.clear()

            if batch:
                await self._process_batch(batch)

            # Wait for task to complete
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

    def get_metrics(self) -> Dict[str, Any]:
        """Get batch processing metrics"""
        return dict(self._metrics)


class AsyncConnectionPool:
    """Async connection pool with health checks and metrics"""

    def __init__(
        self,
        create_connection: Callable[[], Awaitable[T]],
        max_connections: int = 10,
        min_connections: int = 1,
        health_check_interval: float = 30.0,
        max_idle_time: float = 300.0,
    ):
        self.create_connection = create_connection
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.health_check_interval = health_check_interval
        self.max_idle_time = max_idle_time

        self._pool: Deque[Tuple[T, float]] = deque()
        self._in_use: Set[T] = set()
        self._lock = asyncio.Lock()
        self._semaphore = AsyncSemaphore(max_connections)
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown = False

        self._metrics = {
            "connections_created": 0,
            "connections_reused": 0,
            "health_checks": 0,
            "failed_health_checks": 0,
            "connections_closed": 0,
        }

    async def initialize(self):
        """Initialize the connection pool"""
        # Create minimum connections
        for _ in range(self.min_connections):
            try:
                conn = await self.create_connection()
                self._pool.append((conn, time.time()))
                self._metrics["connections_created"] += 1
            except Exception as e:
                logger.error(f"Failed to create initial connection: {e}")

        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    @asynccontextmanager
    async def get_connection(self, timeout: Optional[float] = None):
        """Get connection from pool"""
        async with self._semaphore.acquire(timeout):
            async with self._lock:
                # Try to get existing connection
                while self._pool:
                    conn, last_used = self._pool.popleft()

                    # Check if connection is too old
                    if time.time() - last_used > self.max_idle_time:
                        await self._close_connection(conn)
                        self._metrics["connections_closed"] += 1
                        continue

                    self._in_use.add(conn)
                    self._metrics["connections_reused"] += 1
                    break
                else:
                    # Create new connection
                    conn = await self.create_connection()
                    self._in_use.add(conn)
                    self._metrics["connections_created"] += 1

            try:
                # Perform health check
                if not await self._is_healthy(conn):
                    await self._close_connection(conn)
                    self._metrics["failed_health_checks"] += 1
                    raise RuntimeError("Connection health check failed")

                yield conn

            finally:
                # Return connection to pool
                async with self._lock:
                    self._in_use.discard(conn)
                    if not self._shutdown:
                        self._pool.append((conn, time.time()))

    async def _is_healthy(self, conn: T) -> bool:
        """Check if connection is healthy"""
        try:
            # Default health check - can be overridden
            if hasattr(conn, "ping"):
                return await conn.ping()
            elif hasattr(conn, "execute"):
                # Database connection
                await conn.execute("SELECT 1")
                return True
            return True
        except Exception:
            return False

    async def _close_connection(self, conn: T):
        """Close connection"""
        try:
            if hasattr(conn, "close"):
                if asyncio.iscoroutinefunction(conn.close):
                    await conn.close()
                else:
                    conn.close()
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")

    async def _health_check_loop(self):
        """Periodic health check loop"""
        while not self._shutdown:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _perform_health_checks(self):
        """Perform health checks on all pooled connections"""
        async with self._lock:
            healthy_connections = deque()

            while self._pool:
                conn, last_used = self._pool.popleft()

                if await self._is_healthy(conn):
                    healthy_connections.append((conn, last_used))
                else:
                    await self._close_connection(conn)
                    self._metrics["failed_health_checks"] += 1

            self._pool = healthy_connections
            self._metrics["health_checks"] += len(healthy_connections)

    async def close_all(self):
        """Close all connections and shutdown pool"""
        self._shutdown = True

        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        async with self._lock:
            # Close pooled connections
            while self._pool:
                conn, _ = self._pool.popleft()
                await self._close_connection(conn)
                self._metrics["connections_closed"] += 1

            # Close in-use connections
            for conn in self._in_use:
                await self._close_connection(conn)
                self._metrics["connections_closed"] += 1

            self._in_use.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """Get pool metrics"""
        return {
            **self._metrics,
            "pool_size": len(self._pool),
            "in_use": len(self._in_use),
            "max_connections": self.max_connections,
        }


def async_circuit_breaker(
    failure_threshold: int = 5, recovery_timeout: float = 60.0, expected_exception: type = Exception
):
    """Async circuit breaker decorator"""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        # Circuit breaker state
        failure_count = 0
        last_failure_time = None
        state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        lock = asyncio.Lock()

        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            nonlocal failure_count, last_failure_time, state

            async with lock:
                if state == "OPEN":
                    # Check if recovery timeout has passed
                    if time.time() - last_failure_time > recovery_timeout:
                        state = "HALF_OPEN"
                    else:
                        raise RuntimeError("Circuit breaker is OPEN")

            try:
                result = await func(*args, **kwargs)

                # Success - reset circuit breaker
                async with lock:
                    if state == "HALF_OPEN":
                        state = "CLOSED"
                    failure_count = 0

                return result

            except expected_exception:
                async with lock:
                    failure_count += 1
                    last_failure_time = time.time()

                    if failure_count >= failure_threshold:
                        state = "OPEN"
                        logger.warning(
                            f"Circuit breaker OPEN for {func.__name__} after {failure_count} failures"
                        )

                raise

        wrapper._circuit_breaker_state = lambda: {"state": state, "failure_count": failure_count}
        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[type, ...] = (Exception,),
):
    """Async retry decorator with exponential backoff"""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")

            raise last_exception

        return wrapper

    return decorator


class AsyncPerformanceMonitor:
    """Monitor performance of async operations"""

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._operation_times: Dict[str, Deque[float]] = defaultdict(
            lambda: deque(maxlen=max_samples)
        )
        self._operation_counts: Dict[str, int] = defaultdict(int)
        self._operation_errors: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def monitor(self, operation_name: str):
        """Context manager for monitoring operation performance"""
        start_time = time.time()
        error = None

        try:
            yield
        except Exception as e:
            error = e
            raise
        finally:
            duration = time.time() - start_time

            async with self._lock:
                self._operation_times[operation_name].append(duration)
                self._operation_counts[operation_name] += 1
                if error:
                    self._operation_errors[operation_name] += 1

    def get_stats(self, operation_name: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics"""
        if operation_name:
            return self._get_operation_stats(operation_name)

        stats = {}
        for op_name in self._operation_times.keys():
            stats[op_name] = self._get_operation_stats(op_name)
        return stats

    def _get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get stats for specific operation"""
        times = self._operation_times[operation_name]
        count = self._operation_counts[operation_name]
        errors = self._operation_errors[operation_name]

        if not times:
            return {
                "count": count,
                "errors": errors,
                "error_rate": 0.0,
                "avg_time": 0.0,
                "min_time": 0.0,
                "max_time": 0.0,
            }

        return {
            "count": count,
            "errors": errors,
            "error_rate": (errors / count * 100) if count > 0 else 0.0,
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "p95_time": sorted(times)[int(len(times) * 0.95)] if len(times) > 0 else 0.0,
            "p99_time": sorted(times)[int(len(times) * 0.99)] if len(times) > 0 else 0.0,
        }


# Global performance monitor
_global_monitor: Optional[AsyncPerformanceMonitor] = None


def get_async_monitor() -> AsyncPerformanceMonitor:
    """Get or create global async performance monitor"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = AsyncPerformanceMonitor()
    return _global_monitor


def monitor_async_performance(operation_name: str):
    """Decorator for monitoring async operation performance"""
    monitor = get_async_monitor()

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            async with monitor.monitor(operation_name or f"{func.__module__}.{func.__qualname__}"):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


@asynccontextmanager
async def optimized_async_context(
    resource_factory: Callable[[], Awaitable[T]],
    cleanup_func: Optional[Callable[[T], Awaitable[None]]] = None,
):
    """Optimized async context manager with resource cleanup"""
    resource = None
    try:
        resource = await resource_factory()
        yield resource
    finally:
        if resource:
            if cleanup_func:
                await cleanup_func(resource)
            elif hasattr(resource, "aclose"):
                await resource.aclose()
            elif hasattr(resource, "close"):
                if asyncio.iscoroutinefunction(resource.close):
                    await resource.close()
                else:
                    resource.close()
