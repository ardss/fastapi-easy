"""Optimized query parameter handling with caching and performance improvements"""

from __future__ import annotations

import functools
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Type, get_args, get_origin, get_type_hints

from fastapi import Depends, Query
from pydantic import BaseModel, ValidationError


@dataclass
class QueryParamConfig:
    """Configuration for query parameter optimization"""

    enable_cache: bool = True
    cache_size: int = 1000
    cache_ttl: int = 3600  # 1 hour
    enable_async_parsing: bool = True
    batch_size: int = 100


class TypeHintCache:
    """LRU cache for type hints with TTL"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.max_size = max_size
        self.ttl = ttl
        self._cache: Dict[str, tuple] = {}
        self._access_times: Dict[str, float] = {}

    def _make_key(self, schema: Type) -> str:
        """Generate cache key from schema"""
        return f"{schema.__module__}.{schema.__qualname__}"

    def get(self, schema: Type) -> Optional[Dict[str, Any]]:
        """Get cached type hints"""
        key = self._make_key(schema)

        if key in self._cache:
            cached_time, hints = self._cache[key]

            # Check TTL
            if time.time() - cached_time < self.ttl:
                self._access_times[key] = time.time()
                return hints
            else:
                # Expired, remove
                del self._cache[key]
                if key in self._access_times:
                    del self._access_times[key]

        return None

    def set(self, schema: Type, hints: Dict[str, Any]):
        """Cache type hints"""
        key = self._make_key(schema)

        # Remove oldest if cache is full
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._access_times.keys(), key=lambda k: self._access_times[k])
            del self._cache[oldest_key]
            del self._access_times[oldest_key]

        self._cache[key] = (time.time(), hints)
        self._access_times[key] = time.time()


class JSONParserPool:
    """Pool of JSON parsers for better performance"""

    def __init__(self, pool_size: int = 10):
        self.pool_size = pool_size
        self._pool = []
        self._created = 0

        # Pre-warm the pool
        for _ in range(pool_size):
            self._pool.append(json.JSONDecoder())
            self._created += 1

    def get_parser(self):
        """Get a parser from the pool"""
        if self._pool:
            return self._pool.pop()
        else:
            # Create new parser if pool is empty
            if self._created < self.pool_size * 2:
                self._created += 1
                return json.JSONDecoder()
            else:
                # Fall back to default
                return json

    def return_parser(self, parser):
        """Return parser to pool"""
        if len(self._pool) < self.pool_size and hasattr(parser, "decode"):
            # Reset parser state
            try:
                parser.decode("")
                self._pool.append(parser)
            except:
                pass


# Global instances
_type_cache = TypeHintCache()
_json_pool = JSONParserPool()


@functools.lru_cache(maxsize=1000)
def _parse_complex_type_cached(value: Any, field_type_key: str) -> Any:
    """
    Cached version of complex type parsing

    Args:
        value: The raw value from query parameters
        field_type_key: String representation of field type for caching

    Returns:
        Parsed value or original value
    """
    if not isinstance(value, str):
        return value

    # Parse the field type from the key (simple reconstruction)
    # In practice, you'd want to store more type information
    if (
        "list" in field_type_key
        or field_type_key == "list"
        or "dict" in field_type_key
        or field_type_key == "dict"
    ):
        try:
            parser = _json_pool.get_parser()
            result = parser.decode(value)
            _json_pool.return_parser(parser)
            return result
        except (json.JSONDecodeError, ValueError, AttributeError):
            return value

    return value


def _get_type_key(field_type: Type) -> str:
    """Generate a cacheable key for field type"""
    origin = get_origin(field_type)
    if origin:
        args = get_args(field_type)
        return f"{origin.__name__}_{len(args)}"
    return getattr(field_type, "__name__", str(field_type))


async def _parse_complex_type_async(value: Any, field_type: Type) -> Any:
    """
    Async version of complex type parsing with batch processing

    Args:
        value: The raw value
        field_type: Expected field type

    Returns:
        Parsed value
    """
    # In a real implementation, you might batch JSON parsing operations
    # For now, just use the cached synchronous version
    return _parse_complex_type_cached(value, _get_type_key(field_type))


class OptimizedQueryParamProcessor:
    """High-performance query parameter processor"""

    def __init__(self, config: QueryParamConfig = None):
        self.config = config or QueryParamConfig()
        self._stats = {"cache_hits": 0, "cache_misses": 0, "parse_errors": 0, "total_requests": 0}

    def process_schema(self, schema: Type[BaseModel]) -> Dict[str, Any]:
        """
        Process schema with caching for better performance

        Returns:
            Dictionary with type hints, defaults, and metadata
        """
        self._stats["total_requests"] += 1

        # Try cache first
        if self.config.enable_cache:
            cached = _type_cache.get(schema)
            if cached:
                self._stats["cache_hits"] += 1
                return cached
            self._stats["cache_misses"] += 1

        # Process schema
        type_hints = get_type_hints(schema)
        model_fields = schema.model_fields

        # Pre-calculate defaults and descriptions
        defaults = {}
        for field_name, field_info in model_fields.items():
            description = (
                getattr(field_info, "description", None) or f"Query parameter: {field_name}"
            )

            if field_info.default is not None and field_info.default != ...:
                defaults[field_name] = Query(default=field_info.default, description=description)
            elif getattr(field_info, "default_factory", None) is not None:
                defaults[field_name] = Query(
                    default_factory=field_info.default_factory, description=description
                )
            else:
                defaults[field_name] = Query(..., description=description)

        result = {"type_hints": type_hints, "defaults": defaults, "model_fields": model_fields}

        # Cache result
        if self.config.enable_cache:
            _type_cache.set(schema, result)

        return result

    async def process_params(
        self, schema: Type[BaseModel], query_params: Dict[str, Any]
    ) -> BaseModel:
        """
        Process query parameters with optimized parsing

        Args:
            schema: Pydantic model schema
            query_params: Raw query parameters

        Returns:
            Validated Pydantic model instance
        """
        try:
            # Direct validation first (fast path)
            return schema(**query_params)
        except ValidationError:
            # Fallback to complex type parsing
            schema_info = self.process_schema(schema)
            type_hints = schema_info["type_hints"]

            parsed_params = {}
            parse_tasks = []

            # Prepare parsing tasks for async processing
            for field_name, value in query_params.items():
                if field_name in type_hints:
                    field_type = type_hints[field_name]

                    if self.config.enable_async_parsing:
                        # Batch async parsing
                        parse_tasks.append(
                            (field_name, _parse_complex_type_async(value, field_type))
                        )
                    else:
                        # Synchronous cached parsing
                        type_key = _get_type_key(field_type)
                        parsed_params[field_name] = _parse_complex_type_cached(value, type_key)
                else:
                    parsed_params[field_name] = value

            # Execute async tasks if enabled
            if self.config.enable_async_parsing and parse_tasks:
                # Batch process with limited concurrency
                for i in range(0, len(parse_tasks), self.config.batch_size):
                    batch = parse_tasks[i : i + self.config.batch_size]
                    for field_name, coro in batch:
                        try:
                            result = await coro
                            parsed_params[field_name] = result
                        except Exception:
                            self._stats["parse_errors"] += 1
                            parsed_params[field_name] = query_params[field_name]

            # Final validation
            try:
                return schema(**parsed_params)
            except ValidationError as e:
                # If still fails, raise original error for better error messages
                raise e

    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics"""
        total = self._stats["total_requests"]
        return {
            **self._stats,
            "cache_hit_rate": (self._stats["cache_hits"] / max(1, total) * 100),
            "type_cache_size": len(_type_cache._cache),
            "json_pool_size": len(_json_pool._pool),
        }


