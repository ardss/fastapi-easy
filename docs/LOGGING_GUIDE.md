# Logging Guide

This guide covers the logging configuration and best practices used in FastAPI-Easy.

## Overview

FastAPI-Easy uses **structured logging** with `structlog` for consistent, queryable log output across all components. The logging system is designed to:

- Provide structured JSON logs in production
- Support human-readable logs in development
- Include correlation IDs for request tracing
- Log errors with full context
- Support different log levels per component
- Integrate with monitoring systems

## Configuration

### Basic Setup

```python
from fastapi import FastAPI
from fastapi_easy.core.logging import configure_logging, get_logger
import structlog

# Configure logging
configure_logging(
    level="INFO",  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    json_logs=False,  # True for production
    include_fields=True,  # Include request/response fields
)

app = FastAPI()

# Get a logger for your module
logger = get_logger(__name__)

@app.get("/")
async def root():
    logger.info("Root endpoint accessed", extra={"user_agent": "test"})
    return {"message": "Hello World"}
```

### Advanced Configuration

```python
from fastapi_easy.core.logging import configure_logging, LoggingConfig

config = LoggingConfig(
    level="INFO",
    json_logs=True,  # Production mode
    include_fields=True,
    log_requests=True,
    log_responses=True,
    exclude_paths=["/health", "/metrics"],  # Don't log health checks
    additional_processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ],
)

configure_logging(config)
```

## Logging Levels

Use appropriate log levels for different types of messages:

### DEBUG (10)
Detailed information, typically of interest only when diagnosing problems.

```python
logger.debug(
    "Processing database query",
    extra={
        "query": str(query),
        "params": query.parameters,
        "execution_time_ms": 45.2
    }
)
```

### INFO (20)
General information about application flow.

```python
logger.info(
    "User authentication successful",
    extra={
        "user_id": user.id,
        "method": "oauth2",
        "provider": "google"
    }
)
```

### WARNING (30)
Unexpected behavior that doesn't prevent the application from working.

```python
logger.warning(
    "Cache miss for frequently accessed item",
    extra={
        "cache_key": f"user:{user_id}:profile",
        "hit_rate": 0.75
    }
)
```

### ERROR (40)
Error events that might still allow the application to continue running.

```python
logger.error(
    "Failed to process payment",
    extra={
        "payment_id": payment.id,
        "amount": payment.amount,
        "error": str(exc)
    },
    exc_info=True  # Include stack trace
)
```

### CRITICAL (50)
Very severe error events that will presumably lead the application to abort.

```python
logger.critical(
    "Database connection lost",
    extra={
        "database": "primary",
        "attempts": 5,
        "last_error": str(exc)
    }
)
```

## Structured Logging

### Basic Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Simple structured log
logger.info("User created", user_id=123, email="user@example.com")

# Complex structured log
logger.info(
    "API request processed",
    extra={
        "endpoint": "/api/users",
        "method": "POST",
        "status_code": 201,
        "duration_ms": 123.45,
        "user_id": user.id,
        "request_id": request_id
    }
)
```

### Context Management

```python
from structlog.contextvars import bind_contextvars, clear_contextvars

# Bind context for the entire request
async def process_request(request: Request):
    bind_contextvars(
        request_id=request.headers.get("X-Request-ID"),
        user_id=request.state.user.id if hasattr(request.state, "user") else None,
        ip_address=request.client.host,
    )

    try:
        # All logs in this context will include the bound variables
        logger.info("Processing request started")
        result = await business_logic()
        logger.info("Processing request completed")
        return result
    finally:
        clear_contextvars()
```

## Request Logging Middleware

FastAPI-Easy includes automatic request/response logging:

```python
from fastapi_easy.core.logging import RequestLoggingMiddleware

app.add_middleware(
    RequestLoggingMiddleware,
    log_requests=True,
    log_responses=True,
    log_headers=False,  # Set to True for debugging
    include_body=False,  # Be careful with sensitive data
    exclude_paths=["/health", "/metrics"],
)
```

### Custom Request Logging

```python
from fastapi import Request
from structlog.contextvars import bind_contextvars

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Generate request ID
    request_id = str(uuid.uuid4())
    bind_contextvars(request_id=request_id)

    start_time = time.time()

    # Log request
    logger.info(
        "Request started",
        extra={
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
        }
    )

    try:
        response = await call_next(request)

        # Log response
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Request completed",
            extra={
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )

        return response
    except Exception as exc:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "Request failed",
            extra={
                "error": str(exc),
                "duration_ms": duration_ms,
            },
            exc_info=True
        )
        raise
```

## Error Logging

### Exception Logging

```python
import traceback
from fastapi_easy.core.errors import AppError

async def handle_error(exc: Exception, context: dict):
    """Log errors with full context."""

    if isinstance(exc, AppError):
        # Application error - log with details
        logger.error(
            "Application error occurred",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "error_message": exc.message,
                "error_details": exc.details,
                **context
            }
        )
    else:
        # Unexpected error - log with full traceback
        logger.error(
            "Unexpected error occurred",
            extra={
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                **context
            },
            exc_info=True
        )
```

### Performance Logging

```python
import time
from functools import wraps

