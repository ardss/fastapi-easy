"""
Query Parameter Processing Optimizer

This module provides high-performance query parameter processing with:
- Type hint resolution caching
- JSON parsing optimization
- Batch processing capabilities
- Reduced redundant validation
- Memory-efficient operations
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import inspect
import json
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import RLock
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    get_type_hints,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ProcessingMetrics:
    """Metrics for query parameter processing"""

    total_processed: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    avg_processing_time: float = 0.0
    peak_processing_time: float = 0.0
    validation_time: float = 0.0
    parsing_time: float = 0.0
    batch_operations: int = 0

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.cache_hits + self.cache_misses
        return (self.cache_hits / total * 100) if total > 0 else 0.0


class TypeHintCache:
    """High-performance cache for type hint resolution"""

    def __init__(self, max_size: int = 1000, ttl: float = 300.0):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, Tuple[Dict[str, Type], float]] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = RLock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _generate_key(self, func: Callable) -> str:
        """Generate cache key for function"""
        # Use function source and signature for stable key
        try:
            source = inspect.getsource(func)
            signature = str(inspect.signature(func))
            key_data = f"{func.__module__}.{func.__qualname__}:{signature}:{source}"
            return hashlib.sha256(key_data.encode()).hexdigest()[:16]
        except Exception:
            # Fallback to function name and module
            return f"{func.__module__}.{func.__qualname__}"

    def get_type_hints(self, func: Callable) -> Dict[str, Type]:
        """Get cached type hints for function"""
        key = self._generate_key(func)
        current_time = time.time()

        with self._lock:
            if key in self._cache:
                hints, timestamp = self._cache[key]
                if current_time - timestamp < self.ttl:
                    self._access_times[key] = current_time
                    self._stats["hits"] += 1
                    return hints
                else:
                    # Expired entry
                    del self._cache[key]
                    if key in self._access_times:
                        del self._access_times[key]

            # Cache miss - compute and store
            self._stats["misses"] += 1
            try:
                hints = get_type_hints(func)
            except (NameError, TypeError):
                # Fallback for problematic type hints
                hints = {}

            # Check if we need to evict
            if len(self._cache) >= self.max_size:
                self._evict_oldest()

            self._cache[key] = (hints, current_time)
            self._access_times[key] = current_time
            return hints

    def _evict_oldest(self):
        """Evict oldest entries from cache"""
        if not self._access_times:
            return

        # Remove 25% of oldest entries
        to_remove = max(1, self.max_size // 4)
        sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])

        for key, _ in sorted_keys[:to_remove]:
            if key in self._cache:
                del self._cache[key]
            del self._access_times[key]
            self._stats["evictions"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0

            return {
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                **self._stats,
            }

    def clear(self):
        """Clear cache"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._stats = {"hits": 0, "misses": 0, "evictions": 0}


