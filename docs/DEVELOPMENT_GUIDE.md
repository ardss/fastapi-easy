# FastAPI-Easy Development Guide

## Table of Contents

1. [Documentation Standards](#documentation-standards)
2. [Code Quality Requirements](#code-quality-requirements)
3. [Type Annotation Guidelines](#type-annotation-guidelines)
4. [Testing Guidelines](#testing-guidelines)
5. [Development Workflow](#development-workflow)
6. [ contributing Guidelines](#contributing-guidelines)

## Documentation Standards

### Google Style Docstrings

All Python modules, classes, and functions must follow Google Style docstring format:

```python
def function(param: Type) -> ReturnType:
    """Brief description of the function.

    Longer description if needed. Explain the purpose, behavior, and
    any important details about the function.

    Args:
        param: Description of the parameter
        optional_param: Description of optional parameter (default: value)

    Returns:
        Description of the return value

    Raises:
        ErrorType: When the error occurs
        AnotherError: Another error condition

    Example:
        ```python
        # Show usage example
        result = function(value)
        print(result)
        ```
    """
```

### Module Documentation

Every module must have a comprehensive module-level docstring that includes:

- Clear description of the module's purpose
- Main features and capabilities
- Example usage
- Important notes or considerations

```python
"""Module description.

This module provides functionality for...
It includes these main features:
- Feature 1
- Feature 2
- Feature 3

Example:
    ```python
    from fastapi_easy import Component

    component = Component()
    result = await component.process()
    ```
"""
```

### Class Documentation

Classes must document their purpose, attributes, and provide usage examples:

```python
class ExampleClass:
    """Brief description of the class.

    Detailed description of the class purpose and behavior.
    Explain the main use cases and design patterns.

    Attributes:
        attr1: Description of first attribute
        attr2: Description of second attribute (Type)

    Example:
        ```python
        # Show class usage
        instance = ExampleClass(attr1="value")
        result = instance.method()
        ```
    """
```

## Code Quality Requirements

### Type Annotations

- Use modern type hints (`list` instead of `List`, `dict` instead of `Dict`)
- Use `|` for union types (`str | int` instead of `Union[str, int]`)
- Import runtime-dependent types inside `TYPE_CHECKING` blocks
- Use generic type variables where appropriate

```python
# Good
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List, Optional, Type
    from pydantic import BaseModel

def process_data(items: list[str]) -> dict[str, int]:
    return {"count": len(items)}

# Bad
from typing import List, Dict, Union

def process_data(items: List[str]) -> Dict[str, int]:
    return {"count": len(items)}
```

### Import Organization

Follow the import order:
1. Standard library imports
2. Third-party imports
3. Local imports (from fastapi_easy)

Use `isort` to maintain consistent import ordering.

### Error Handling

- Use specific exception types
- Include meaningful error messages
- Handle exceptions appropriately
- Use the custom exception classes from `fastapi_easy.core.exceptions`

```python
# Good
try:
    result = await database_operation()
except DatabaseConnectionException as e:
    logger.error(f"Database connection failed: {e}")
    raise FastAPIEasyException("Unable to connect to database") from e

# Bad
try:
    result = await database_operation()
except Exception as e:
    print("Error")
```

## Type Annotation Guidelines

### Type Checking

Run type checking with mypy:

```bash
python -m mypy src/fastapi_easy/core/ --ignore-missing-imports
```

### Common Patterns

```python
# Optional parameters
def func(param: str | None = None) -> None:
    pass

# Generic classes
class Repository(Generic[T]):
    def get_by_id(self, id: int) -> T | None:
        pass

# Callable types
Handler = Callable[[str], Awaitable[None]]

# Protocol for duck typing
class SupportsClose(Protocol):
    def close(self) -> None: ...
```

### Configuration

Configure mypy in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.9"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

## Testing Guidelines

### Test Structure

- Unit tests for individual functions/classes
- Integration tests for component interactions
- End-to-end tests for complete workflows
- Performance tests for critical paths

### Test Documentation

Each test file must have a docstring explaining what's being tested:

```python
"""Test cases for the CRUD router module.

Tests cover:
- Route generation
- Parameter validation
- Response serialization
- Error handling
"""
```

### Test Naming

Use descriptive test names:

```python
# Good
async def test_crud_router_rejects_invalid_schema():
    pass

async def test_get_all_returns_paginated_results():
    pass

# Bad
async def test_router_1():
    pass

async def test_basic():
    pass
```

## Development Workflow

### 1. Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/ardss/fastapi-easy.git
cd fastapi-easy

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install development dependencies
pip install -e ".[dev]"
```

### 2. Make Changes

1. Create a feature branch
2. Write code following the standards
3. Add comprehensive docstrings
4. Write tests for new functionality

### 3. Quality Checks

```bash
# Run linting
python -m ruff check src/ --fix

# Run type checking
python -m mypy src/

# Run tests
python -m pytest tests/

# Check documentation style
python -m pydocstyle src/
```

### 4. Submit Changes

1. Commit changes with descriptive messages
2. Push to your fork
3. Create a pull request
4. Address any feedback

## Contributing Guidelines

### Pull Request Requirements

- [ ] All tests pass
- [ ] Code coverage meets minimum threshold (85%)
- [ ] No linting errors
- [ ] No type checking errors
- [ ] Documentation updated
- [ ] CHANGELOG updated for significant changes

### Code Review Process

1. Automated checks must pass
2. At least one maintainer review required
3. Address all review comments
4. Squash commits if needed
5. Merge to main branch

### Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create git tag
4. Build and publish to PyPI

## Resources

- [Google Style Python Docstrings](https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Ruff Linter](https://github.com/charliermarsh/ruff)
- [MyPy Type Checker](https://mypy.readthedocs.io/)