def log_performance(func):
    """Decorator to log function performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        function_name = f"{func.__module__}.{func.__name__}"

        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                "Function completed successfully",
                extra={
                    "function": function_name,
                    "duration_ms": duration_ms,
                    "success": True
                }
            )

            return result
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                "Function failed",
                extra={
                    "function": function_name,
                    "duration_ms": duration_ms,
                    "success": False,
                    "error": str(exc)
                },
                exc_info=True
            )
            raise

    return wrapper

# Usage
@log_performance
async def expensive_operation(data: dict):
    """Expensive operation with performance logging."""
    # ... operation logic
    pass
```

## Business Event Logging

### User Actions

```python
async def log_user_action(
    user_id: int,
    action: str,
    resource: str,
    resource_id: Optional[int] = None,
    metadata: Optional[dict] = None
):
    """Log user business actions."""

    logger.info(
        "User action performed",
        extra={
            "event_type": "user_action",
            "user_id": user_id,
            "action": action,  # create, read, update, delete
            "resource": resource,  # user, post, comment
            "resource_id": resource_id,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Usage
await log_user_action(
    user_id=123,
    action="create",
    resource="post",
    resource_id=456,
    metadata={"title": "My New Post", "category": "tech"}
)
```

### Security Events

```python
async def log_security_event(
    event_type: str,
    user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None
):
    """Log security-related events."""

    logger.warning(
        "Security event detected",
        extra={
            "event_type": "security",
            "security_event": event_type,  # login_failed, suspicious_activity, etc.
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Usage
await log_security_event(
    event_type="login_failed",
    user_id=123,
    ip_address="192.168.1.1",
    details={"reason": "invalid_password", "attempts": 3}
)
```

## Log Aggregation and Monitoring

### ELK Stack Configuration

```python
# For production with ELK stack
configure_logging(
    level="INFO",
    json_logs=True,
    additional_processors=[
        structlog.processors.JSONRenderer(),
    ]
)

# Log format for Elasticsearch
{
  "timestamp": "2023-12-08T10:30:00.000Z",
  "level": "info",
  "logger": "app.services.user",
  "message": "User authentication successful",
  "user_id": 123,
  "method": "oauth2",
  "provider": "google",
  "request_id": "req_123456"
}
```

### Integration with Monitoring Systems

```python
from prometheus_client import Counter, Histogram

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

class MetricsMiddleware:
    async def __call__(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        # Update Prometheus metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        REQUEST_DURATION.observe(time.time() - start_time)

        # Log metrics
        logger.info(
            "Request metrics",
            extra={
                "method": request.method,
                "endpoint": request.url.path,
                "status_code": response.status_code,
                "duration_seconds": time.time() - start_time
            }
        )

        return response
```

## Development vs Production

### Development Configuration

```python
# Development - human readable logs
configure_logging(
    level="DEBUG",
    json_logs=False,
    include_fields=True,
)

# Output format:
# 2023-12-08 10:30:00 [INFO] app.services.user: User authentication successful user_id=123 method=oauth2
```

### Production Configuration

```python
# Production - structured JSON logs
configure_logging(
    level="INFO",
    json_logs=True,
    include_fields=True,
)

# Output format:
# {"timestamp": "2023-12-08T10:30:00.000Z", "level": "info", "logger": "app.services.user", "message": "User authentication successful", "user_id": 123, "method": "oauth2"}
```

## Best Practices

### 1. Use Structured Data

```python
# ❌ Bad - Unstructured message
logger.info("User 123 logged in from 192.168.1.1")

# ✅ Good - Structured data
logger.info(
    "User login successful",
    extra={
        "user_id": 123,
        "ip_address": "192.168.1.1",
        "timestamp": datetime.utcnow().isoformat()
    }
)
```

### 2. Include Correlation IDs

```python
# Always include request IDs for tracing
logger.info(
    "Operation completed",
    extra={
        "operation": "create_user",
        "user_id": user.id,
        "request_id": request_id,
        "trace_id": trace_id
    }
)
```

### 3. Log at Appropriate Levels

```python
# Debug: Detailed diagnostics
logger.debug("Database query executed", query=str(query), duration_ms=45.2)

# Info: Important business events
logger.info("Order created", order_id=123, customer_id=456, total=99.99)

# Warning: Potential issues
logger.warning("High memory usage", usage_percent=85.2, threshold=80.0)

# Error: Failure that needs attention
logger.error("Payment processing failed", payment_id=789, error=str(exc), exc_info=True)

# Critical: System failure
logger.critical("Database connection pool exhausted", active_connections=100, max_connections=100)
```

### 4. Avoid Sensitive Data

```python
# ❌ Bad - Logging sensitive data
logger.info("User created", email="user@example.com", password="secret123")

# ✅ Good - Sanitize sensitive data
logger.info(
    "User created",
    extra={
        "user_id": user.id,
        "email_domain": user.email.split("@")[1],  # Only domain
        "password_hash": hash_password(user.password),  # Hash only
    }
)
```

### 5. Use Context Managers

```python
from structlog.contextvars import bind_contextvars

# Bind context for the entire operation
bind_contextvars(
    operation="user_registration",
    user_id=user.id,
    session_id=session_id
)

try:
    # All logs will include the bound context
    logger.info("Registration started")
    await create_user(user)
    logger.info("Registration completed")
except Exception as exc:
    logger.error("Registration failed", exc_info=True)
    raise
finally:
    clear_contextvars()
```

This logging guide ensures consistent, structured, and useful logging throughout the FastAPI-Easy application, making debugging and monitoring much more effective.