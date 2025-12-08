# FastAPI-Easy Refactoring Examples

This document provides concrete examples of recommended refactoring improvements for the FastAPI-Easy project.

## 1. Improved Distributed Lock Implementation

### Current Issues
- Connection leaks in PostgreSQL/MySQL providers
- Complex test environment handling
- No proper timeout management

### Refactored Implementation

```python
"""
Improved distributed lock with proper resource management
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Optional, AsyncContextManager, Any
from enum import Enum

import aiopg  # For PostgreSQL async support
import aiomysql  # For MySQL async support
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

logger = logging.getLogger(__name__)


class LockState(Enum):
    RELEASED = "released"
    ACQUIRED = "acquired"
    EXPIRED = "expired"


@dataclass
class LockConfig:
    """Configuration for distributed locks"""
    timeout: int = 30
    retry_interval: float = 0.1
    max_retries: int = 3
    heartbeat_interval: float = 10.0
    auto_renew: bool = False


class LockError(Exception):
    """Base exception for lock operations"""
    pass


class LockAcquisitionError(LockError):
    """Failed to acquire lock"""
    pass


class LockReleaseError(LockError):
    """Failed to release lock"""
    pass


class LockProvider(ABC):
    """Abstract base class for lock providers"""

    @abstractmethod
    async def acquire(self, lock_key: str, config: LockConfig) -> AsyncContextManager:
        """Acquire a lock"""
        pass

    @abstractmethod
    async def release(self, lock_key: str) -> bool:
        """Release a lock"""
        pass

    @abstractmethod
    async def is_locked(self, lock_key: str) -> bool:
        """Check if lock is held"""
        pass


class DatabaseLockProvider(LockProvider):
    """Base class for database-based locks with connection pooling"""

    def __init__(self, engine: AsyncEngine, pool_size: int = 5):
        self.engine = engine
        self.pool_size = pool_size
        self._locks: Dict[str, LockState] = {}

    @asynccontextmanager
    async def acquire(self, lock_key: str, config: LockConfig) -> AsyncContextManager[Any]:
        """Acquire lock with proper resource management"""
        lock_acquired = False

        try:
            # Try to acquire lock with retry
            for attempt in range(config.max_retries):
                if await self._try_acquire(lock_key, config.timeout):
                    lock_acquired = True
                    self._locks[lock_key] = LockState.ACQUIRED
                    logger.info(f"Lock acquired: {lock_key}")

                    # Start heartbeat if auto-renew enabled
                    heartbeat_task = None
                    if config.auto_renew:
                        heartbeat_task = asyncio.create_task(
                            self._heartbeat(lock_key, config.heartbeat_interval)
                        )

                    try:
                        yield lock_key
                    finally:
                        if heartbeat_task:
                            heartbeat_task.cancel()
                            try:
                                await heartbeat_task
                            except asyncio.CancelledError:
                                pass

                    break

                if attempt < config.max_retries - 1:
                    await asyncio.sleep(config.retry_interval)

            if not lock_acquired:
                raise LockAcquisitionError(f"Failed to acquire lock: {lock_key}")

        except Exception as e:
            logger.error(f"Error in lock acquire: {e}")
            raise
        finally:
            # Ensure cleanup
            if lock_acquired:
                await self.release(lock_key)

    async def _try_acquire(self, lock_key: str, timeout: int) -> bool:
        """To be implemented by subclasses"""
        raise NotImplementedError

    async def _heartbeat(self, lock_key: str, interval: float):
        """Maintain lock heartbeat"""
        while True:
            await asyncio.sleep(interval)
            # Refresh lock - implementation dependent
            await self._refresh_lock(lock_key)

    async def _refresh_lock(self, lock_key: str):
        """To be implemented by subclasses"""
        raise NotImplementedError


class PostgresLockProvider(DatabaseLockProvider):
    """PostgreSQL advisory lock provider with async support"""

    def __init__(self, engine: AsyncEngine):
        super().__init__(engine)
        # Convert lock key to numeric hash for pg_advisory_lock
        self._lock_ids = {}

    def _get_lock_id(self, lock_key: str) -> int:
        """Convert string key to numeric lock ID"""
        if lock_key not in self._lock_ids:
            # Use hash of the key
            self._lock_ids[lock_key] = hash(lock_key) & 0x7FFFFFFF
        return self._lock_ids[lock_key]

    async def _try_acquire(self, lock_key: str, timeout: int) -> bool:
        """Try to acquire PostgreSQL advisory lock"""
        lock_id = self._get_lock_id(lock_key)

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(
                    "SELECT pg_try_advisory_lock(%s)", (lock_id,)
                )
                locked = result.scalar()
                return locked

        except Exception as e:
            logger.error(f"Error acquiring PostgreSQL lock: {e}")
            return False

    async def _refresh_lock(self, lock_key: str):
        """Refresh PostgreSQL lock (no-op, advisory locks are connection-bound)"""
        # PostgreSQL advisory locks are tied to connection
        # No refresh needed as long as connection is maintained
        pass

    async def release(self, lock_key: str) -> bool:
        """Release PostgreSQL advisory lock"""
        lock_id = self._get_lock_id(lock_key)

        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(
                    "SELECT pg_advisory_unlock(%s)", (lock_id,)
                )
                released = result.scalar()

                if released:
                    self._locks[lock_key] = LockState.RELEASED
                    logger.info(f"Lock released: {lock_key}")

                return released

        except Exception as e:
            logger.error(f"Error releasing PostgreSQL lock: {e}")
            return False

    async def is_locked(self, lock_key: str) -> bool:
        """Check PostgreSQL lock status"""
        return self._locks.get(lock_key) == LockState.ACQUIRED


class FileLockProvider(LockProvider):
    """File-based lock provider with improved reliability"""

    def __init__(self, lock_dir: str = "/tmp/fastapi-easy-locks"):
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self._locks: Dict[str, LockState] = {}

    @asynccontextmanager
    async def acquire(self, lock_key: str, config: LockConfig):
        """Acquire file lock"""
        lock_file = self.lock_dir / f"{lock_key}.lock"
        lock_acquired = False

        try:
            # Try to acquire with atomic file creation
            start_time = time.time()

            while time.time() - start_time < config.timeout:
                try:
                    # Atomic file creation
                    fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)

                    # Write lock metadata
                    lock_data = {
                        "pid": os.getpid(),
                        "timestamp": time.time(),
                        "hostname": socket.gethostname(),
                        "lock_key": lock_key
                    }

                    with os.fdopen(fd, 'w') as f:
                        json.dump(lock_data, f)

                    lock_acquired = True
                    self._locks[lock_key] = LockState.ACQUIRED

                    try:
                        yield lock_key
                    finally:
                        # Ensure lock file is removed
                        if lock_file.exists():
                            lock_file.unlink()
                        self._locks[lock_key] = LockState.RELEASED

                    break

                except FileExistsError:
                    # Check if lock is stale
                    if await self._is_stale_lock(lock_file):
                        try:
                            lock_file.unlink()
                            continue
                        except OSError:
                            pass

                    await asyncio.sleep(config.retry_interval)

            if not lock_acquired:
                raise LockAcquisitionError(f"Failed to acquire file lock: {lock_key}")

        except Exception as e:
            logger.error(f"Error in file lock acquire: {e}")
            raise

    async def _is_stale_lock(self, lock_file: Path, timeout: int = 60) -> bool:
        """Check if lock file is stale"""
        try:
            with open(lock_file, 'r') as f:
                lock_data = json.load(f)

            # Check if process exists
            try:
                os.kill(lock_data['pid'], 0)
            except ProcessLookupError:
                return True

            # Check timestamp
            age = time.time() - lock_data['timestamp']
            return age > timeout

        except (json.JSONDecodeError, KeyError, OSError):
            return True

    async def release(self, lock_key: str) -> bool:
        """Release file lock"""
        lock_file = self.lock_dir / f"{lock_key}.lock"

        try:
            if lock_file.exists():
                lock_file.unlink()
                self._locks[lock_key] = LockState.RELEASED
                logger.info(f"File lock released: {lock_key}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error releasing file lock: {e}")
            return False

    async def is_locked(self, lock_key: str) -> bool:
        """Check file lock status"""
        lock_file = self.lock_dir / f"{lock_key}.lock"

        if not lock_file.exists():
            return False

        return not await self._is_stale_lock(lock_file)


class LockManager:
    """High-level lock manager with automatic provider selection"""

    def __init__(self, engine: Optional[AsyncEngine] = None):
        self.engine = engine
        self.provider: Optional[LockProvider] = None

    async def initialize(self, lock_file_dir: Optional[str] = None):
        """Initialize appropriate lock provider"""
        if self.engine:
            dialect = self.engine.dialect.name

            if dialect == "postgresql":
                self.provider = PostgresLockProvider(self.engine)
            elif dialect == "mysql":
                self.provider = MySQLLockProvider(self.engine)
            else:
                self.provider = FileLockProvider(lock_file_dir)
        else:
            self.provider = FileLockProvider(lock_file_dir)

    async def acquire_lock(
        self,
        lock_key: str,
        config: Optional[LockConfig] = None
    ) -> AsyncContextManager:
        """Acquire a lock"""
        if not self.provider:
            await self.initialize()

        config = config or LockConfig()
        return await self.provider.acquire(lock_key, config)

    async def release_lock(self, lock_key: str) -> bool:
        """Release a lock"""
        if not self.provider:
            return False
        return await self.provider.release(lock_key)


# Usage example
async def example_usage():
    """Example of using the improved lock system"""
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    lock_manager = LockManager(engine)

    try:
        async with await lock_manager.acquire_lock("migration_lock") as lock:
            # Critical section
            logger.info(f"Working with lock: {lock}")
            # Perform migration operations

    except LockAcquisitionError as e:
        logger.error(f"Could not acquire lock: {e}")
```

