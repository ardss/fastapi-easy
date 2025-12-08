"""
Advanced Async Utilities for FastAPI-Easy

Provides:
- Async context managers
- Concurrent execution patterns
- Resource management
- Async generators and streams
- Performance monitoring
- Circuit breaker pattern
- Retry mechanisms
"""

from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if system recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: Type[Exception] = Exception
    recovery_timeout_max: float = 300.0
    recovery_timeout_multiplier: float = 2.0


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for resilience
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None, name: Optional[str] = None):
        self.config = config or CircuitBreakerConfig()
        self.name = name or "unnamed"
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.recovery_timeout = self.config.recovery_timeout

    async def __aenter__(self):
        """Enter circuit breaker context"""
        if not self.can_execute():
            raise Exception(f"Circuit breaker '{self.name}' is OPEN")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit circuit breaker context"""
        if exc_type and issubclass(exc_type, self.config.expected_exception):
            self.record_failure()
        else:
            self.record_success()

    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        elif self.state == CircuitState.HALF_OPEN:
            return True
        return False

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset"""
        return (
            self.last_failure_time and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def record_success(self):
        """Record a successful execution"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.recovery_timeout = self.config.recovery_timeout
            logger.info(f"Circuit breaker '{self.name}' CLOSED after successful test")

    def record_failure(self):
        """Record a failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.recovery_timeout = min(
                self.recovery_timeout * self.config.recovery_timeout_multiplier,
                self.config.recovery_timeout_max,
            )
            logger.warning(
                f"Circuit breaker '{self.name}' OPEN after failure "
                f"during HALF_OPEN state. Recovery timeout: {self.recovery_timeout}s"
            )
        elif (
            self.state == CircuitState.CLOSED
            and self.failure_count >= self.config.failure_threshold
        ):
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' OPEN after " f"{self.failure_count} failures"
            )


def circuit_breaker(config: Optional[CircuitBreakerConfig] = None, name: Optional[str] = None):
    """Decorator for circuit breaker pattern"""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        cb = CircuitBreaker(config, name or func.__name__)

        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            if not cb.can_execute():
                raise Exception(
                    f"Circuit breaker for {func.__name__} is OPEN. "
                    f"Last failure: {cb.last_failure_time}"
                )

            try:
                result = await func(*args, **kwargs)
                cb.record_success()
                return result
            except Exception as e:
                if isinstance(e, (config.expected_exception if config else Exception)):
                    cb.record_failure()
                raise

        return wrapper

    return decorator