# Global processor instance
_processor = OptimizedQueryParamProcessor()


def QueryParamsOptimized(schema: Type[BaseModel]) -> Callable:
    """
    Optimized QueryParams decorator with caching and performance improvements

    Args:
        schema: Pydantic model class

    Returns:
        Optimized dependency function
    """
    # Process schema once and cache
    schema_info = _processor.process_schema(schema)
    type_hints = schema_info["type_hints"]
    defaults = schema_info["defaults"]

    async def dependency(**query_params: Any) -> BaseModel:
        """Optimized dependency with async processing"""
        return await _processor.process_params(schema, query_params)

    # Set function metadata
    dependency.__defaults__ = tuple(defaults.values())
    dependency.__annotations__ = {**type_hints, "return": schema}
    dependency._schema_info = schema_info  # For debugging

    return dependency


def as_query_params_optimized(schema: Type[BaseModel]) -> Callable:
    """
    Alternative optimized query parameter dependency

    Args:
        schema: Pydantic model class

    Returns:
        Optimized dependency function
    """
    schema_info = _processor.process_schema(schema)
    type_hints = schema_info["type_hints"]
    model_fields = schema_info["model_fields"]

    async def query_dependency(**kwargs: Any) -> BaseModel:
        """Optimized query dependency"""
        return await _processor.process_params(schema, kwargs)

    # Set annotations for each field
    for field_name, field_info in model_fields.items():
        field_type = type_hints.get(field_name, Any)
        description = getattr(field_info, "description", None) or f"Query parameter: {field_name}"

        query_dependency.__annotations__[field_name] = field_type

        if field_info.default is not None and field_info.default != ...:
            setattr(
                query_dependency,
                field_name,
                Query(default=field_info.default, description=description),
            )
        else:
            setattr(query_dependency, field_name, Query(..., description=description))

    query_dependency.__annotations__["return"] = schema
    query_dependency._schema_info = schema_info

    return query_dependency


def get_query_param_stats() -> Dict[str, Any]:
    """Get query parameter processing statistics"""
    return _processor.get_stats()


def clear_query_param_cache():
    """Clear all query parameter caches"""
    global _type_cache, _json_pool, _processor

    _type_cache._cache.clear()
    _type_cache._access_times.clear()
    _json_pool._pool.clear()
    _processor._stats = {"cache_hits": 0, "cache_misses": 0, "parse_errors": 0, "total_requests": 0}


# Example usage with performance monitoring
if __name__ == "__main__":

    import uvicorn
    from fastapi import FastAPI

    app = FastAPI()

    class UserQuery(BaseModel):
        name: str
        age: int = None
        tags: list = []
        metadata: dict = {}

        model_config = {
            "json_schema_extra": {
                "example": {
                    "name": "John",
                    "age": 30,
                    "tags": ["admin", "user"],
                    "metadata": {"source": "web"},
                }
            }
        }

    @app.get("/users/")
    async def get_users(params: UserQuery = Depends(as_query_params_optimized(UserQuery))):
        """Optimized endpoint with query parameter processing"""
        return {"message": f"Searching for users: {params.name}", "stats": get_query_param_stats()}

    @app.get("/stats/")
    async def get_stats():
        """Get query parameter processing statistics"""
        return get_query_param_stats()

    if __name__ == "__main__":
        uvicorn.run(app, host="0.0.0.0", port=8000)