class JSONOptimizer:
    """Optimized JSON parsing with caching and batch processing"""

    def __init__(self, cache_size: int = 500):
        self.cache_size = cache_size
        self._parse_cache: Dict[str, Any] = {}
        self._stringify_cache: Dict[str, str] = {}
        self._lock = RLock()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="json_optimizer")

        # Pre-allocate common patterns
        self._common_patterns = {
            "empty_object": "{}",
            "empty_array": "[]",
            "null": "null",
            "true": "true",
            "false": "false",
        }

    def parse_json(self, json_str: str, use_cache: bool = True) -> Any:
        """Parse JSON with optimization and caching"""
        if not json_str or json_str in self._common_patterns.values():
            return self._parse_common(json_str)

        if use_cache:
            cache_key = hashlib.md5(json_str.encode()).hexdigest()

            with self._lock:
                if cache_key in self._parse_cache:
                    return self._parse_cache[cache_key]

        try:
            result = json.loads(json_str)

            if use_cache:
                with self._lock:
                    if len(self._parse_cache) < self.cache_size:
                        self._parse_cache[cache_key] = result

            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            raise

    def _parse_common(self, json_str: str) -> Any:
        """Parse common JSON patterns"""
        if json_str == "{}":
            return {}
        elif json_str == "[]":
            return []
        elif json_str == "null":
            return None
        elif json_str == "true":
            return True
        elif json_str == "false":
            return False
        return None

    def stringify_json(self, obj: Any, use_cache: bool = True) -> str:
        """Stringify object with caching"""
        if obj is None:
            return "null"
        elif obj is True:
            return "true"
        elif obj is False:
            return "false"
        elif obj == {}:
            return "{}"
        elif obj == []:
            return "[]"

        if use_cache and isinstance(obj, (dict, list, str, int, float, bool)):
            try:
                # Create stable cache key
                if isinstance(obj, dict):
                    sorted_items = tuple(sorted(obj.items()))
                    cache_key = hashlib.md5(str(sorted_items).encode()).hexdigest()
                elif isinstance(obj, list):
                    cache_key = hashlib.md5(str(tuple(obj)).encode()).hexdigest()
                else:
                    cache_key = hashlib.md5(str(obj).encode()).hexdigest()

                with self._lock:
                    if cache_key in self._stringify_cache:
                        return self._stringify_cache[cache_key]
            except (TypeError, ValueError):
                use_cache = False

        try:
            result = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)

            if use_cache:
                with self._lock:
                    if len(self._stringify_cache) < self.cache_size:
                        self._stringify_cache[cache_key] = result

            return result

        except (TypeError, ValueError) as e:
            logger.error(f"JSON stringify error: {e}")
            raise

    async def parse_batch(self, json_strings: List[str]) -> List[Any]:
        """Parse multiple JSON strings in parallel"""
        if not json_strings:
            return []

        # Use thread pool for CPU-bound parsing
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self._executor, self.parse_json, json_str)
            for json_str in json_strings
        ]

        return await asyncio.gather(*tasks, return_exceptions=True)

    async def stringify_batch(self, objects: List[Any]) -> List[str]:
        """Stringify multiple objects in parallel"""
        if not objects:
            return []

        loop = asyncio.get_event_loop()
        tasks = [loop.run_in_executor(self._executor, self.stringify_json, obj) for obj in objects]

        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        with self._lock:
            return {
                "parse_cache_size": len(self._parse_cache),
                "stringify_cache_size": len(self._stringify_cache),
                "max_cache_size": self.cache_size,
            }

    def clear_cache(self):
        """Clear all caches"""
        with self._lock:
            self._parse_cache.clear()
            self._stringify_cache.clear()


class ValidationCache:
    """Cache for validation results to avoid redundant checks"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, bool] = {}
        self._lock = RLock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    def _generate_key(self, value: Any, validator: Callable) -> str:
        """Generate cache key for value and validator"""
        try:
            # Use type and value representation
            type_name = type(value).__name__
            value_repr = repr(value)[:100]  # Limit size
            validator_name = (
                validator.__name__ if hasattr(validator, "__name__") else str(validator)
            )
            return (
                f"{type_name}:{validator_name}:{hashlib.md5(value_repr.encode()).hexdigest()[:8]}"
            )
        except Exception:
            return f"{type(value).__name__}:{id(validator)}"

    def validate(self, value: Any, validator: Callable) -> bool:
        """Validate with caching"""
        key = self._generate_key(value, validator)

        with self._lock:
            if key in self._cache:
                self._stats["hits"] += 1
                return self._cache[key]

            self._stats["misses"] += 1

            # Check cache size
            if len(self._cache) >= self.max_size:
                self._evict_random()

            # Perform validation
            try:
                result = validator(value)
                self._cache[key] = result
                return result
            except Exception as e:
                logger.warning(f"Validation error: {e}")
                self._cache[key] = False
                return False

    def _evict_random(self):
        """Evict random entries when cache is full"""
        import random

        to_remove = max(1, self.max_size // 10)
        keys = list(self._cache.keys())

        for key in random.sample(keys, min(to_remove, len(keys))):
            del self._cache[key]
            self._stats["evictions"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get validation cache statistics"""
        with self._lock:
            total_requests = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0

            return {
                "cache_size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate": hit_rate,
                "total_requests": total_requests,
                **self._stats,
            }