@dataclass
class RetryConfig:
    """Configuration for retry mechanism"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: Tuple[Type[Exception], ...] = (Exception,)


async def retry(
    func: Callable[..., Awaitable[T]], config: Optional[RetryConfig] = None, *args, **kwargs
) -> T:
    """Execute function with retry logic"""
    cfg = config or RetryConfig()
    last_exception = None

    for attempt in range(cfg.max_attempts):
        try:
            return await func(*args, **kwargs)
        except cfg.retry_on as e:
            last_exception = e

            if attempt == cfg.max_attempts - 1:
                # Last attempt, re-raise
                logger.error(
                    f"Function {func.__name__} failed after " f"{cfg.max_attempts} attempts: {e!s}"
                )
                raise

            # Calculate delay
            delay = cfg.base_delay * (cfg.exponential_base**attempt)
            delay = min(delay, cfg.max_delay)

            if cfg.jitter:
                # Add jitter to prevent thundering herd
                import random

                delay *= 0.5 + random.random() * 0.5

            logger.warning(
                f"Attempt {attempt + 1} failed for {func.__name__}: {e!s}. "
                f"Retrying in {delay:.2f}s"
            )
            await asyncio.sleep(delay)

    # Should never reach here
    if last_exception:
        raise last_exception


def retry_decorator(config: Optional[RetryConfig] = None):
    """Decorator for retry functionality"""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry(func, config, *args, **kwargs)

        return wrapper

    return decorator


class AsyncContextPool:
    """
    Pool for managing async context managers efficiently
    """

    def __init__(
        self,
        factory: Callable[..., Awaitable[Any]],
        max_size: int = 10,
        max_idle_time: float = 300.0,
        *factory_args,
        **factory_kwargs,
    ):
        self.factory = factory
        self.factory_args = factory_args
        self.factory_kwargs = factory_kwargs
        self.max_size = max_size
        self.max_idle_time = max_idle_time

        self._pool: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._created = 0
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()

    async def get(self) -> Any:
        """Get a context manager from the pool"""
        # Periodic cleanup
        await self._cleanup_stale()

        try:
            # Try to get from pool
            cm = self._pool.get_nowait()
            return cm
        except asyncio.QueueEmpty:
            # Pool empty, create new
            async with self._lock:
                if self._created < self.max_size:
                    self._created += 1
                    return await self.factory(*self.factory_args, **self.factory_kwargs)
                else:
                    # Wait for an available connection
                    return await self._pool.get()

    async def put(self, cm: Any) -> None:
        """Return a context manager to the pool"""
        try:
            # Mark with timestamp
            if hasattr(cm, "_last_used"):
                cm._last_used = time.time()
            self._pool.put_nowait(cm)
        except asyncio.QueueFull:
            # Pool full, just discard
            if hasattr(cm, "close"):
                await cm.close()

    async def _cleanup_stale(self) -> None:
        """Remove stale items from pool"""
        now = time.time()
        if now - self._last_cleanup < 60:  # Cleanup every minute
            return

        self._last_cleanup = now
        to_remove = []

        # Check items in queue
        temp_items = []
        while True:
            try:
                cm = self._pool.get_nowait()
                if hasattr(cm, "_last_used") and now - cm._last_used > self.max_idle_time:
                    to_remove.append(cm)
                    self._created -= 1
                else:
                    temp_items.append(cm)
            except asyncio.QueueEmpty:
                break

        # Put back non-stale items
        for cm in temp_items:
            try:
                self._pool.put_nowait(cm)
            except asyncio.QueueFull:
                pass

        # Close stale items
        for cm in to_remove:
            if hasattr(cm, "close"):
                try:
                    await cm.close()
                except Exception as e:
                    logger.warning(f"Error closing stale pool item: {e}")

    @asynccontextmanager
    async def acquire(self):
        """Context manager for acquiring and releasing"""
        cm = None
        try:
            cm = await self.get()
            if hasattr(cm, "__aenter__"):
                async with cm as item:
                    yield item
            else:
                yield cm
        finally:
            if cm:
                await self.put(cm)


class AsyncBatchProcessor:
    """
    Process items in batches with controlled concurrency
    """

    def __init__(
        self,
        batch_size: int = 100,
        max_concurrency: int = 10,
        process_func: Optional[Callable[[List[T]], Awaitable[List[R]]]] = None,
        error_handler: Optional[Callable[[Exception, T], None]] = None,
    ):
        self.batch_size = batch_size
        self.max_concurrency = max_concurrency
        self.process_func = process_func
        self.error_handler = error_handler
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def process_items(self, items: List[T]) -> List[R]:
        """Process items in batches with controlled concurrency"""
        if not self.process_func:
            raise ValueError("process_func must be provided")

        batches = [items[i : i + self.batch_size] for i in range(0, len(items), self.batch_size)]

        # Process batches concurrently
        tasks = []
        for batch in batches:
            task = self._process_batch_with_semaphore(batch)
            tasks.append(task)

        # Wait for all batches to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results
        all_results = []
        for result in batch_results:
            if isinstance(result, Exception):
                if self.error_handler:
                    self.error_handler(result, None)
                logger.error(f"Batch processing failed: {result}")
            else:
                all_results.extend(result)

        return all_results

    async def _process_batch_with_semaphore(self, batch: List[T]) -> List[R]:
        """Process a single batch with semaphore control"""
        async with self._semaphore:
            try:
                return await self.process_func(batch)
            except Exception as e:
                if self.error_handler:
                    for item in batch:
                        try:
                            self.error_handler(e, item)
                        except Exception as inner_e:
                            logger.error(f"Error handler failed: {inner_e}")
                raise


class AsyncRateLimiter:
    """
    Rate limiter for async operations
    """

    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire permission to make a call"""
        async with self._lock:
            now = time.time()

            # Remove old calls outside the time window
            self.calls = [
                call_time for call_time in self.calls if now - call_time < self.time_window
            ]

            # Check if we can make a call
            if len(self.calls) >= self.max_calls:
                # Calculate wait time
                oldest_call = min(self.calls)
                wait_time = self.time_window - (now - oldest_call)
                if wait_time > 0:
                    logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)

            # Record this call
            self.calls.append(now)