## 2. Improved Query Parameter Handler

### Current Issues
- Dynamic signature modification
- Limited performance optimizations
- No request context access

### Refactored Implementation

```python
"""
Improved query parameter handling with field descriptors
"""

import json
from typing import Any, Type, get_type_hints, Optional, Dict, Set
from dataclasses import dataclass, field
from functools import lru_cache
from fastapi import Query, Depends
from pydantic import BaseModel, Field
from starlette.requests import Request


@dataclass
class QueryParamConfig:
    """Configuration for query parameter handling"""
    enable_caching: bool = True
    enable_validation_context: bool = True
    strict_mode: bool = False
    max_array_length: int = 100
    max_dict_depth: int = 5


class QueryParamDescriptor:
    """Descriptor for query parameters with proper typing"""

    def __init__(
        self,
        field_name: str,
        field_type: Type,
        default_value: Any = None,
        description: Optional[str] = None,
        required: bool = False,
        config: Optional[QueryParamConfig] = None
    ):
        self.field_name = field_name
        self.field_type = field_type
        self.default_value = default_value
        self.description = description or f"Query parameter: {field_name}"
        self.required = required
        self.config = config or QueryParamConfig()
        self._cache_key = f"{field_name}_{field_type}_{default_value}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self

        return getattr(obj, f"_value_{self.field_name}", self.default_value)

    def __set__(self, obj, value):
        setattr(obj, f"_value_{self.field_name}", value)

    @lru_cache(maxsize=128)
    def parse_value(self, raw_value: str) -> Any:
        """Parse raw query string value with caching"""
        if not isinstance(raw_value, str):
            return raw_value

        # Handle complex types
        origin = get_origin(self.field_type)

        if origin is list or self.field_type is list:
            return self._parse_list(raw_value)
        elif origin is dict or self.field_type is dict:
            return self._parse_dict(raw_value)
        elif hasattr(self.field_type, '__fields__'):  # Pydantic model
            return self._parse_model(raw_value)

        # Simple type conversion
        return self._convert_simple_type(raw_value)

    def _parse_list(self, value: str) -> list:
        """Parse JSON array or comma-separated values"""
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                if len(parsed) > self.config.max_array_length:
                    raise ValueError(f"Array too long (max: {self.config.max_array_length})")
                return parsed
        except json.JSONDecodeError:
            # Fallback to comma-separated
            return [item.strip() for item in value.split(',') if item.strip()]

    def _parse_dict(self, value: str) -> dict:
        """Parse JSON dictionary"""
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                if self._get_dict_depth(parsed) > self.config.max_dict_depth:
                    raise ValueError(f"Dictionary too deep (max: {self.config.max_dict_depth})")
                return parsed
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON for dictionary parameter: {self.field_name}")

    def _parse_model(self, value: str) -> BaseModel:
        """Parse Pydantic model from JSON"""
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return self.field_type(**parsed)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid JSON for model parameter {self.field_name}: {e}")

    def _convert_simple_type(self, value: str) -> Any:
        """Convert simple types"""
        if self.field_type is bool:
            return value.lower() in ('true', '1', 'yes', 'on')
        elif self.field_type is int:
            return int(value)
        elif self.field_type is float:
            return float(value)
        return value

    def _get_dict_depth(self, d: dict, current_depth: int = 0) -> int:
        """Calculate dictionary depth"""
        if not isinstance(d, dict):
            return current_depth

        max_depth = current_depth
        for value in d.values():
            if isinstance(value, dict):
                max_depth = max(max_depth, self._get_dict_depth(value, current_depth + 1))

        return max_depth


class QueryParamsMeta(type):
    """Metaclass for query parameter models with descriptor management"""

    def __new__(mcls, name, bases, namespace):
        # Collect field definitions
        fields = {}
        hints = get_type_hints(namespace.get('__annotations__', {}))

        for key, value in namespace.items():
            if isinstance(value, (Field, QueryParamDescriptor)):
                fields[key] = value

        # Create descriptors for Pydantic fields
        for field_name, field_info in namespace.get('__annotations__', {}).items():
            if field_name not in fields:
                if field_name in hints:
                    fields[field_name] = QueryParamDescriptor(
                        field_name=field_name,
                        field_type=hints[field_name],
                        required=True
                    )

        # Add descriptors to namespace
        namespace.update(fields)
        namespace['_query_fields'] = fields

        return super().__new__(mcls, name, bases, namespace)


class QueryParamsBase(metaclass=QueryParamsMeta):
    """Base class for query parameter models"""

    def __init__(self, request: Request, **kwargs):
        self._request = request
        self._context = {}

        # Set values from query parameters
        for field_name in getattr(self, '_query_fields', {}):
            descriptor = getattr(self.__class__, field_name)
            if isinstance(descriptor, QueryParamDescriptor):
                value = kwargs.get(field_name, descriptor.default_value)
                if value is not None:
                    try:
                        parsed_value = descriptor.parse_value(str(value))
                        setattr(self, field_name, parsed_value)
                    except (ValueError, TypeError) as e:
                        if descriptor.config.strict_mode:
                            raise
                        logger.warning(f"Failed to parse {field_name}: {e}")

    def get_context(self) -> Dict[str, Any]:
        """Get request context for validation"""
        return {
            'request': self._request,
            'user': getattr(self._request.state, 'user', None),
            'headers': dict(self._request.headers),
            **self._context
        }


def as_query_params(
    schema: Type[BaseModel],
    config: Optional[QueryParamConfig] = None
):
    """
    Convert Pydantic model to query parameter dependency

    Args:
        schema: Pydantic model class
        config: Query parameter configuration

    Returns:
        FastAPI dependency function
    """

    # Create dynamic class with descriptors
    class_name = f"{schema.__name__}Query"

    # Get model fields
    model_fields = schema.model_fields
    type_hints = get_type_hints(schema)

    # Create namespace with descriptors
    namespace = {
        '__annotations__': {},
        '__module__': schema.__module__
    }

    for field_name, field_info in model_fields.items():
        field_type = type_hints.get(field_name, Any)

        # Create descriptor
        descriptor = QueryParamDescriptor(
            field_name=field_name,
            field_type=field_type,
            default_value=field_info.default if field_info.default != ... else None,
            description=field_info.description,
            required=field_info.default == ...,
            config=config
        )

        namespace[field_name] = descriptor
        namespace['__annotations__'][field_name] = field_type

    # Create the query parameter class
    QueryParamClass = type(class_name, (QueryParamsBase,), namespace)

    # Create FastAPI dependency
    async def query_dependency(request: Request, **query_params: Any):
        """FastAPI dependency function"""
        return QueryParamClass(request, **query_params)

    # Add query parameters to dependency signature
    for field_name, field_info in model_fields.items():
        if field_info.default != ...:
            query_dependency.__annotations__[field_name] = type_hints.get(field_name, str)
            setattr(
                query_dependency,
                field_name,
                Query(
                    default=field_info.default,
                    description=field_info.description or f"Query parameter: {field_name}"
                )
            )
        else:
            query_dependency.__annotations__[field_name] = type_hints.get(field_name, str)
            setattr(
                query_dependency,
                field_name,
                Query(
                    ...,
                    description=field_info.description or f"Query parameter: {field_name}"
                )
            )

    query_dependency.__annotations__['return'] = QueryParamClass

    return query_dependency


# Usage example
class UserSearchQuery(BaseModel):
    name: Optional[str] = None
    age_min: Optional[int] = Field(None, description="Minimum age")
    age_max: Optional[int] = Field(None, description="Maximum age")
    tags: List[str] = Field(default_factory=list, description="User tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="User metadata")


# FastAPI endpoint
@app.get("/users/search")
async def search_users(
    params: UserSearchQuery = Depends(as_query_params(UserSearchQuery, QueryParamConfig()))
):
    """Search users with query parameters"""
    # params now has properly typed and validated query parameters
    return {"filters": params.model_dump()}
```

