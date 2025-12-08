# FastAPI-Easy Error Handling Guide

This guide provides comprehensive documentation for the FastAPI-Easy error handling system.

## Overview

The FastAPI-Easy error handling system provides:

- **Structured Exception Hierarchy**: Comprehensive exception classes for different error types
- **Error Context Tracking**: Detailed context information for debugging and monitoring
- **Consistent Error Responses**: Standardized API error responses with multiple formats
- **Error Recovery**: Retry and fallback strategies for resilient applications
- **Integration Ready**: Easy integration with FastAPI applications via middleware

## Quick Start

```python
from fastapi import FastAPI
from fastapi_easy.core.exceptions import (
    add_error_middleware,
    DatabaseException,
    ValidationError,
)
from fastapi_easy.core.exceptions.middleware import ResponseFormat

app = FastAPI()

# Add error handling middleware
add_error_middleware(
    app,
    response_format=ResponseFormat.STANDARD,
    security_headers=True,
)

# Use custom exceptions
@app.get("/users/{user_id}")
async def get_user(user_id: str):
    try:
        user = await get_user_from_db(user_id)
        if not user:
            raise NotFoundError(
                resource="User",
                identifier=user_id,
            )
        return user
    except DatabaseException:
        # Handled by middleware
        raise
```

## Key Features

### 1. Exception Hierarchy
- Base: `FastAPIEasyException`
- Database: `DatabaseException`, `DatabaseConnectionException`, etc.
- Authentication: `AuthenticationException`, `TokenExpiredException`, etc.
- Validation: `ValidationException`, `FieldValidationException`, etc.
- Migration: `MigrationException`, `MigrationExecutionException`, etc.

### 2. Error Context
```python
from fastapi_easy.core.exceptions import ErrorContext

context = ErrorContext(
    request_id="req-123",
    user_id="user-456",
    endpoint="/api/users",
    method="POST",
    resource="users",
    action="create",
)
```

### 3. Response Formats
- **Standard**: Detailed error with context
- **Minimal**: Production-safe basic errors
- **Development**: Includes stack traces and debug info
- **API Problem**: RFC 7807 compliant format

### 4. Error Recovery
```python
from fastapi_easy.core.exceptions.handlers import ErrorHandler, RetryConfig

handler = ErrorHandler()
handler.configure_retry(
    DatabaseException,
    RetryConfig(max_attempts=3, base_delay=1.0)
)
```

## Migration Guide

### Step 1: Add Middleware
```python
from fastapi_easy.core.exceptions.middleware import add_error_middleware

add_error_middleware(app)
```

### Step 2: Replace HTTPException
```python
# Before
raise HTTPException(status_code=404, detail="User not found")

# After
raise NotFoundError(resource="User", identifier=user_id)
```

### Step 3: Add Context
```python
exception.with_context(
    user_id=current_user.id,
    operation="get_user",
)
```

## Best Practices

1. Use specific exception types
2. Include actionable error messages
3. Add context information
4. Use appropriate severity levels
5. Implement retry for transient errors
6. Sanitize errors in production

## Example Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "status": 422,
    "category": "validation",
    "context": {
      "request_id": "req-123",
      "correlation_id": "corr-456"
    },
    "details": {
      "field": "email",
      "suggestion": "Please provide a valid email address"
    }
  }
}
```
