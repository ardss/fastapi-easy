"""
Optimized Import Management for FastAPI-Easy

Centralized import management to:
- Reduce circular import issues
- Optimize import loading times
- Provide lazy loading capabilities
- Group related imports
- Ensure consistent import patterns
"""

from __future__ import annotations

import importlib
import inspect
import logging
import sys
import time
import asyncio
from types import ModuleType
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

# Lazy import registry
_LAZY_IMPORTS: Dict[str, "LazyLoader"] = {}
_IMPORTED_MODULES: Dict[str, float] = {}

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ImportStats:
    """Import performance statistics"""

    module_name: str
    load_time: float
    size: int
    dependencies: int


class LazyLoader:
    """Lazy loader for delayed imports"""

    def __init__(self, module_path: str, item_name: Optional[str] = None):
        self.module_path = module_path
        self.item_name = item_name
        self._module: Optional[ModuleType] = None
        self._item: Optional[Any] = None

    def __getattr__(self, name: str) -> Any:
        if self._item is None:
            self._load()
        return getattr(self._item, name) if self._item else getattr(self._module, name)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        if self._item is None:
            self._load()
        return self._item(*args, **kwargs) if self._item else self._module

    def _load(self) -> None:
        """Perform the actual import"""
        if self._module is None:
            start_time = time.perf_counter()
            self._module = importlib.import_module(self.module_path)
            load_time = time.perf_counter() - start_time

            _IMPORTED_MODULES[self.module_path] = load_time

            if self.item_name:
                self._item = getattr(self._module, self.item_name)

    def __repr__(self) -> str:
        if self._item is None:
            return f"<LazyLoader {self.module_path}::{self.item_name}>"
        return repr(self._item)


def lazy_import(module_path: str, item_name: Optional[str] = None) -> Union[LazyLoader, Any]:
    """
    Create a lazy import that loads the module/item only when first accessed.

    Args:
        module_path: Full module path (e.g., 'fastapi_easy.backends.sqlalchemy')
        item_name: Specific item to import from module (optional)

    Returns:
        Lazy loader instance or the actual item if already loaded
    """
    if module_path in sys.modules:
        # Module already loaded
        module = sys.modules[module_path]
        if item_name:
            return getattr(module, item_name)
        return module

    # Create lazy loader
    key = f"{module_path}::{item_name}" if item_name else module_path
    if key not in _LAZY_IMPORTS:
        _LAZY_IMPORTS[key] = LazyLoader(module_path, item_name)

    return _LAZY_IMPORTS[key]


# Common lazy imports used throughout the project
SQLAlchemyAdapter = lazy_import("fastapi_easy.backends.sqlalchemy", "SQLAlchemyAdapter")
SQLModelAdapter = lazy_import("fastapi_easy.backends.sqlmodel", "SQLModelAdapter")
TortoiseAdapter = lazy_import("fastapi_easy.backends.tortoise", "TortoiseAdapter")
MongoAdapter = lazy_import("fastapi_easy.backends.mongo", "MongoAdapter")

CRUDRouter = lazy_import("fastapi_easy.core.crud_router", "CRUDRouter")
OptimizedCRUDRouter = lazy_import("fastapi_easy.core.optimized_crud_router", "OptimizedCRUDRouter")

BaseError = lazy_import("fastapi_easy.core.optimized_errors", "BaseError")
ValidationError = lazy_import("fastapi_easy.core.optimized_errors", "ValidationError")
NotFoundError = lazy_import("fastapi_easy.core.optimized_errors", "NotFoundError")

OptimizedDatabaseManager = lazy_import(
    "fastapi_easy.core.optimized_database", "OptimizedDatabaseManager"
)
QueryCache = lazy_import("fastapi_easy.core.optimized_database", "QueryCache")

AppSettings = lazy_import("fastapi_easy.core.settings", "AppSettings")
DatabaseConfig = lazy_import("fastapi_easy.core.settings", "DatabaseConfig")
SecurityConfig = lazy_import("fastapi_easy.core.settings", "SecurityConfig")


@lru_cache(maxsize=128)
def get_import_path(obj: Any) -> str:
    """
    Get the full import path for an object.

    Args:
        obj: Object to get import path for

    Returns:
        Full import path string
    """
    if inspect.ismodule(obj):
        return obj.__name__
    elif inspect.isclass(obj) or inspect.isfunction(obj):
        module = inspect.getmodule(obj)
        if module:
            return f"{module.__name__}.{obj.__name__}"
    return str(obj)


