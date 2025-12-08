# Error Handling Migration Guide

This guide helps you migrate your existing FastAPI-Easy applications to use the new comprehensive error handling system.

## Migration Steps

### Phase 1: Add Error Middleware (Immediate)

Add the error handling middleware to your FastAPI application:

```python
# main.py
from fastapi import FastAPI
from fastapi_easy.core.exceptions.middleware import add_error_middleware, ResponseFormat

app = FastAPI()

# Add error handling middleware
add_error_middleware(
    app,
    response_format=ResponseFormat.STANDARD,  # Use DETAILED for development
    security_headers=True,
    monitor_errors=True,
)

# Your existing routes...
```

**Benefits**: Existing exceptions will be automatically caught and formatted consistently.

### Phase 2: Replace Common Exceptions (High Priority)

Update common error patterns to use new exception classes:

#### Database Errors

**Before:**
```python
try:
    result = await db.execute(query)
except Exception as e:
    logger.error(f"Database error: {e}")
    raise HTTPException(status_code=500, detail="Database error")
```

**After:**
```python
from fastapi_easy.core.exceptions import (
    DatabaseConnectionException,
    DatabaseQueryException,
)

try:
    result = await db.execute(query)
except ConnectionError as e:
    raise DatabaseConnectionException(
        database="mydb",
        original_error=e,
    ).with_context(operation="user_query")
except Exception as e:
    raise DatabaseQueryException(
        query=str(query),
        original_error=e,
    ).with_context(operation="user_query")
```

#### Not Found Errors

**Before:**
```python
user = await get_user(user_id)
if not user:
    raise HTTPException(
        status_code=404,
        detail=f"User {user_id} not found"
    )
```

**After:**
```python
from fastapi_easy.core.exceptions import NotFoundError

user = await get_user(user_id)
if not user:
    raise NotFoundError(
        resource="User",
        identifier=user_id,
    ).with_context(
        user_id=user_id,
        action="get_user",
    )
```

#### Validation Errors

**Before:**
```python
if not email_regex.match(email):
    raise HTTPException(
        status_code=422,
        detail="Invalid email format"
    )
```

**After:**
```python
from fastapi_easy.core.exceptions import FieldValidationException

if not email_regex.match(email):
    raise FieldValidationException(
        field="email",
        message="Invalid email format",
        value=email,
        expected_type="valid_email",
    )
```

### Phase 3: Update Custom Exceptions (Medium Priority)

Extend your custom exceptions from `FastAPIEasyException`:

**Before:**
```python
class BusinessError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

raise BusinessError("Insufficient credits")
```

**After:**
```python
from fastapi_easy.core.exceptions import (
    FastAPIEasyException,
    ErrorCategory,
    ErrorSeverity,
)

class BusinessError(FastAPIEasyException):
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            code="BUSINESS_ERROR",
            status_code=400,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )

raise BusinessError(
    message="Insufficient credits",
    details_field="credits",
    suggestion="Please add credits to your account",
)
```

### Phase 4: Add Error Recovery (Optional)

Implement retry and fallback strategies:

```python
from fastapi_easy.core.exceptions.handlers import (
    ErrorHandler,
    RetryConfig,
    FallbackConfig,
    handle_errors,
    ErrorHandlingStrategy,
)

# Global error handler
error_handler = ErrorHandler()

# Configure retry for database operations
error_handler.configure_retry(
    DatabaseConnectionException,
    RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        exponential_base=2.0,
        jitter=True,
    )
)

# Configure fallback for external services
error_handler.configure_fallback(
    ExternalServiceException,
    FallbackConfig(
        fallback_func=get_cached_data,
        fallback_args=[],
        fallback_kwargs={"ttl": 300},
    )
)

# Use decorators for automatic handling
@handle_errors(
    strategy=ErrorHandlingStrategy.RETRY,
    exceptions=[DatabaseConnectionException]
)
async def get_user_data(user_id: str):
    return await database.fetch_user(user_id)
```

## Specific File Migrations

### Updating CRUDRouter

The `crud_router.py` has been updated to use the new exception system. Key changes:

1. **New Imports**: Added exception classes
2. **Enhanced Error Handling**: `_handle_error` method now creates specific exceptions
3. **Context Tracking**: Errors include operation context
4. **Automatic Conversion**: Database errors are converted to appropriate exception types

No changes required if you're using the latest version.

### Updating Migration Engine

The migration engine has been enhanced with better error handling:

1. **Migration Exceptions**: Specific exceptions for migration failures
2. **Lock Handling**: Proper lock acquisition errors
3. **Context Tracking**: Migration operations include detailed context