class BatchProcessor:
    """Batch processor for optimizing multiple parameter operations"""

    def __init__(self, batch_size: int = 100, max_delay: float = 0.1):
        self.batch_size = batch_size
        self.max_delay = max_delay
        self._pending: List[Tuple[Callable, tuple, dict, asyncio.Future]] = []
        self._processor_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._metrics = {"batches_processed": 0, "items_processed": 0, "total_time": 0.0}

    async def process_item(self, func: Callable, args: tuple = (), kwargs: dict = None) -> Any:
        """Add item to batch and wait for processing"""
        if kwargs is None:
            kwargs = {}

        future = asyncio.Future()

        async with self._lock:
            self._pending.append((func, args, kwargs, future))

            # Start processor if not running
            if self._processor_task is None or self._processor_task.done():
                self._processor_task = asyncio.create_task(self._process_batches())

            # Trigger processing if batch is full
            if len(self._pending) >= self.batch_size:
                self._processor_task.cancel()
                self._processor_task = asyncio.create_task(self._process_batches())

        return await future

    async def _process_batches(self):
        """Process pending items in batches"""
        while True:
            try:
                # Wait for batch to fill or timeout
                await asyncio.sleep(self.max_delay)

                async with self._lock:
                    if not self._pending:
                        break

                    # Get current batch
                    batch = self._pending[:]
                    self._pending.clear()

                if batch:
                    start_time = time.time()
                    await self._process_batch(batch)
                    processing_time = time.time() - start_time

                    self._metrics["batches_processed"] += 1
                    self._metrics["items_processed"] += len(batch)
                    self._metrics["total_time"] += processing_time

            except asyncio.CancelledError:
                # Process any remaining items before exiting
                async with self._lock:
                    batch = self._pending[:]
                    self._pending.clear()

                if batch:
                    await self._process_batch(batch)
                break

            except Exception as e:
                logger.error(f"Batch processing error: {e}")

    async def _process_batch(self, batch: List[Tuple[Callable, tuple, dict, asyncio.Future]]):
        """Process a single batch of items"""
        # Group by function for optimization
        function_groups = defaultdict(list)

        for func, args, kwargs, future in batch:
            function_groups[func].append((args, kwargs, future))

        # Process each group
        for func, items in function_groups.items():
            try:
                if asyncio.iscoroutinefunction(func):
                    # Process async functions in parallel
                    tasks = [func(*args, **kwargs) for args, kwargs, _ in items]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    for (_, _, future), result in zip(items, results):
                        if isinstance(result, Exception):
                            future.set_exception(result)
                        else:
                            future.set_result(result)
                else:
                    # Process sync functions in thread pool
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor(max_workers=4) as executor:
                        tasks = [
                            loop.run_in_executor(executor, func, *args, **kwargs)
                            for args, kwargs, _ in items
                        ]
                        results = await asyncio.gather(*tasks, return_exceptions=True)

                        for (_, _, future), result in zip(items, results):
                            if isinstance(result, Exception):
                                future.set_exception(result)
                            else:
                                future.set_result(result)

            except Exception as e:
                # Set exception for all items in this group
                for _, _, future in items:
                    if not future.done():
                        future.set_exception(e)

    def get_metrics(self) -> Dict[str, Any]:
        """Get batch processing metrics"""
        total_items = self._metrics["items_processed"]
        avg_time = (
            self._metrics["total_time"] / self._metrics["batches_processed"]
            if self._metrics["batches_processed"] > 0
            else 0.0
        )

        return {
            **self._metrics,
            "avg_batch_time": avg_time,
            "avg_items_per_batch": (
                total_items / self._metrics["batches_processed"]
                if self._metrics["batches_processed"] > 0
                else 0.0
            ),
        }