class AsyncStream:
    """
    Async stream utilities for efficient data processing
    """

    @staticmethod
    async def batch(
        source: AsyncGenerator[T, None], batch_size: int
    ) -> AsyncGenerator[List[T], None]:
        """Batch items from async generator"""
        batch = []
        async for item in source:
            batch.append(item)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    @staticmethod
    async def map(
        source: AsyncGenerator[T, None], func: Callable[[T], Awaitable[R]], concurrency: int = 10
    ) -> AsyncGenerator[R, None]:
        """Map async function over stream with concurrency"""
        semaphore = asyncio.Semaphore(concurrency)

        async def process_item(item: T) -> R:
            async with semaphore:
                return await func(item)

        async for item in source:
            # Don't wait for result to maintain order
            yield asyncio.create_task(process_item(item))

    @staticmethod
    async def filter(
        source: AsyncGenerator[T, None], predicate: Callable[[T], Awaitable[bool]]
    ) -> AsyncGenerator[T, None]:
        """Filter items from async generator"""
        async for item in source:
            if await predicate(item):
                yield item

    @staticmethod
    async def merge(*sources: AsyncGenerator[T, None]) -> AsyncGenerator[T, None]:
        """Merge multiple async generators"""
        queues = [asyncio.Queue() for _ in sources]

        async def producer(source: AsyncGenerator[T, None], queue: asyncio.Queue):
            async for item in source:
                await queue.put(item)
            await queue.put(None)  # Signal end

        # Start producers
        tasks = [
            asyncio.create_task(producer(source, queue)) for source, queue in zip(sources, queues)
        ]

        # Yield items from queues
        active_queues = set(queues)
        while active_queues:
            done, pending = await asyncio.wait(
                [queue.get() for queue in active_queues], return_when=asyncio.FIRST_COMPLETED
            )

            for task in done:
                item = task.result()
                if item is None:
                    # Remove completed queue
                    for q in queues:
                        if q in active_queues and q.empty():
                            active_queues.remove(q)
                            break
                else:
                    yield item

        # Wait for all producers
        await asyncio.gather(*tasks)


class AsyncResourceManager:
    """
    Manage async resources with automatic cleanup
    """

    def __init__(self):
        self._resources: Dict[str, Any] = {}
        self._cleanup_tasks: List[Callable[[], Awaitable[None]]] = []
        self._lock = asyncio.Lock()

    async def register(
        self,
        name: str,
        resource: Any,
        cleanup_func: Optional[Callable[[Any], Awaitable[None]]] = None,
    ) -> None:
        """Register a resource for management"""
        async with self._lock:
            self._resources[name] = resource
            if cleanup_func:
                self._cleanup_tasks.append(lambda r=resource: cleanup_func(r))

    async def get(self, name: str) -> Any:
        """Get a managed resource"""
        async with self._lock:
            return self._resources.get(name)

    async def cleanup(self) -> None:
        """Clean up all managed resources"""
        async with self._lock:
            for cleanup_task in self._cleanup_tasks:
                try:
                    await cleanup_task()
                except Exception as e:
                    logger.error(f"Error during resource cleanup: {e}")

            self._resources.clear()
            self._cleanup_tasks.clear()

    @asynccontextmanager
    async def managed_context(self):
        """Context manager for resource management"""
        try:
            yield self
        finally:
            await self.cleanup()


