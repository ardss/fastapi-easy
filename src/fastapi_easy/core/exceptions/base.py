"""
Base exception classes and utilities for FastAPI-Easy.

This module provides the foundation for all FastAPI-Easy exceptions, including:
- Base exception class with rich error information
- Error context management
- Error severity and classification
- Error tracking and correlation
- Error response formatting
"""

from __future__ import annotations

import logging
import threading
import traceback
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Type, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="FastAPIEasyException")


class ErrorSeverity(str, Enum):
    """Error severity levels for prioritization and alerting."""

    LOW = "low"  # Minor issues, doesn't affect functionality
    MEDIUM = "medium"  # Degraded functionality, workarounds available
    HIGH = "high"  # Significant impact, partial system outage
    CRITICAL = "critical"  # Complete failure, requires immediate attention


class ErrorCategory(str, Enum):
    """Error categories for classification and routing."""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATABASE = "database"
    MIGRATION = "migration"
    CONFIGURATION = "configuration"
    PERMISSION = "permission"
    NETWORK = "network"
    EXTERNAL_SERVICE = "external_service"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    SECURITY = "security"


class ErrorCode(str, Enum):
    """Standardized error codes for client applications."""

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
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Database errors
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_TIMEOUT = "DATABASE_TIMEOUT"
    DATABASE_CONSTRAINT_ERROR = "DATABASE_CONSTRAINT_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    DATABASE_TRANSACTION_ERROR = "DATABASE_TRANSACTION_ERROR"
    DATABASE_MIGRATION_ERROR = "DATABASE_MIGRATION_ERROR"
    DATABASE_POOL_ERROR = "DATABASE_POOL_ERROR"

    # Authentication/Authorization errors
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_MISSING = "TOKEN_MISSING"
    CREDENTIALS_INVALID = "CREDENTIALS_INVALID"
    ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
    ACCOUNT_EXPIRED = "ACCOUNT_EXPIRED"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # Migration errors
    MIGRATION_NOT_FOUND = "MIGRATION_NOT_FOUND"
    MIGRATION_EXECUTION_FAILED = "MIGRATION_EXECUTION_FAILED"
    MIGRATION_CONFLICT = "MIGRATION_CONFLICT"
    MIGRATION_DEPENDENCY_ERROR = "MIGRATION_DEPENDENCY_ERROR"
    MIGRATION_ROLLBACK_FAILED = "MIGRATION_ROLLBACK_FAILED"
    MIGRATION_VALIDATION_FAILED = "MIGRATION_VALIDATION_FAILED"

    # Configuration errors
    MISSING_CONFIGURATION = "MISSING_CONFIGURATION"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    ENVIRONMENT_CONFIGURATION_ERROR = "ENVIRONMENT_CONFIGURATION_ERROR"
    SECURITY_CONFIGURATION_ERROR = "SECURITY_CONFIGURATION_ERROR"

    # Permission errors
    RESOURCE_PERMISSION_DENIED = "RESOURCE_PERMISSION_DENIED"
    ACTION_PERMISSION_DENIED = "ACTION_PERMISSION_DENIED"
    ROLE_PERMISSION_DENIED = "ROLE_PERMISSION_DENIED"
    SCOPE_PERMISSION_DENIED = "SCOPE_PERMISSION_DENIED"

    # Validation errors
    FIELD_VALIDATION_ERROR = "FIELD_VALIDATION_ERROR"
    TYPE_VALIDATION_ERROR = "TYPE_VALIDATION_ERROR"
    FORMAT_VALIDATION_ERROR = "FORMAT_VALIDATION_ERROR"
    RANGE_VALIDATION_ERROR = "RANGE_VALIDATION_ERROR"
    REQUIRED_FIELD_ERROR = "REQUIRED_FIELD_ERROR"
    UNIQUE_CONSTRAINT_ERROR = "UNIQUE_CONSTRAINT_ERROR"
    BUSINESS_RULE_VALIDATION_ERROR = "BUSINESS_RULE_VALIDATION_ERROR"