No changes required if you're using the latest version.

### Updating Distributed Lock

The distributed lock module will benefit from automatic exception handling by the middleware, but you can also use specific exceptions:

```python
from fastapi_easy.core.exceptions import DatabaseLockException

# In your lock implementation
if not await self._acquire_lock(timeout):
    raise DatabaseLockException(
        lock_type="distributed",
        resource=resource_name,
        timeout=timeout,
    )
```

### Updating JWT Authentication

JWT authentication can use specific auth exceptions:

```python
from fastapi_easy.core.exceptions import (
    TokenExpiredException,
    TokenInvalidException,
    AuthenticationException,
)

# In your auth code
if token_expired:
    raise TokenExpiredException(
        expires_at=token.exp,
        token_type="access",
    )

if token_invalid:
    raise TokenInvalidException(
        reason="Invalid signature",
        token_type="access",
    )
```

## Configuration Updates

### Environment Variables

Add these environment variables for error handling configuration:

```bash
# Error handling settings
ERROR_RESPONSE_FORMAT=standard  # standard, minimal, detailed, development
ERROR_INCLUDE_TRACEBACK=false
ERROR_LOG_ERRORS=true
ERROR_MONITOR_ERRORS=true

# Security settings
ERROR_SANITIZE_ERRORS=true
ERROR_MAX_ERROR_DETAIL=1000
```

### Application Settings

Update your application configuration:

```python
# config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Error handling
    error_response_format: str = "standard"
    error_include_traceback: bool = False
    error_log_errors: bool = True
    error_monitor_errors: bool = True

    # Security
    error_sanitize_errors: bool = True
    error_max_error_detail: int = 1000

    class Config:
        env_prefix = "ERROR_"

settings = Settings()
```

## Testing Migration

### Unit Tests

Update your tests to expect new exception types:

**Before:**
```python
def test_get_user_not_found():
    with pytest.raises(HTTPException) as exc_info:
        await get_user("nonexistent")
    assert exc_info.value.status_code == 404
```

**After:**
```python
def test_get_user_not_found():
    with pytest.raises(NotFoundError) as exc_info:
        await get_user("nonexistent")
    assert exc_info.value.code == "NOT_FOUND_ERROR"
    assert exc_info.value.status_code == 404
```

### Integration Tests

Test error responses:

```python
def test_api_error_response(client):
    response = client.get("/users/nonexistent")

    assert response.status_code == 404
    error_data = response.json()

    assert "error" in error_data
    assert error_data["error"]["code"] == "NOT_FOUND_ERROR"
    assert "context" in error_data["error"]
    assert "correlation_id" in error_data["error"]["context"]
```

## Rollback Plan

If you need to rollback the migration:

1. **Remove Middleware**: Delete the `add_error_middleware()` call
2. **Restore Imports**: Keep new imports for future use
3. **Partial Rollback**: Keep using new exceptions without middleware

The new exception classes are backward compatible and can be used without the middleware.

## Common Migration Issues

### Issue: "Import Error: cannot import name 'NotFoundError'"

**Solution**: Ensure you're importing from the correct module:
```python
from fastapi_easy.core.exceptions import NotFoundError
```

### Issue: "Middleware not catching exceptions"

**Solution**: Add middleware before defining routes:
```python
app = FastAPI()
add_error_middleware(app)  # Add this first

@app.get("/users/{user_id}")  # Then define routes
async def get_user(user_id: str):
    # ...
```

### Issue: "Too much error detail in production"

**Solution**: Configure appropriate response format:
```python
add_error_middleware(
    app,
    response_format=ResponseFormat.MINIMAL,  # Use minimal in production
)
```

### Issue: "Performance impact from error tracking"

**Solution**: Disable tracking if not needed:
```python
add_error_middleware(
    app,
    track_metrics=False,  # Disable if not using metrics
)
```

## Migration Checklist

- [ ] Add error handling middleware
- [ ] Update imports to use new exceptions
- [ ] Replace HTTPException with specific exceptions
- [ ] Add context information to errors
- [ ] Update custom exceptions to extend FastAPIEasyException
- [ ] Configure environment variables
- [ ] Update unit tests
- [ ] Update integration tests
- [ ] Test error responses in different environments
- [ ] Monitor error metrics
- [ ] Update documentation

## Support

For migration assistance:
1. Check the [Error Handling Guide](ERROR_HANDLING_GUIDE.md)
2. Review test examples in the repository
3. Open an issue with specific migration questions

Remember: The new error handling system is designed to be backward compatible. You can migrate gradually and see immediate benefits from the middleware alone.