# Global resource manager
_global_resource_manager = AsyncResourceManager()


async def get_global_resource_manager() -> AsyncResourceManager:
    """Get the global resource manager"""
    return _global_resource_manager


# Performance monitoring decorator
@dataclass
class PerformanceMetrics:
    """Track async operation performance"""

    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    errors: int = 0
    concurrent_calls: int = 0
    max_concurrent: int = 0

    @property
    def avg_time(self) -> float:
        return self.total_time / max(1, self.call_count)

    def reset(self) -> None:
        """Reset all metrics"""
        self.call_count = 0
        self.total_time = 0.0
        self.min_time = float("inf")
        self.max_time = 0.0
        self.errors = 0
        self.concurrent_calls = 0
        self.max_concurrent = 0


def monitor_async_performance(metrics: Optional[PerformanceMetrics] = None):
    """Decorator to monitor async function performance"""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        m = metrics or PerformanceMetrics()
        concurrent_calls = 0
        lock = asyncio.Lock()

        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            nonlocal concurrent_calls

            start_time = time.time()

            async with lock:
                concurrent_calls += 1
                m.concurrent_calls += 1
                m.max_concurrent = max(m.max_concurrent, concurrent_calls)

            try:
                m.call_count += 1
                result = await func(*args, **kwargs)
                return result
            except Exception:
                m.errors += 1
                raise
            finally:
                elapsed = time.time() - start_time
                m.total_time += elapsed
                m.min_time = min(m.min_time, elapsed)
                m.max_time = max(m.max_time, elapsed)

                async with lock:
                    concurrent_calls -= 1

        return wrapper

    return decorator


# Utility function for running sync code in thread pool
async def run_in_threadpool(
    func: Callable[..., T], *args, executor: Optional[ThreadPoolExecutor] = None, **kwargs
) -> T:
    """Run synchronous function in thread pool"""
    loop = asyncio.get_running_loop()
    if executor:
        return await loop.run_in_executor(executor, func, *args, **kwargs)
    else:
        return await loop.run_in_executor(None, func, *args, **kwargs)


# Context manager for timeout handling
@asynccontextmanager
async def timeout_context(timeout: float):
    """Context manager with timeout"""
    try:
        async with asyncio.timeout(timeout):
            yield
    except TimeoutError:
        logger.warning(f"Operation timed out after {timeout} seconds")
        raise


# Queue-based worker pattern
class AsyncWorker:
    """Background worker for processing queued tasks"""

    def __init__(
        self,
        task_func: Callable[[Any], Awaitable[None]],
        max_queue_size: int = 1000,
        num_workers: int = 1,
    ):
        self.task_func = task_func
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.num_workers = num_workers
        self.workers: List[asyncio.Task] = []
        self.running = False

    async def start(self) -> None:
        """Start the worker"""
        if self.running:
            return

        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(f"worker-{i}")) for i in range(self.num_workers)
        ]
        logger.info(f"Started {self.num_workers} workers")

    async def stop(self) -> None:
        """Stop the worker"""
        if not self.running:
            return

        self.running = False

        # Cancel workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)

        logger.info("Stopped all workers")

    async def put(self, task: Any) -> None:
        """Add task to queue"""
        try:
            await self.queue.put(task)
        except asyncio.QueueFull:
            logger.warning("Worker queue is full, dropping task")
            raise

    async def _worker(self, name: str) -> None:
        """Worker coroutine"""
        logger.debug(f"Worker {name} started")

        while self.running:
            try:
                # Get task with timeout
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)

                try:
                    await self.task_func(task)
                except Exception as e:
                    logger.error(f"Worker {name} task failed: {e}")

                self.queue.task_done()

            except asyncio.TimeoutError:
                # No task available, continue
                continue
            except Exception as e:
                logger.error(f"Worker {name} error: {e}")

        logger.debug(f"Worker {name} stopped")