@dataclass
class ErrorContext:
    """Context information for errors to aid in debugging and tracking."""

    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary, excluding sensitive fields."""
        return {
            "request_id": self.request_id,
            "user_id": self._sanitize_user_id(),
            "session_id": self.session_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "ip_address": self._ip_address if self._should_include_ip() else None,
            "user_agent": self.user_agent,
            "resource": self.resource,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "metadata": self._sanitize_metadata(),
        }

    def _sanitize_user_id(self) -> Optional[str]:
        """Partially mask user ID for privacy."""
        if not self.user_id or len(self.user_id) < 8:
            return self.user_id
        return f"{self.user_id[:4]}***{self.user_id[-4:]}"

    def _should_include_ip(self) -> bool:
        """Determine if IP address should be included (exclude in production)."""
        # In production, you might want to exclude IP addresses for privacy
        return True  # Adjust based on your requirements

    @property
    def _ip_address(self) -> Optional[str]:
        """Mask IP address for privacy."""
        if not self.ip_address:
            return None
        parts = self.ip_address.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.{parts[3]}"
        return "***"

    def _sanitize_metadata(self) -> Dict[str, Any]:
        """Remove sensitive information from metadata."""
        sensitive_keys = {"password", "token", "secret", "key", "credential"}
        sanitized = {}
        for key, value in self.metadata.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***"
            else:
                sanitized[key] = value
        return sanitized


@dataclass
class ErrorDetails:
    """Detailed error information with suggestions and context."""

    field: Optional[str] = None
    value: Optional[Any] = None
    constraint: Optional[str] = None
    suggestion: Optional[str] = None
    documentation_url: Optional[str] = None
    error_code: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert details to dictionary."""
        return {
            "field": self.field,
            "value": self.value,
            "constraint": self.constraint,
            "suggestion": self.suggestion,
            "documentation_url": self.documentation_url,
            "error_code": self.error_code,
            "debug_info": self.debug_info,
        }


class ErrorTracker:
    """Thread-safe error tracking for correlation and monitoring."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._error_counts = {}
                    cls._instance._recent_errors = []
                    cls._instance._max_recent_errors = 1000
        return cls._instance

    def track_error(self, exception: FastAPIEasyException) -> None:
        """Track an error occurrence."""
        error_key = f"{exception.__class__.__name__}:{exception.code}"

        with self._lock:
            # Update counts
            self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

            # Add to recent errors
            self._recent_errors.append(
                {
                    "timestamp": datetime.utcnow(),
                    "exception_type": exception.__class__.__name__,
                    "code": exception.code,
                    "message": exception.message,
                    "severity": exception.severity,
                    "category": exception.category,
                    "context": exception.context,
                }
            )

            # Trim recent errors if needed
            if len(self._recent_errors) > self._max_recent_errors:
                self._recent_errors = self._recent_errors[-self._max_recent_errors :]

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        with self._lock:
            return {
                "error_counts": dict(self._error_counts),
                "total_errors": sum(self._error_counts.values()),
                "unique_error_types": len(self._error_counts),
                "recent_errors_count": len(self._recent_errors),
            }

    def get_recent_errors(self, limit: int = 100) -> list:
        """Get recent errors."""
        with self._lock:
            return self._recent_errors[-limit:]


class FastAPIEasyException(Exception):
    """
    Base exception class for all FastAPI-Easy exceptions.

    Provides structured error information, context tracking, and
    standardized error responses.
    """

    def __init__(
        self,
        message: str,
        code: Union[str, ErrorCode] = None,
        status_code: int = 500,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[ErrorDetails] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
        should_track: bool = True,
        include_traceback: bool = False,
    ):
        """
        Initialize FastAPI-Easy exception.

        Args:
            message: Human-readable error message
            code: Error code for programmatic handling
            status_code: HTTP status code for responses
            category: Error category for classification
            severity: Error severity for prioritization
            details: Additional error details
            context: Error context information
            cause: Original exception that caused this error
            should_track: Whether to track this error
            include_traceback: Whether to include traceback in debug info
        """
        super().__init__(message)

        self.message = message
        self.code = (
            code.value if isinstance(code, ErrorCode) else code or self.__class__.__name__.upper()
        )
        self.status_code = status_code
        self.category = category
        self.severity = severity
        self.details = details or ErrorDetails()
        self.context = context or ErrorContext()
        self.cause = cause
        self.should_track = should_track
        self.include_traceback = include_traceback

        # Track error if enabled
        if self.should_track:
            ErrorTracker().track_error(self)

        # Log error
        self._log_error()

    def _log_error(self) -> None:
        """Log the error with appropriate level based on severity."""
        log_data = {
            "error_code": self.code,
            "error_category": self.category.value,
            "error_severity": self.severity.value,
            "details": self.details.to_dict(),
            "context": self.context.to_dict(),
        }

        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {self.message}", extra=log_data, exc_info=self)
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {self.message}", extra=log_data, exc_info=self)
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {self.message}", extra=log_data)
        else:
            logger.info(f"Low severity error: {self.message}", extra=log_data)

    def to_dict(self, include_debug: bool = False) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API responses.

        Args:
            include_debug: Whether to include debug information

        Returns:
            Dictionary representation of the error
        """
        error_dict = {
            "error": {
                "code": self.code,
                "message": self.message,
                "category": self.category.value,
                "severity": self.severity.value,
                "status_code": self.status_code,
                "context": self.context.to_dict(),
            }
        }

        # Add details if present
        if any([self.details.field, self.details.suggestion, self.details.documentation_url]):
            error_dict["error"]["details"] = self.details.to_dict()

        # Add debug information in development or if explicitly requested
        if include_debug or self.include_traceback:
            debug_info = {
                "exception_type": self.__class__.__name__,
                "correlation_id": self.context.correlation_id,
            }

            if self.cause:
                debug_info["cause"] = str(self.cause)
                debug_info["cause_type"] = type(self.cause).__name__

            if include_debug:
                debug_info["traceback"] = traceback.format_exc()

            error_dict["error"]["debug"] = debug_info

        return error_dict

    def with_context(self, **kwargs) -> FastAPIEasyException:
        """Add or update context information."""
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                self.context.metadata[key] = value
        return self

    def with_details(
        self,
        field: str = None,
        value: Any = None,
        constraint: str = None,
        suggestion: str = None,
        documentation_url: str = None,
        debug_info: Dict[str, Any] = None,
    ) -> FastAPIEasyException:
        """Add or update error details."""
        if field is not None:
            self.details.field = field
        if value is not None:
            self.details.value = value
        if constraint is not None:
            self.details.constraint = constraint
        if suggestion is not None:
            self.details.suggestion = suggestion
        if documentation_url is not None:
            self.details.documentation_url = documentation_url
        if debug_info is not None:
            self.details.debug_info = debug_info
        return self

    def __str__(self) -> str:
        """String representation of the exception."""
        return f"{self.__class__.__name__}: {self.message} (Code: {self.code}, Status: {self.status_code})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"code='{self.code}', "
            f"status_code={self.status_code}, "
            f"category={self.category}, "
            f"severity={self.severity}"
            f")"
        )