class QueryParameterOptimizer:
    """Main optimizer for query parameter processing"""

    def __init__(
        self,
        type_cache_size: int = 1000,
        json_cache_size: int = 500,
        validation_cache_size: int = 1000,
        batch_size: int = 100,
        batch_delay: float = 0.1,
    ):
        self.type_cache = TypeHintCache(type_cache_size)
        self.json_optimizer = JSONOptimizer(json_cache_size)
        self.validation_cache = ValidationCache(validation_cache_size)
        self.batch_processor = BatchProcessor(batch_size, batch_delay)

        self.metrics = ProcessingMetrics()
        self._processing_times = deque(maxlen=1000)  # Keep last 1000 measurements

    async def process_parameters(
        self, func: Callable, parameters: Dict[str, Any], validate: bool = True
    ) -> Dict[str, Any]:
        """Process and validate parameters with optimization"""
        start_time = time.time()

        try:
            # Get type hints with caching
            type_hints = self.type_cache.get_type_hints(func)

            processed = {}
            validation_start = time.time()

            for param_name, param_value in parameters.items():
                if param_name in type_hints:
                    expected_type = type_hints[param_name]

                    # Type conversion and validation
                    processed_value = await self._process_parameter(
                        param_value, expected_type, validate
                    )
                    processed[param_name] = processed_value
                else:
                    processed[param_name] = param_value

            self.metrics.validation_time += time.time() - validation_start

            return processed

        finally:
            processing_time = time.time() - start_time
            self._processing_times.append(processing_time)
            self._update_metrics(processing_time)

    async def _process_parameter(self, value: Any, expected_type: Type, validate: bool) -> Any:
        """Process individual parameter with optimization"""
        # Handle JSON strings efficiently
        if expected_type in (dict, list) and isinstance(value, str):
            try:
                return self.json_optimizer.parse_json(value)
            except json.JSONDecodeError:
                pass

        # Type conversion
        if not isinstance(value, expected_type):
            try:
                if expected_type is bool:
                    return self._convert_to_bool(value)
                elif expected_type is int:
                    return int(value)
                elif expected_type is float:
                    return float(value)
                elif expected_type is str:
                    return str(value)
                elif hasattr(expected_type, "__origin__"):
                    # Handle generic types (List, Dict, etc.)
                    return self._handle_generic_type(value, expected_type)
            except (ValueError, TypeError) as e:
                if validate:
                    raise ValueError(f"Cannot convert {value} to {expected_type}: {e}")

        # Validation if needed
        if validate and expected_type is not Any:
            if not self.validation_cache.validate(value, type(expected_type)):
                raise ValueError(f"Invalid value for type {expected_type}: {value}")

        return value

    def _convert_to_bool(self, value: Any) -> bool:
        """Convert value to boolean efficiently"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        elif isinstance(value, (int, float)):
            return bool(value)
        else:
            return bool(value)

    def _handle_generic_type(self, value: Any, expected_type: Type) -> Any:
        """Handle generic types like List[T], Dict[K, V]"""
        origin = getattr(expected_type, "__origin__", None)

        if origin is list and isinstance(value, (list, tuple)):
            return list(value)
        elif origin is dict and isinstance(value, dict):
            return dict(value)
        elif origin is list and isinstance(value, str):
            # Try to parse JSON list
            try:
                parsed = self.json_optimizer.parse_json(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
            # Fallback to comma-separated
            return [item.strip() for item in value.split(",") if item.strip()]

        return value

    def _update_metrics(self, processing_time: float):
        """Update processing metrics"""
        self.metrics.total_processed += 1
        self.metrics.total_acquire_time += processing_time
        self.metrics.avg_processing_time = (
            self.metrics.total_acquire_time / self.metrics.total_processed
        )

        if processing_time > self.metrics.peak_processing_time:
            self.metrics.peak_processing_time = processing_time

    async def process_batch_parameters(
        self, requests: List[Tuple[Callable, Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Process multiple parameter sets in batch"""
        self.metrics.batch_operations += 1

        tasks = [self.process_parameters(func, params) for func, params in requests]

        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics"""
        return {
            "processing_metrics": self.metrics.__dict__,
            "type_cache_stats": self.type_cache.get_stats(),
            "json_optimizer_stats": self.json_optimizer.get_stats(),
            "validation_cache_stats": self.validation_cache.get_stats(),
            "batch_processor_metrics": self.batch_processor.get_metrics(),
            "recent_performance": {
                "avg_last_100": (
                    sum(self._processing_times) / len(self._processing_times)
                    if self._processing_times
                    else 0.0
                ),
                "min_last_100": min(self._processing_times) if self._processing_times else 0.0,
                "max_last_100": max(self._processing_times) if self._processing_times else 0.0,
            },
        }

    async def cleanup(self):
        """Cleanup resources"""
        # Cancel any pending batch processing
        if self.batch_processor._processor_task:
            self.batch_processor._processor_task.cancel()

        # Clear caches
        self.type_cache.clear()
        self.json_optimizer.clear_cache()

        logger.info("Query parameter optimizer cleaned up")


# Global optimizer instance
_global_optimizer: Optional[QueryParameterOptimizer] = None


def get_query_optimizer() -> QueryParameterOptimizer:
    """Get or create global query optimizer instance"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = QueryParameterOptimizer()
    return _global_optimizer


def optimize_parameter_processing(func: Callable) -> Callable:
    """Decorator to optimize parameter processing for a function"""
    optimizer = get_query_optimizer()

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Convert args to kwargs using function signature
        sig = inspect.signature(func)
        bound_args = sig.bind_partial(*args, **kwargs)
        bound_args.apply_defaults()

        # Process parameters
        processed_params = await optimizer.process_parameters(func, bound_args.arguments)

        # Call function with processed parameters
        return await func(**processed_params)

    return wrapper