def conditional_import(condition: bool, module_path: str, item_name: Optional[str] = None) -> Optional[Union[ModuleType, Any]]:
    """
    Conditionally import a module/item.

    Args:
        condition: Whether to perform the import
        module_path: Module path to import
        item_name: Specific item to import (optional)

    Returns:
        Imported item or None if condition is False
    """
    if condition:
        if item_name:
            module = importlib.import_module(module_path)
            return getattr(module, item_name)
        return importlib.import_module(module_path)
    return None


def try_import(module_path: str, item_name: Optional[str] = None, default: Any = None) -> Any:
    """
    Try to import a module/item, return default on failure.

    Args:
        module_path: Module path to import
        item_name: Specific item to import (optional)
        default: Default value to return on failure

    Returns:
        Imported item or default value
    """
    try:
        if item_name:
            module = importlib.import_module(module_path)
            return getattr(module, item_name)
        return importlib.import_module(module_path)
    except (ImportError, AttributeError):
        return default


class ImportProfiler:
    """Profile import performance"""

    def __init__(self) -> None:
        self.imports: Dict[str, ImportStats] = {}

    def profile_import(self, module_path: str) -> ImportStats:
        """
        Profile the import of a specific module.

        Args:
            module_path: Module to profile

        Returns:
            Import statistics
        """
        # Force reload if already imported
        if module_path in sys.modules:
            del sys.modules[module_path]

        start_time = time.perf_counter()
        module = importlib.import_module(module_path)
        load_time = time.perf_counter() - start_time

        # Calculate module size (approximate)
        size = 0
        dependencies = 0

        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if inspect.ismodule(attr):
                dependencies += 1
            elif hasattr(attr, "__code__"):
                size += len(attr.__code__.co_code)

        stats = ImportStats(
            module_name=module_path, load_time=load_time, size=size, dependencies=dependencies
        )

        self.imports[module_path] = stats
        return stats

    def get_slow_imports(self, threshold: float = 0.1) -> list[ImportStats]:
        """
        Get imports slower than threshold.

        Args:
            threshold: Time threshold in seconds

        Returns:
            List of slow imports
        """
        return [stats for stats in self.imports.values() if stats.load_time > threshold]

    def get_summary(self) -> Dict[str, Any]:
        """
        Get import performance summary.

        Returns:
            Summary dictionary
        """
        if not self.imports:
            return {}

        total_time = sum(stats.load_time for stats in self.imports.values())
        total_size = sum(stats.size for stats in self.imports.values())
        total_deps = sum(stats.dependencies for stats in self.imports.values())

        return {
            "total_imports": len(self.imports),
            "total_time": total_time,
            "avg_time": total_time / len(self.imports),
            "total_size": total_size,
            "total_dependencies": total_deps,
            "slowest": max(self.imports.values(), key=lambda s: s.load_time).module_name,
            "largest": max(self.imports.values(), key=lambda s: s.size).module_name,
        }


# Global import profiler
_import_profiler = ImportProfiler()


def get_import_profiler() -> ImportProfiler:
    """Get the global import profiler"""
    return _import_profiler


def optimize_imports() -> None:
    """
    Optimize imports by:
    1. Removing unused imports
    2. Consolidating related imports
    3. Moving imports to where they're needed
    """
    # This is a placeholder for import optimization logic
    # In practice, you might use tools like isort, autoflake, etc.
    pass


# Preload critical modules for better performance
def preload_modules(module_paths: list[str]) -> None:
    """
    Preload commonly used modules.

    Args:
        module_paths: List of module paths to preload
    """
    for module_path in module_paths:
        try:
            start_time = time.perf_counter()
            importlib.import_module(module_path)
            load_time = time.perf_counter() - start_time
            _IMPORTED_MODULES[module_path] = load_time
        except ImportError as e:
            logger.warning(f"Failed to preload {module_path}: {e}")


# Essential modules to preload
ESSENTIAL_MODULES = [
    "asyncio",
    "typing",
    "logging",
    "time",
    "json",
    "dataclasses",
    "contextlib",
    "functools",
    "pydantic",
    "fastapi",
    "sqlalchemy",
]


def preinitialize() -> None:
    """Preinitialize essential modules for faster startup"""
    preload_modules(ESSENTIAL_MODULES)


# Auto-initialize on import
preinitialize()


# Compatibility layer for older Python versions
def ensure_future(coro: Any) -> Any:
    """Ensure compatibility with different asyncio implementations"""
    try:
        return asyncio.ensure_future(coro)
    except AttributeError:
        return asyncio.create_task(coro)