## 3. Improved Error Handling System

### Current Issues
- Inconsistent error types
- Limited error context
- No centralized error handling

### Refactored Implementation

```python
"""
Unified error handling system for FastAPI-Easy
"""

import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union
from fastapi import HTTPException, Request, status
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """Standardized error codes"""

    # Validation errors (400)
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "INVALID_FORMAT"

    # Authentication errors (401)
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"

    # Authorization errors (403)
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    RESOURCE_ACCESS_DENIED = "RESOURCE_ACCESS_DENIED"

    # Not found errors (404)
    NOT_FOUND = "NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    ENDPOINT_NOT_FOUND = "ENDPOINT_NOT_FOUND"

    # Conflict errors (409)
    CONFLICT = "CONFLICT"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    VERSION_CONFLICT = "VERSION_CONFLICT"

    # Rate limit errors (429)
    RATE_LIMITED = "RATE_LIMITED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"

    # Server errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    MIGRATION_ERROR = "MIGRATION_ERROR"


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Error context information"""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)


class FastAPIEasyError(Exception):
    """Base exception for FastAPI-Easy errors"""

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None,
        context: Optional[ErrorContext] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        cause: Optional[Exception] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.context = context or ErrorContext()
        self.severity = severity
        self.cause = cause
        self.traceback = traceback.format_exc() if cause else None

        super().__init__(self.message)


class ValidationError(FastAPIEasyError):
    """Validation error"""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)

        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_FAILED,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            **kwargs
        )


class AuthenticationError(FastAPIEasyError):
    """Authentication error"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.UNAUTHORIZED,
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs
        )


class AuthorizationError(FastAPIEasyError):
    """Authorization error"""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.FORBIDDEN,
            status_code=status.HTTP_403_FORBIDDEN,
            **kwargs
        )


class NotFoundError(FastAPIEasyError):
    """Resource not found error"""

    def __init__(self, message: str = "Resource not found", resource_type: str = "resource", **kwargs):
        details = kwargs.get('details', {})
        details['resource_type'] = resource_type

        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            **kwargs
        )


class ConflictError(FastAPIEasyError):
    """Conflict error"""

    def __init__(self, message: str = "Resource conflict", **kwargs):
        super().__init__(
            message=message,
            code=ErrorCode.CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
            **kwargs
        )


class DatabaseError(FastAPIEasyError):
    """Database operation error"""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if operation:
            details['operation'] = operation
        if table:
            details['table'] = table

        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class MigrationError(FastAPIEasyError):
    """Migration error"""

    def __init__(
        self,
        message: str = "Migration failed",
        migration_version: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get('details', {})
        if migration_version:
            details['migration_version'] = migration_version

        super().__init__(
            message=message,
            code=ErrorCode.MIGRATION_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            severity=ErrorSeverity.CRITICAL,
            **kwargs
        )


class ErrorResponse(BaseModel):
    """Standard error response model"""

    error: str
    code: ErrorCode
    message: str
    details: Dict[str, Any] = {}
    request_id: Optional[str] = None
    timestamp: str

    @classmethod
    def from_exception(
        cls,
        error: FastAPIEasyError,
        request: Optional[Request] = None
    ) -> 'ErrorResponse':
        """Create error response from exception"""
        return cls(
            error=error.__class__.__name__,
            code=error.code,
            message=error.message,
            details=error.details,
            request_id=error.context.request_id or getattr(request.state, 'request_id', None) if request else None,
            timestamp=datetime.utcnow().isoformat()
        )


class ErrorHandler:
    """Centralized error handler"""

    def __init__(self):
        self.error_handlers: Dict[Type[Exception], callable] = {
            FastAPIEasyError: self._handle_fastapi_easy_error,
            ValidationError: self._handle_validation_error,
            ValueError: self._handle_value_error,
            HTTPException: self._handle_http_exception,
        }

    def register_handler(self, exception_type: Type[Exception], handler: callable):
        """Register custom error handler"""
        self.error_handlers[exception_type] = handler

    async def handle_error(
        self,
        error: Exception,
        request: Optional[Request] = None
    ) -> HTTPException:
        """Handle error and convert to HTTP exception"""

        # Find appropriate handler
        handler = None
        for exc_type, exc_handler in self.error_handlers.items():
            if isinstance(error, exc_type):
                handler = exc_handler
                break

        if not handler:
            handler = self._handle_generic_error

        # Handle the error
        try:
            return await handler(error, request)
        except Exception as handling_error:
            # Fallback if error handler fails
            logger.error(f"Error handler failed: {handling_error}")
            return HTTPException(
                status_code=500,
                detail={
                    "error": "InternalServerError",
                    "message": "An unexpected error occurred",
                    "code": ErrorCode.INTERNAL_ERROR
                }
            )

    async def _handle_fastapi_easy_error(
        self,
        error: FastAPIEasyError,
        request: Optional[Request] = None
    ) -> HTTPException:
        """Handle FastAPI-Easy specific errors"""

        # Log the error
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error.severity, logging.ERROR)

        logger.log(
            log_level,
            f"{error.__class__.__name__}: {error.message}",
            extra={
                'error_code': error.code,
                'details': error.details,
                'context': error.context.__dict__,
                'traceback': error.traceback
            }
        )

        # Create response
        response = ErrorResponse.from_exception(error, request)

        return HTTPException(
            status_code=error.status_code,
            detail=response.dict()
        )

    async def _handle_validation_error(
        self,
        error: ValidationError,
        request: Optional[Request] = None
    ) -> HTTPException:
        """Handle validation errors"""
        return await self._handle_fastapi_easy_error(error, request)

    async def _handle_value_error(
        self,
        error: ValueError,
        request: Optional[Request] = None
    ) -> HTTPException:
        """Handle value errors"""
        api_error = ValidationError(
            message=str(error),
            cause=error
        )
        return await self._handle_fastapi_easy_error(api_error, request)

    async def _handle_http_exception(
        self,
        error: HTTPException,
        request: Optional[Request] = None
    ) -> HTTPException:
        """Handle HTTP exceptions"""
        # Convert to standardized format if needed
        if isinstance(error.detail, dict) and 'code' in error.detail:
            return error

        response = ErrorResponse(
            error="HTTPException",
            code=ErrorCode.INTERNAL_ERROR,
            message=str(error.detail),
            request_id=getattr(request.state, 'request_id', None) if request else None,
            timestamp=datetime.utcnow().isoformat()
        )

        return HTTPException(
            status_code=error.status_code,
            detail=response.dict()
        )

    async def _handle_generic_error(
        self,
        error: Exception,
        request: Optional[Request] = None
    ) -> HTTPException:
        """Handle generic unexpected errors"""
        logger.error(
            f"Unexpected error: {error}",
            exc_info=True
        )

        api_error = FastAPIEasyError(
            message="An unexpected error occurred",
            code=ErrorCode.INTERNAL_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            cause=error,
            severity=ErrorSeverity.CRITICAL
        )

        return await self._handle_fastapi_easy_error(api_error, request)


# Global error handler instance
error_handler = ErrorHandler()


def create_error_handler_middleware():
    """Create FastAPI error handler middleware"""

    async def error_handler_middleware(request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            http_exception = await error_handler.handle_error(e, request)

            # Return JSON response for consistency
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=http_exception.status_code,
                content=http_exception.detail
            )

    return error_handler_middleware


# Usage examples
def example_usage():
    """Examples of using the error handling system"""

    # Raise specific errors
    raise ValidationError(
        message="Invalid email format",
        field="email",
        value="invalid-email"
    )

    raise NotFoundError(
        message="User not found",
        resource_type="User",
        context=ErrorContext(
            user_id="123",
            action="get_user"
        )
    )

    raise DatabaseError(
        message="Failed to create user",
        operation="INSERT",
        table="users",
        cause=Exception("Connection timeout")
    )


# FastAPI app setup
def setup_error_handling(app):
    """Setup error handling for FastAPI app"""

    # Add middleware
    app.middleware("http")(create_error_handler_middleware())

    # Register custom handlers
    @app.exception_handler(FastAPIEasyError)
    async def fastapi_easy_exception_handler(request: Request, exc: FastAPIEasyError):
        http_exception = await error_handler.handle_error(exc, request)
        return JSONResponse(
            status_code=http_exception.status_code,
            content=http_exception.detail
        )
```