@contextmanager
def error_context(**context_kwargs):
    """Context manager for automatically setting error context."""
    context = ErrorContext(**context_kwargs)
    try:
        yield context
    except FastAPIEasyException as e:
        # Merge contexts if exception already has one
        if e.context and e.context != context:
            for key, value in context.__dict__.items():
                if value is not None and not getattr(e.context, key, None):
                    setattr(e.context, key, value)
        else:
            e.context = context
        raise
    except Exception as e:
        # Wrap non-FastAPIEasy exceptions
        raise FastAPIEasyException(
            message=str(e),
            code="WRAPPED_EXCEPTION",
            context=context,
            cause=e,
        ) from e


def create_exception_class(
    name: str,
    code: str = None,
    status_code: int = 500,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
) -> Type[FastAPIEasyException]:
    """
    Dynamically create an exception class.

    Args:
        name: Name of the exception class
        code: Default error code
        status_code: Default HTTP status code
        category: Default error category
        severity: Default error severity

    Returns:
        New exception class
    """
    class_attrs = {
        "__module__": __name__,
        "default_code": code or name.upper(),
        "default_status_code": status_code,
        "default_category": category,
        "default_severity": severity,
    }

    def __init__(self, message: str, **kwargs):
        # Apply defaults if not provided
        kwargs.setdefault("code", kwargs.get("code", self.default_code))
        kwargs.setdefault("status_code", kwargs.get("status_code", self.default_status_code))
        kwargs.setdefault("category", kwargs.get("category", self.default_category))
        kwargs.setdefault("severity", kwargs.get("severity", self.default_severity))
        super(self.__class__, self).__init__(message, **kwargs)

    class_attrs["__init__"] = __init__

    return type(name, (FastAPIEasyException,), class_attrs)
