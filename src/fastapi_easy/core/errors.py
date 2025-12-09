"""Error handling system for FastAPI-Easy"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional


class ErrorCode(str, Enum):
    """Standard error codes"""

    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    BAD_REQUEST = "BAD_REQUEST"
    TIMEOUT = "TIMEOUT"
    CONNECTION_ERROR = "CONNECTION_ERROR"


class AppError(Exception):
    """Base application error class

    All application errors should inherit from this class.
    """

    code: ErrorCode
    status_code: int
    message: str
    details: Dict[str, Any]

    def __init__(
        self,
        code: ErrorCode,
        status_code: int,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize AppError

        Args:
            code: Error code
            status_code: HTTP status code
            message: Error message
            details: Additional error details
        """
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }


class NotFoundError(AppError):
    """Resource not found error"""

    def __init__(self, resource: str, id: Any):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            message=f"{resource} with id {id} not found",
            details={"resource": resource, "id": str(id)},
        )


class ValidationError(AppError):
    """Validation error"""

    def __init__(self, field: str, message: str):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            message=f"Validation error in field '{field}'",
            details={"field": field, "message": message},
        )


class PermissionDeniedError(AppError):
    """Permission denied error"""

    def __init__(self, action: str, reason: Optional[str] = None):
        super().__init__(
            code=ErrorCode.PERMISSION_DENIED,
            status_code=403,
            message=f"Permission denied for action '{action}'",
            details={"action": action, "reason": reason},
        )


class ConflictError(AppError):
    """Resource conflict error"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.CONFLICT,
            status_code=409,
            message=message,
            details=details,
        )


class UnauthorizedError(AppError):
    """Unauthorized error"""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            code=ErrorCode.UNAUTHORIZED,
            status_code=401,
            message=message,
        )


class BadRequestError(AppError):
    """Bad request error"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code=ErrorCode.BAD_REQUEST,
            status_code=400,
            message=message,
            details=details,
        )
