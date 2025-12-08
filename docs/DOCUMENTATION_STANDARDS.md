# Documentation Standards and Guidelines

## Overview

This document defines the documentation standards for FastAPI-Easy project to ensure consistency, clarity, and maintainability across all code and documentation.

## Docstring Standards

### Style Guide

We use **Google Style** docstrings with NumPy-style type annotations. This format was chosen for its:
- Excellent readability in source code
- Good parsing support by documentation tools
- Clean separation of sections
- Wide industry adoption

### Docstring Template

```python
def example_function(param1: str, param2: Optional[int] = None) -> bool:
    """Brief one-line description of the function.

    Extended description spanning multiple lines if needed. Explain the
    purpose, behavior, and any important considerations.

    Args:
        param1: Description of the first parameter.
        param2: Description of the second parameter. Defaults to None.

    Returns:
        Description of the return value.

    Raises:
        ValueError: If param1 is invalid.
        TypeError: If param2 is not an int when provided.

    Example:
        >>> result = example_function("test", 42)
        >>> print(result)
        True

    Note:
        Additional notes about the function's behavior, side effects,
        or implementation details.

    See Also:
        related_function: Related function that might be useful.
    """
```

### Class Documentation Template

```python
class ExampleClass:
    """Brief description of the class.

    Extended description explaining the class's purpose, responsibilities,
    and usage patterns.

    Attributes:
        attr1: Description of attribute 1.
        attr2: Description of attribute 2.

    Example:
        >>> obj = ExampleClass(attr1="value")
        >>> obj.method()
        'result'

    Note:
        Important notes about class usage or implementation.
    """

    def __init__(self, attr1: str, attr2: Optional[int] = None):
        """Initialize ExampleClass.

        Args:
            attr1: Description of attribute 1.
            attr2: Description of attribute 2. Defaults to None.
        """
```

## Documentation Requirements

### 1. Public API Documentation
- All public classes, functions, and methods MUST have complete docstrings
- Include type hints for all parameters and return values
- Provide usage examples for complex APIs
- Document all exceptions that can be raised

### 2. Internal Code Documentation
- Private methods (starting with `_`) should have brief docstrings
- Complex algorithms need inline comments explaining the logic
- Non-obvious business logic should be documented

### 3. Module Documentation
Each module should have a module-level docstring that includes:
- Brief description of module purpose
- Main classes and functions provided
- Usage example if applicable
- Any important considerations or dependencies

## Inline Comments

### When to Add Comments
1. **Complex Logic**: When the code is not immediately obvious
2. **Business Rules**: When implementing specific business requirements
3. **Workarounds**: When working around known issues
4. **Performance Critical**: When explaining optimization choices
5. **Security Considerations**: When explaining security-related code

### Comment Style
```python
# Use inline comments for brief explanations
result = complex_calculation(data)  # Transforms data for API compatibility

# Use block comments for detailed explanations
# This section handles the special case where users have multiple
# active sessions. We need to merge their permissions to ensure
# consistent access control across all sessions.
if user_sessions > 1:
    merge_permissions(user)
```

## Type Hints

All code must use Python type hints following PEP 484:
- Use standard library types when possible
- Import typing constructs from `typing` module
- Use `Optional[T]` for nullable values
- Use `Union[T, U]` for multiple types
- Use `Literal[T]` for enumerated string values

```python
from typing import Optional, Union, Literal, Dict, List, Any
from typing_extensions import TypedDict

Status = Literal["active", "inactive", "pending"]

class UserData(TypedDict):
    """Type definition for user data."""
    id: int
    name: str
    status: Status

def process_user(user: UserData, flags: Optional[List[str]] = None) -> Dict[str, Any]:
    """Process user data with optional flags."""
```

## Example Documentation

### API Endpoint Documentation
```python
@router.post("/users/", response_model=UserResponse)
async def create_user(
    user: UserCreate,
    *,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Create a new user in the system.

    This endpoint creates a new user with the provided data. The user
    making the request must have admin privileges.

    Args:
        user: User creation data with all required fields.
        db: Database session dependency.
        current_user: Currently authenticated user (must be admin).

    Returns:
        UserResponse: The created user data with assigned ID.

    Raises:
        HTTPException: 403 if user lacks admin privileges.
        HTTPException: 409 if user with email already exists.
        ValidationError: If provided data is invalid.

    Example:
        >>> user_data = UserCreate(email="user@example.com", name="John Doe")
        >>> response = await create_user(user_data, db=session, current_user=admin)
        >>> print(response.id)
        123
    """
```

## Documentation Quality Checklist

Before submitting code, verify:
- [ ] All public functions/classes have complete docstrings
- [ ] Type hints are present and correct
- [ ] Examples work and are tested
- [ ] Edge cases are documented
- [ ] Error conditions are documented
- [ ] Performance implications are noted
- [ ] Security considerations are documented
- [ ] Dependencies are clearly stated

## Tools and Validation

### Automated Checks
- **pydocstyle**: Enforces docstring style compliance
- **mypy**: Validates type hints
- **sphinx**: Generates documentation from docstrings
- **black**: Ensures consistent formatting

### Manual Review Process
1. Code review includes documentation verification
2. Documentation is updated with API changes
3. Examples are tested in CI/CD pipeline
4. Documentation is rendered and reviewed

## API Documentation Generation

### Sphinx Configuration
We use Sphinx with the following extensions:
- `sphinx.ext.autodoc`: Automatic documentation from docstrings
- `sphinx.ext.viewcode`: Add source code links
- `sphinx.ext.napoleon`: Google/NumPy style docstrings
- `sphinx.ext.intersphinx`: Link to other projects' docs

### Documentation Build
```bash
# Build documentation locally
cd docs
make html

# Check for docstring coverage
sphinx-apidoc -o docs/source src/fastapi_easy
```

## Best Practices

### 1. Writing Good Descriptions
- Start with a verb for functions (e.g., "Create", "Calculate", "Validate")
- Use present tense for class descriptions
- Be concise but complete
- Avoid implementation details in user-facing documentation

### 2. Providing Examples
- Keep examples simple and focused
- Use `>>>` for doctest examples
- Include edge cases in examples when helpful
- Test all examples in CI/CD

### 3. Error Documentation
- Document all possible exceptions
- Group related exceptions
- Explain the cause of each error
- Suggest resolution when applicable

### 4. Version Compatibility
- Document version-specific behavior
- Use `.. versionadded::` for new features
- Use `.. deprecated::` for deprecated features
- Provide migration paths for breaking changes

## Maintenance

### Regular Tasks
- Update documentation with code changes
- Review and improve existing documentation
- Check for broken links and outdated examples
- Validate type hint coverage

### Metrics to Track
- Documentation coverage percentage
- Number of examples in docstrings
- Broken documentation links
- Type hint compliance rate