## 4. Improved Configuration Management

### Current Issues
- Scattered configuration
- Limited validation
- No environment-specific configs

### Refactored Implementation

```python
"""
Improved configuration management system
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from pydantic import BaseSettings, Field, validator
import yaml
import toml


class Environment(str, Enum):
    """Application environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


T = TypeVar('T', bound='BaseConfig')


class ConfigLoader(ABC):
    """Abstract base for configuration loaders"""

    @abstractmethod
    def load(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from file"""
        pass

    @abstractmethod
    def save(self, config: Dict[str, Any], path: Union[str, Path]) -> None:
        """Save configuration to file"""
        pass


class YAMLConfigLoader(ConfigLoader):
    """YAML configuration loader"""

    def load(self, path: Union[str, Path]) -> Dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def save(self, config: Dict[str, Any], path: Union[str, Path]) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False)


class TOMLConfigLoader(ConfigLoader):
    """TOML configuration loader"""

    def load(self, path: Union[str, Path]) -> Dict[str, Any]:
        import toml
        with open(path, 'r', encoding='utf-8') as f:
            return toml.load(f)

    def save(self, config: Dict[str, Any], path: Union[str, Path]) -> None:
        import toml
        with open(path, 'w', encoding='utf-8') as f:
            toml.dump(config, f)


class EnvConfigLoader(ConfigLoader):
    """Environment variable configuration loader"""

    def __init__(self, prefix: str = "FASTAPI_EASY_"):
        self.prefix = prefix

    def load(self, path: Union[str, Path] = None) -> Dict[str, Any]:
        config = {}

        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(self.prefix):].lower()

                # Try to parse as JSON, fallback to string
                try:
                    import json
                    config[config_key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    config[config_key] = value

        return config

    def save(self, config: Dict[str, Any], path: Union[str, Path] = None) -> None:
        """Environment variables are read-only"""
        raise NotImplementedError("Cannot save to environment variables")


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = Field(..., description="Database URL")
    pool_size: int = Field(10, description="Connection pool size")
    max_overflow: int = Field(20, description="Max overflow connections")
    pool_timeout: int = Field(30, description="Pool timeout in seconds")
    pool_recycle: int = Field(3600, description="Pool recycle time in seconds")
    echo: bool = Field(False, description="Enable SQL logging")

    @validator('url')
    def validate_url(cls, v):
        if not v:
            raise ValueError('Database URL is required')
        return v


@dataclass
class RedisConfig:
    """Redis configuration"""
    url: str = Field("redis://localhost:6379", description="Redis URL")
    max_connections: int = Field(10, description="Max connections")
    retry_on_timeout: bool = Field(True, description="Retry on timeout")
    socket_timeout: int = Field(5, description="Socket timeout")


@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = Field(..., description="JWT secret key")
    algorithm: str = Field("HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(30, description="Access token expiration")
    refresh_token_expire_days: int = Field(7, description="Refresh token expiration")
    password_min_length: int = Field(8, description="Minimum password length")
    max_login_attempts: int = Field(5, description="Max login attempts")
    lockout_duration_minutes: int = Field(15, description="Lockout duration")

    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters')
        return v


@dataclass
class MigrationConfig:
    """Migration configuration"""
    directory: str = Field("migrations", description="Migration directory")
    auto_migrate: bool = Field(False, description="Auto-migrate on startup")
    lock_timeout: int = Field(300, description="Lock timeout in seconds")
    dry_run: bool = Field(False, description="Run in dry-run mode")


class BaseConfig(BaseSettings):
    """Base configuration class"""

    # Environment
    environment: Environment = Field(Environment.DEVELOPMENT, description="Application environment")
    debug: bool = Field(False, description="Debug mode")

    # Server
    host: str = Field("0.0.0.0", description="Server host")
    port: int = Field(8000, description="Server port")
    workers: int = Field(1, description="Number of workers")

    # Logging
    log_level: str = Field("INFO", description="Log level")
    log_format: str = Field("%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")

    # Sub-configurations
    database: DatabaseConfig = Field(..., description="Database configuration")
    redis: RedisConfig = Field(default_factory=RedisConfig, description="Redis configuration")
    security: SecurityConfig = Field(..., description="Security configuration")
    migration: MigrationConfig = Field(default_factory=MigrationConfig, description="Migration configuration")

    # Application specific
    api_prefix: str = Field("/api/v1", description="API prefix")
    cors_origins: List[str] = Field(default_factory=list, description="CORS origins")
    rate_limit_enabled: bool = Field(True, description="Enable rate limiting")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

        # Environment prefix for nested configs
        env_prefix = "FASTAPI_EASY_"

    @classmethod
    def from_file(
        cls: Type[T],
        path: Union[str, Path],
        loader: Optional[ConfigLoader] = None
    ) -> T:
        """Load configuration from file"""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        # Determine loader based on extension
        if loader is None:
            if path.suffix.lower() in ['.yml', '.yaml']:
                loader = YAMLConfigLoader()
            elif path.suffix.lower() == '.toml':
                loader = TOMLConfigLoader()
            else:
                raise ValueError(f"Unsupported config file extension: {path.suffix}")

        # Load configuration
        config_data = loader.load(path)

        # Flatten nested keys
        flattened = cls._flatten_dict(config_data)

        # Create instance
        return cls(**flattened)

    @classmethod
    def from_environment(
        cls: Type[T],
        prefix: str = "FASTAPI_EASY_"
    ) -> T:
        """Load configuration from environment variables"""
        loader = EnvConfigLoader(prefix)
        config_data = loader.load()

        return cls(**config_data)

    @classmethod
    def _flatten_dict(cls, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Flatten nested dictionary"""
        items = []

        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k

            if isinstance(v, dict):
                items.extend(cls._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))

        return dict(items)

    def save_to_file(
        self,
        path: Union[str, Path],
        loader: Optional[ConfigLoader] = None
    ) -> None:
        """Save configuration to file"""
        path = Path(path)

        if loader is None:
            if path.suffix.lower() in ['.yml', '.yaml']:
                loader = YAMLConfigLoader()
            elif path.suffix.lower() == '.toml':
                loader = TOMLConfigLoader()
            else:
                raise ValueError(f"Unsupported config file extension: {path.suffix}")

        # Convert to dictionary
        config_dict = self.dict()

        # Unflatten nested keys
        unflattened = self._unflatten_dict(config_dict)

        # Save to file
        loader.save(unflattened, path)

    @classmethod
    def _unflatten_dict(cls, d: Dict[str, Any], sep: str = '_') -> Dict[str, Any]:
        """Unflatten dictionary"""
        result = {}

        for key, value in d.items():
            parts = key.split(sep)
            current = result

            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            current[parts[-1]] = value

        return result

    def get_database_url(self) -> str:
        """Get database URL"""
        return self.database.url

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PRODUCTION


class ConfigManager:
    """Configuration manager with environment-specific configs"""

    def __init__(self, config_class: Type[BaseConfig] = BaseConfig):
        self.config_class = config_class
        self._configs: Dict[str, BaseConfig] = {}

    def load_config(
        self,
        environment: Optional[Environment] = None,
        config_file: Optional[Union[str, Path]] = None,
        env_prefix: Optional[str] = None
    ) -> BaseConfig:
        """Load configuration for specific environment"""

        environment = environment or Environment(os.getenv('ENV', 'development'))
        cache_key = str(environment)

        if cache_key in self._configs:
            return self._configs[cache_key]

        # Load base config
        config = self.config_class()

        # Override with environment file if exists
        if config_file:
            env_file = Path(config_file)
        else:
            env_file = Path(f"config.{environment.value}.yml")

        if env_file.exists():
            config = self.config_class.from_file(env_file)

        # Override with environment variables
        env_config = self.config_class.from_environment(env_prefix)

        # Merge configs (environment variables take precedence)
        merged_config = self._merge_configs(config, env_config)

        # Cache
        self._configs[cache_key] = merged_config

        return merged_config

    def _merge_configs(self, base: BaseConfig, override: BaseConfig) -> BaseConfig:
        """Merge two configuration objects"""
        base_dict = base.dict()
        override_dict = override.dict()

        # Deep merge
        merged = self._deep_merge(base_dict, override_dict)

        return self.config_class(**merged)

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def clear_cache(self):
        """Clear configuration cache"""
        self._configs.clear()


# Global config manager instance
config_manager = ConfigManager()


# Usage examples
def example_usage():
    """Examples of using the configuration system"""

    # Load from file
    config = BaseConfig.from_file("config.yml")

    # Load from environment
    env_config = BaseConfig.from_environment("MY_APP_")

    # Load with manager
    manager = ConfigManager()
    dev_config = manager.load_config(Environment.DEVELOPMENT)
    prod_config = manager.load_config(Environment.PRODUCTION)

    # Access configuration
    print(f"Database URL: {config.database.url}")
    print(f"Secret key: {config.security.secret_key}")
    print(f"Is production: {config.is_production()}")
```

These refactoring examples demonstrate:

1. **Better Resource Management**: Improved connection handling and cleanup
2. **Consistent Error Handling**: Unified error types and responses
3. **Type Safety**: Proper use of descriptors and type hints
4. **Configuration Flexibility**: Support for multiple config sources and formats
5. **Performance Optimizations**: Caching and async operations
6. **Security Improvements**: Better validation and input handling
7. **Maintainability**: Cleaner separation of concerns and interfaces

Each example addresses specific issues identified in the architectural review while maintaining backward compatibility where possible.