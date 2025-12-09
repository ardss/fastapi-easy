# Type Annotation Guidelines for FastAPI-Easy

This document provides comprehensive guidelines for type annotations in the FastAPI-Easy project to ensure consistent typing practices and improve code quality.

## Table of Contents

1. [Core Principles](#core-principles)
2. [Common Patterns](#common-patterns)
3. [Generic Types](#generic-types)
4. [Async/Await Patterns](#asyncawait-patterns)
5. [Error Handling Types](#error-handling-types)
6. [Configuration Types](#configuration-types)
7. [Testing Types](#testing-types)
8. [Migration Guide](#migration-guide)

## Core Principles

### 1. Always Use Return Type Annotations

Every function and method must have a return type annotation:

```python
# ❌ Bad
def process_data(data):
    return data.upper()

def setup():
    pass

# ✅ Good
def process_data(data: str) -> str:
    return data.upper()

def setup() -> None:
    pass
```

### 2. Use Specific Types Over Any

Prefer specific types over `Any` when possible:

```python
# ❌ Bad
def get_config(key: str) -> Any:
    return config[key]

# ✅ Good
def get_config(key: str) -> Union[str, int, bool, Dict[str, Any]]:
    return config[key]

# Even better - use ConfigValue from _types
def get_config(key: str) -> ConfigValue:
    return config[key]
```

### 3. Optional Types Must Be Explicit

When a value can be None, use Optional explicitly:

```python
# ❌ Bad
def get_user(id: int):
    # Might return None
    return db.get_user(id)

# ✅ Good
def get_user(id: int) -> Optional[User]:
    # Explicitly states it can return None
    return db.get_user(id)
```

## Common Patterns

### Function Definitions

```python
# Standard function
def function_name(param1: str, param2: int) -> bool:
    return param1 * param2 > 0

# Function with optional parameters
def function_name(param: str, optional: Optional[str] = None) -> None:
    if optional:
        print(optional)

# Function with variable arguments
def function_name(*args: str, **kwargs: Any) -> Dict[str, Any]:
    return {"args": args, "kwargs": kwargs}

# Function returning multiple values
def function_name() -> Tuple[str, int, bool]:
    return "result", 42, True
```

### Class Methods

```python
class MyClass:
    # Instance method
    def method(self, param: str) -> str:
        return param.upper()

    # Class method
    @classmethod
    def class_method(cls, param: int) -> int:
        return param * 2

    # Static method
    @staticmethod
    def static_method(param: bool) -> bool:
        return not param

    # Property
    @property
    def computed_value(self) -> float:
        return self._value * 1.5

    # Setter
    @computed_value.setter
    def computed_value(self, value: float) -> None:
        self._value = value
```

## Generic Types

### Using TypeVar

```python
from typing import TypeVar, Generic, List

T = TypeVar('T')

class Container(Generic[T]):
    def __init__(self) -> None:
        self._items: List[T] = []

    def add(self, item: T) -> None:
        self._items.append(item)

    def get_all(self) -> List[T]:
        return self._items.copy()

# Usage
string_container = Container[str]()
int_container = Container[int]()
```

### Bound TypeVars

```python
from typing import TypeVar, Protocol

class SupportsStr(Protocol):
    def __str__(self) -> str: ...

T_Str = TypeVar('T_Str', bound=SupportsStr)

def display(item: T_Str) -> str:
    return str(item)
```

## Async/Await Patterns

### Async Function Return Types

```python
# Async function returning a value
async def fetch_data(url: str) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        return await client.get(url).json()

# Async function returning optional
async def find_user(email: str) -> Optional[User]:
    return await db.find_user(email)

# Async function with no return
async def process_queue() -> None:
    while True:
        item = await queue.get()
        await process_item(item)

# Async context manager
async def database_transaction() -> AsyncIterator[Connection]:
    async with connection.begin():
        yield connection
```

### Callable Types

```python
from typing import Callable, Awaitable

# Sync callback
def add_callback(callback: Callable[[str], None]) -> None:
    callback("Hello")

# Async callback
def add_async_callback(callback: Callable[[str], Awaitable[None]]) -> None:
    await callback("Hello")
```

## Error Handling Types

### Exception Types

```python
from typing import Type

def with_error_handling(
    func: Callable[[], T],
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Tuple[Optional[T], Optional[Exception]]:
    try:
        return func(), None
    except exceptions as e:
        return None, e
```

### Result Types

```python
from typing import Union
from dataclasses import dataclass

@dataclass
class Success[T]:
    value: T

@dataclass
class Error:
    message: str
    exception: Optional[Exception] = None

Result[T] = Union[Success[T], Error]

def safe_divide(a: float, b: float) -> Result[float]:
    if b == 0:
        return Error("Division by zero")
    return Success(a / b)
```

## Configuration Types

### Configuration Values

```python
from typing import Literal, Union
from enum import Enum

ConfigValue = Union[str, int, float, bool, List[str], Dict[str, Any]]

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

class DatabaseBackend(Enum):
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"

@dataclass
class DatabaseConfig:
    backend: DatabaseBackend
    host: str
    port: int
    database: str
    username: str
    password: Optional[str] = None
    pool_size: int = 10
```

## Testing Types

### Test Fixtures

```python
from typing import Generator, AsyncGenerator
import pytest

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Mock Types

```python
from unittest.mock import Mock
from typing import Any

def create_mock_repository() -> Mock:
    mock = Mock(spec=IRepository)
    mock.get_by_id.return_value = None
    return mock
```

## Migration Guide

### Step 1: Add Return Types

For each function without a return type:

1. Identify if it returns something: Use appropriate type
2. If it returns None: Add `-> None`
3. If it might return None: Use `Optional[T]`

### Step 2: Fix Generic Types

Replace generic types with parameterized ones:

```python
# Before
data: Dict = {}
items: List = []

# After
data: Dict[str, Any] = {}
items: List[str] = []
```

### Step 3: Handle Untyped Imports

For libraries without type stubs:

1. Add to `mypy` overrides in `pyproject.toml`
2. Use `# type: ignore` for specific problematic lines
3. Consider adding stub packages if available

### Step 4: Fix Async/Await

Ensure all async functions have proper return types:

```python
# Before
async def process(data):
    return await some_operation(data)

# After
async def process(data: str) -> ProcessedData:
    return await some_operation(data)
```

## Best Practices

### 1. Import Organization

```python
# Standard library first
from typing import Any, Dict, List, Optional
from collections import defaultdict
from datetime import datetime

# Third-party libraries
from fastapi import FastAPI
from pydantic import BaseModel

# Local imports
from .core._types import ConfigValue
from .utils import helper_function
```

### 2. Type Aliases

Create descriptive type aliases for complex types:

```python
from typing import Dict, List, Optional

UserInfo = Dict[str, Any]
MetricData = List[Dict[str, Union[str, int, float]]]
ConfigSection = Optional[Dict[str, ConfigValue]]
```

### 3. Protocol Usage

Use protocols for duck typing:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SupportsClose(Protocol):
    def close(self) -> None: ...

def close_resource(resource: SupportsClose) -> None:
    resource.close()
```

### 4. Overloads

Use overloads for functions with different signatures:

```python
from typing import overload, Union

@overload
def process(data: str) -> str: ...
@overload
def process(data: int) -> int: ...

def process(data: Union[str, int]) -> Union[str, int]:
    return str(data) if isinstance(data, int) else data.upper()
```

## Tools and Automation

### MyPy Configuration

Ensure your `pyproject.toml` has strict MyPy configuration:

```toml
[tool.mypy]
python_version = "3.9"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
disallow_subclassing_any = true
disallow_untyped_calls = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true
```

### Pre-commit Hooks

Add type checking to pre-commit hooks:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: mypy
        language: system
        types: [python]
        require_serial: true
        args: [--config-file=pyproject.toml]
```

### IDE Integration

Configure your IDE to:
- Show type hints
- Highlight untyped functions
- Enable MyPy integration
- Use stubs when available

This comprehensive guide should help maintain consistent and high-quality type annotations throughout the FastAPI-Easy project.