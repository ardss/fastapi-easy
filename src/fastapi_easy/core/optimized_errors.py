"""
Optimized Error Handling and Response Management

Provides:
- Structured error responses
- Consistent API error format
- Error monitoring and logging
- Validation error handling
- Custom exception hierarchy
- Error context tracking
- Performance impact analysis
"""

from __future__ import annotations

import logging
import traceback
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorCode(str, Enum):
    """Standardized error codes"""

    # General errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    BAD_REQUEST = "BAD_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"

    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"
    DATABASE_CONSTRAINT_ERROR = "DATABASE_CONSTRAINT_ERROR"

    # Authentication errors
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"

    # Business logic errors
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    RESOURCE_NOT_AVAILABLE = "RESOURCE_NOT_AVAILABLE"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"

    # External service errors
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"
    EXTERNAL_SERVICE_UNAVAILABLE = "EXTERNAL_SERVICE_UNAVAILABLE"


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for errors"""

    request_id: Optional[str] = None
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class BaseError(Exception):
    """Base error class for FastAPI-Easy"""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        cause: Optional[Exception] = None,
        context: Optional[ErrorContext] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        self.severity = severity
        self.cause = cause
        self.context = context or ErrorContext()
        self.traceback = traceback.format_exc() if cause else None
        super().__init__(message)

    def to_dict(self, include_traceback: bool = False) -> Dict[str, Any]:
        """Convert error to dictionary"""
        error_dict = {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "severity": self.severity.value,
                "timestamp": self.context.timestamp.isoformat(),
            }
        }

        if self.details:
            error_dict["error"]["details"] = self.details

        if include_traceback and self.traceback:
            error_dict["error"]["traceback"] = self.traceback

        if self.context.request_id:
            error_dict["error"]["request_id"] = self.context.request_id

        if self.cause:
            error_dict["error"]["cause"] = str(self.cause)

        return error_dict


class ValidationError(BaseError):
    """Validation error"""

    def __init__(
        self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None, **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
            severity=ErrorSeverity.LOW,
            **kwargs,
        )


class NotFoundError(BaseError):
    """Resource not found error"""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs,
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            severity=ErrorSeverity.LOW,
            **kwargs,
        )


class ConflictError(BaseError):
    """Conflict error"""

    def __init__(
        self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None, **kwargs
    ):
        super().__init__(
            message=message,
            code=ErrorCode.CONFLICT,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class AuthenticationError(BaseError):
    """Authentication error"""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AUTHENTICATION_FAILED,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class AuthorizationError(BaseError):
    """Authorization error"""

    def __init__(
        self,
        message: str = "Access denied",
        permissions_required: Optional[List[str]] = None,
        **kwargs,
    ):
        details = {}
        if permissions_required:
            details["permissions_required"] = permissions_required

        super().__init__(
            message=message,
            code=ErrorCode.INSUFFICIENT_PERMISSIONS,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class RateLimitError(BaseError):
    """Rate limit error"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        limit: Optional[int] = None,
        window: Optional[int] = None,
        **kwargs,
    ):
        details = {}
        if retry_after is not None:
            details["retry_after"] = retry_after
        if limit is not None:
            details["limit"] = limit
        if window is not None:
            details["window"] = window

        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMITED,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class DatabaseError(BaseError):
    """Database error"""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
        table: Optional[str] = None,
        **kwargs,
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table

        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )


class BusinessRuleError(BaseError):
    """Business rule violation error"""

    def __init__(
        self,
        message: str = "Business rule violation",
        rule_name: Optional[str] = None,
        rule_description: Optional[str] = None,
        **kwargs,
    ):
        details = {}
        if rule_name:
            details["rule_name"] = rule_name
        if rule_description:
            details["rule_description"] = rule_description

        super().__init__(
            message=message,
            code=ErrorCode.BUSINESS_RULE_VIOLATION,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class ErrorReporter:
    """Error reporting and monitoring"""

    def __init__(
        self, enable_reporting: bool = True, report_threshold: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        self.enable_reporting = enable_reporting
        self.report_threshold = report_threshold
        self._error_counts: Dict[ErrorCode, int] = {}
        self._error_handlers: List[Callable[[BaseError], None]] = []

    def add_handler(self, handler: Callable[[BaseError], None]) -> None:
        """Add error handler"""
        self._error_handlers.append(handler)

    async def report_error(self, error: BaseError) -> None:
        """Report an error"""
        # Increment count
        self._error_counts[error.code] = self._error_counts.get(error.code, 0) + 1

        # Log based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {error.message}", exc_info=error.cause)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {error.message}", exc_info=error.cause)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {error.message}")
        else:
            logger.info(f"Low severity error: {error.message}")

        # Call handlers
        for handler in self._error_handlers:
            try:
                handler(error)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")

        # Report to external service if enabled
        if self.enable_reporting and error.severity.value >= self.report_threshold.value:
            await self._send_to_external_service(error)

    async def _send_to_external_service(self, error: BaseError) -> None:
        """Send error to external monitoring service"""
        # Implementation would depend on your monitoring service
        # (e.g., Sentry, DataDog, etc.)
        pass

    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        return {code.value: count for code, count in self._error_counts.items()}


class ErrorHandlerMiddleware:
    """Middleware for handling errors consistently"""

    def __init__(
        self,
        debug: bool = False,
        include_traceback: bool = False,
        custom_handlers: Optional[Dict[Type[Exception], Callable]] = None,
    ):
        self.debug = debug
        self.include_traceback = include_traceback
        self.custom_handlers = custom_handlers or {}
        self.reporter = ErrorReporter()

    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Handle requests and errors"""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            return response

        except HTTPException as e:
            # FastAPI HTTP exceptions
            return self._handle_http_exception(e, request, request_id)

        except BaseError as e:
            # FastAPI-Easy custom errors
            e.context.request_id = request_id
            await self.reporter.report_error(e)
            return self._create_error_response(e)

        except ValidationError as e:
            # Pydantic validation errors
            error = ValidationError(
                message="Validation failed", details={"validation_errors": e.errors()}
            )
            error.context.request_id = request_id
            await self.reporter.report_error(error)
            return self._create_error_response(error)

        except Exception as e:
            # Unexpected errors
            error = BaseError(
                message="Internal server error",
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                cause=e,
                severity=ErrorSeverity.CRITICAL,
            )
            error.context.request_id = request_id
            error.context.update_from_request(request)
            await self.reporter.report_error(error)
            return self._create_error_response(error)

    def _handle_http_exception(
        self, exc: HTTPException, request: Request, request_id: str
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions"""
        # Map HTTP status to error code
        error_code_map = {
            status.HTTP_400_BAD_REQUEST: ErrorCode.BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
            status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
            status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
            status.HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_ERROR,
            status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.RATE_LIMITED,
        }

        code = error_code_map.get(exc.status_code, ErrorCode.BAD_REQUEST)

        error = BaseError(
            message=exc.detail,
            code=code,
            status_code=exc.status_code,
            context=ErrorContext(request_id=request_id),
        )
        error.context.update_from_request(request)

        return self._create_error_response(error)

    def _create_error_response(self, error: BaseError) -> JSONResponse:
        """Create error response"""
        include_traceback = self.include_traceback or self.debug
        response_data = error.to_dict(include_traceback=include_traceback)

        # Add debug info if enabled
        if self.debug:
            response_data["debug"] = {
                "error_class": error.__class__.__name__,
                "severity": error.severity.value,
            }

        return JSONResponse(status_code=error.status_code, content=response_data)


def create_error_handler(
    error_code: ErrorCode,
    status_code: int,
    default_message: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
) -> Callable:
    """Create a standardized error handler function"""

    def handler(
        message: Optional[str] = None, details: Optional[Dict[str, Any]] = None, **kwargs
    ) -> BaseError:
        return BaseError(
            message=message or default_message,
            code=error_code,
            status_code=status_code,
            details=details,
            severity=severity,
            **kwargs,
        )

    return handler


# Common error handlers
handle_not_found = create_error_handler(
    ErrorCode.NOT_FOUND, status.HTTP_404_NOT_FOUND, "Resource not found", ErrorSeverity.LOW
)

handle_conflict = create_error_handler(
    ErrorCode.CONFLICT, status.HTTP_409_CONFLICT, "Resource conflict", ErrorSeverity.MEDIUM
)

handle_validation_error = create_error_handler(
    ErrorCode.VALIDATION_ERROR,
    status.HTTP_422_UNPROCESSABLE_ENTITY,
    "Validation failed",
    ErrorSeverity.LOW,
)

handle_auth_error = create_error_handler(
    ErrorCode.AUTHENTICATION_FAILED,
    status.HTTP_401_UNAUTHORIZED,
    "Authentication required",
    ErrorSeverity.HIGH,
)


def validate_and_raise(
    data: Dict[str, Any], schema: Type[BaseModel], error_message: Optional[str] = None
) -> BaseModel:
    """Validate data and raise ValidationError if invalid"""
    try:
        return schema(**data)
    except ValidationError as e:
        raise ValidationError(
            message=error_message or "Validation failed", details={"validation_errors": e.errors()}
        )


def check_permission(user_permissions: List[str], required_permissions: List[str]) -> None:
    """Check if user has required permissions"""
    if not all(perm in user_permissions for perm in required_permissions):
        raise AuthorizationError(
            message="Insufficient permissions", permissions_required=required_permissions
        )


def check_rate_limit(
    current_usage: int, limit: int, window: int, retry_after: Optional[int] = None
) -> None:
    """Check rate limit and raise error if exceeded"""
    if current_usage >= limit:
        raise RateLimitError(
            message=f"Rate limit exceeded ({limit}/{window}s)",
            limit=limit,
            window=window,
            retry_after=retry_after,
        )


async def safe_execute(
    func: Callable,
    *args,
    error_message: str = "Operation failed",
    error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
    **kwargs,
) -> Any:
    """Safely execute function with error handling"""
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        raise BaseError(
            message=error_message, code=error_code, cause=e, details={"function": func.__name__}
        )


@asynccontextmanager
async def error_boundary(
    error_message: str = "Operation failed",
    error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
    reraise: bool = True,
):
    """Context manager for catching and handling errors"""
    try:
        yield
    except Exception as e:
        error = BaseError(message=error_message, code=error_code, cause=e)
        if reraise:
            raise error
        else:
            logger.error(f"Error in boundary: {error_message}", exc_info=e)


# Extend ErrorContext to extract request information
def update_from_request(self, request: Request) -> None:
    """Update context from request"""
    self.endpoint = str(request.url.path)
    self.method = request.method
    self.ip_address = request.client.host if request.client else None
    self.user_agent = request.headers.get("user-agent")
    self.additional_data["query_params"] = dict(request.query_params)
    self.additional_data["headers"] = dict(request.headers)


ErrorContext.update_from_request = update_from_request


# Response models for API documentation
class ErrorDetail(BaseModel):
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    severity: str = Field(..., description="Error severity")
    timestamp: str = Field(..., description="Error timestamp (ISO format)")
    request_id: Optional[str] = Field(None, description="Request ID")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    error: ErrorDetail = Field(..., description="Error details")


class ValidationErrorDetail(BaseModel):
    field: str = Field(..., description="Field with validation error")
    message: str = Field(..., description="Validation error message")
    value: Optional[Any] = Field(None, description="Invalid value")


class ValidationErrorResponse(BaseModel):
    error: ErrorDetail = Field(..., description="Error details")
    validation_errors: List[ValidationErrorDetail] = Field(
        ..., description="Specific validation errors"
    )