# Optional imports with graceful fallback
def import_or_dummy(module_path: str, dummy_value: Any = None) -> Any:
    """
    Import module or return dummy value.

    Args:
        module_path: Module path to import
        dummy_value: Value to return if import fails

    Returns:
        Imported module or dummy value
    """
    try:
        return importlib.import_module(module_path)
    except ImportError:
        return dummy_value


# Specialized import helpers
def import_database_backend(backend_type: str) -> Any:
    """
    Import the appropriate database backend.

    Args:
        backend_type: Type of backend ('sqlalchemy', 'sqlmodel', 'tortoise', 'mongo')

    Returns:
        Backend adapter class
    """
    backends = {
        "sqlalchemy": "fastapi_easy.backends.sqlalchemy",
        "sqlmodel": "fastapi_easy.backends.sqlmodel",
        "tortoise": "fastapi_easy.backends.tortoise",
        "mongo": "fastapi_easy.backends.mongo",
    }

    module_path = backends.get(backend_type)
    if not module_path:
        raise ValueError(f"Unknown backend type: {backend_type}")

    module = importlib.import_module(module_path)
    return getattr(module, f"{backend_type.title()}Adapter")


def import_migration_engine(migration_type: str) -> Any:
    """
    Import the appropriate migration engine.

    Args:
        migration_type: Type of migration engine

    Returns:
        Migration engine class
    """
    # Implementation would depend on available migration engines
    return None


# Cache for imported items
class ImportCache:
    """Cache for frequently imported items"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key in self._cache:
            self._access_times[key] = time.time()
            return self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        """Set item in cache"""
        if len(self._cache) >= self.max_size:
            # Remove least recently used
            lru_key = min(self._access_times.keys(), key=lambda k: self._access_times.get(k, 0))
            del self._cache[lru_key]
            del self._access_times[lru_key]

        self._cache[key] = value
        self._access_times[key] = time.time()

    def clear(self) -> None:
        """Clear cache"""
        self._cache.clear()
        self._access_times.clear()


# Global import cache
_import_cache = ImportCache()


def get_import_cache() -> ImportCache:
    """Get the global import cache"""
    return _import_cache


def cached_import(module_path: str, item_name: Optional[str] = None) -> Any:
    """
    Import with caching.

    Args:
        module_path: Module path to import
        item_name: Specific item to import (optional)

    Returns:
        Imported item
    """
    cache_key = f"{module_path}::{item_name}" if item_name else module_path

    # Try cache first
    cached_item = _import_cache.get(cache_key)
    if cached_item is not None:
        return cached_item

    # Import and cache
    if item_name:
        module = importlib.import_module(module_path)
        item = getattr(module, item_name)
    else:
        item = importlib.import_module(module_path)

    _import_cache.set(cache_key, item)
    return item


# Export commonly used items
__all__ = [
    "ImportProfiler",
    "LazyLoader",
    "cached_import",
    "conditional_import",
    "ensure_future",
    "get_import_cache",
    "get_import_profiler",
    "import_database_backend",
    "import_or_dummy",
    "lazy_import",
    "preinitialize",
    "preload_modules",
    "try_import",
]

# Lazy exports for backward compatibility
__lazy_exports__ = {
    "SQLAlchemyAdapter": ("fastapi_easy.backends.sqlalchemy", "SQLAlchemyAdapter"),
    "SQLModelAdapter": ("fastapi_easy.backends.sqlmodel", "SQLModelAdapter"),
    "TortoiseAdapter": ("fastapi_easy.backends.tortoise", "TortoiseAdapter"),
    "MongoAdapter": ("fastapi_easy.backends.mongo", "MongoAdapter"),
    "CRUDRouter": ("fastapi_easy.core.crud_router", "CRUDRouter"),
    "OptimizedCRUDRouter": ("fastapi_easy.core.optimized_crud_router", "OptimizedCRUDRouter"),
    "BaseError": ("fastapi_easy.core.optimized_errors", "BaseError"),
    "ValidationError": ("fastapi_easy.core.optimized_errors", "ValidationError"),
    "NotFoundError": ("fastapi_easy.core.optimized_errors", "NotFoundError"),
    "OptimizedDatabaseManager": (
        "fastapi_easy.core.optimized_database",
        "OptimizedDatabaseManager",
    ),
    "AppSettings": ("fastapi_easy.core.settings", "AppSettings"),
    "DatabaseConfig": ("fastapi_easy.core.settings", "DatabaseConfig"),
    "SecurityConfig": ("fastapi_easy.core.settings", "SecurityConfig"),
}


def __getattr__(name: str) -> Any:
    """Handle lazy exports"""
    if name in __lazy_exports__:
        module_path, item_name = __lazy_exports__[name]
        return lazy_import(module_path, item_name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
