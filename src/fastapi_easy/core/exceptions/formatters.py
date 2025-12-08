"""
Error response formatting utilities for FastAPI-Easy.

This module provides utilities for formatting error responses
with consistent structure, security considerations, and localization support.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from fastapi import Request
from fastapi.responses import JSONResponse

from .base import ErrorCode, FastAPIEasyException


class ResponseFormat(str, Enum):
    """Error response format options."""

    STANDARD = "standard"
    DETAILED = "detailed"
    MINIMAL = "minimal"
    DEVELOPMENT = "development"
    API_PROBLEM = "api_problem"  # RFC 7807 Problem Details for HTTP APIs


class ErrorFormatter:
    """
    Utility class for formatting error responses.

    Provides consistent error response formatting across different
    environments and with different detail levels.
    """

    def __init__(
        self,
        default_format: ResponseFormat = ResponseFormat.STANDARD,
        include_stack_trace: bool = False,
        localize: bool = True,
        default_locale: str = "en",
    ):
        """
        Initialize error formatter.

        Args:
            default_format: Default response format
            include_stack_trace: Whether to include stack traces in responses
            localize: Whether to localize error messages
            default_locale: Default locale for localization
        """
        self.default_format = default_format
        self.include_stack_trace = include_stack_trace
        self.localize = localize
        self.default_locale = default_locale

        # Localization messages (simplified example)
        self.messages = {
            "en": {
                "internal_error": "An internal error occurred",
                "not_found": "Resource not found",
                "validation_error": "Validation failed",
                "auth_error": "Authentication required",
                "permission_error": "Permission denied",
            },
            "es": {
                "internal_error": "Ocurrió un error interno",
                "not_found": "Recurso no encontrado",
                "validation_error": "La validación falló",
                "auth_error": "Autenticación requerida",
                "permission_error": "Permiso denegado",
            },
        }

    def format_error(
        self,
        exception: FastAPIEasyException,
        format_type: Optional[ResponseFormat] = None,
        request: Optional[Request] = None,
        locale: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Format an exception into a response dictionary.

        Args:
            exception: The exception to format
            format_type: Response format type
            request: HTTP request for context
            locale: Locale for localization

        Returns:
            Formatted error response dictionary
        """
        format_type = format_type or self.default_format
        locale = locale or self.default_locale

        if format_type == ResponseFormat.MINIMAL:
            return self._format_minimal(exception)
        elif format_type == ResponseFormat.STANDARD:
            return self._format_standard(exception, request, locale)
        elif format_type == ResponseFormat.DETAILED:
            return self._format_detailed(exception, request, locale)
        elif format_type == ResponseFormat.DEVELOPMENT:
            return self._format_development(exception, request, locale)
        elif format_type == ResponseFormat.API_PROBLEM:
            return self._format_api_problem(exception, request, locale)
        else:
            return self._format_standard(exception, request, locale)

    def _format_minimal(self, exception: FastAPIEasyException) -> Dict[str, Any]:
        """Format error with minimal information for production."""
        return {
            "error": {
                "code": exception.code,
                "message": self._get_safe_message(exception),
            }
        }

    def _format_standard(
        self,
        exception: FastAPIEasyException,
        request: Optional[Request] = None,
        locale: str = "en",
    ) -> Dict[str, Any]:
        """Format error with standard information."""
        error_dict = {
            "error": {
                "code": exception.code,
                "message": self._localize_message(exception.message, locale),
                "status": exception.status_code,
                "category": exception.category.value,
            }
        }

        # Add context information
        if exception.context:
            error_dict["error"]["context"] = {
                "request_id": exception.context.request_id,
                "correlation_id": exception.context.correlation_id,
                "timestamp": exception.context.timestamp.isoformat(),
            }

        # Add details if present
        if exception.details and (
            exception.details.field
            or exception.details.suggestion
            or exception.details.documentation_url
        ):
            error_dict["error"]["details"] = exception.details.to_dict()

        return error_dict

    def _format_detailed(
        self,
        exception: FastAPIEasyException,
        request: Optional[Request] = None,
        locale: str = "en",
    ) -> Dict[str, Any]:
        """Format error with detailed information."""
        error_dict = self._format_standard(exception, request, locale)

        # Add request information
        if request:
            error_dict["error"]["request"] = {
                "method": request.method,
                "url": str(request.url),
                "path_params": dict(request.path_params),
            }

        # Add full context
        if exception.context:
            error_dict["error"]["context"] = exception.context.to_dict()

        return error_dict

    def _format_development(
        self,
        exception: FastAPIEasyException,
        request: Optional[Request] = None,
        locale: str = "en",
    ) -> Dict[str, Any]:
        """Format error with development-only information."""
        error_dict = self._format_detailed(exception, request, locale)

        # Add debug information
        debug_info = {
            "exception_type": exception.__class__.__name__,
            "exception_module": exception.__class__.__module__,
        }

        if exception.cause:
            debug_info["cause"] = {
                "type": type(exception.cause).__name__,
                "message": str(exception.cause),
            }

        if self.include_stack_trace:
            import traceback

            debug_info["stack_trace"] = traceback.format_exc()

        error_dict["error"]["debug"] = debug_info

        return error_dict

    def _format_api_problem(
        self,
        exception: FastAPIEasyException,
        request: Optional[Request] = None,
        locale: str = "en",
    ) -> Dict[str, Any]:
        """
        Format error according to RFC 7807 Problem Details for HTTP APIs.
        """
        problem = {
            "type": f"urn:fastapi-easy:errors:{exception.code.lower()}",
            "title": self._get_problem_title(exception),
            "status": exception.status_code,
            "detail": self._localize_message(exception.message, locale),
            "instance": exception.context.correlation_id,
        }

        # Add custom extensions
        if exception.category:
            problem["category"] = exception.category.value

        if exception.severity:
            problem["severity"] = exception.severity.value

        if request:
            problem["instance"] = f"{request.url.path}#{exception.context.correlation_id}"

        return problem

    def create_json_response(
        self,
        exception: FastAPIEasyException,
        format_type: Optional[ResponseFormat] = None,
        request: Optional[Request] = None,
        locale: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> JSONResponse:
        """
        Create a FastAPI JSONResponse from an exception.

        Args:
            exception: The exception to convert
            format_type: Response format type
            request: HTTP request for context
            locale: Locale for localization
            headers: Additional response headers

        Returns:
            FastAPI JSONResponse
        """
        error_dict = self.format_error(
            exception=exception,
            format_type=format_type,
            request=request,
            locale=locale,
        )

        # Default headers
        response_headers = {
            "Content-Type": "application/json",
            "X-Error-Code": exception.code,
            "X-Correlation-ID": exception.context.correlation_id,
        }

        # Add custom headers
        if headers:
            response_headers.update(headers)

        return JSONResponse(
            content=error_dict,
            status_code=exception.status_code,
            headers=response_headers,
        )

    def _get_safe_message(self, exception: FastAPIEasyException) -> str:
        """
        Get a safe message that doesn't leak sensitive information.

        In production, certain errors should return generic messages
        to prevent information disclosure.
        """
        # Map error codes to safe messages
        safe_messages = {
            ErrorCode.INTERNAL_SERVER_ERROR: "An internal error occurred",
            ErrorCode.DATABASE_ERROR: "A database error occurred",
            ErrorCode.DATABASE_CONNECTION_ERROR: "Database connection failed",
        }

        return safe_messages.get(exception.code, exception.message)

    def _localize_message(self, message: str, locale: str) -> str:
        """
        Localize error message if localization is enabled.

        Args:
            message: Original message
            locale: Target locale

        Returns:
            Localized message or original if not found
        """
        if not self.localize:
            return message

        # For this example, we'll use simple key-based localization
        # In a real implementation, you'd use a proper i18n library
        messages = self.messages.get(locale, self.messages.get("en", {}))

        # Try to find a matching key in the messages
        for key, localized_message in messages.items():
            if key.lower() in message.lower():
                return localized_message

        return message

    def _get_problem_title(self, exception: FastAPIEasyException) -> str:
        """
        Get the problem title for RFC 7807 format.
        """
        title_map = {
            ErrorCode.NOT_FOUND: "Resource Not Found",
            ErrorCode.VALIDATION_ERROR: "Validation Failed",
            ErrorCode.UNAUTHORIZED: "Unauthorized",
            ErrorCode.FORBIDDEN: "Forbidden",
            ErrorCode.INTERNAL_SERVER_ERROR: "Internal Server Error",
            ErrorCode.DATABASE_ERROR: "Database Error",
            ErrorCode.AUTHENTICATION_FAILED: "Authentication Failed",
            ErrorCode.PERMISSION_DENIED: "Permission Denied",
        }

        return title_map.get(exception.code, "Error")


class ErrorAggregator:
    """
    Utility for aggregating multiple errors into a single response.
    """

    def __init__(self, formatter: ErrorFormatter):
        self.formatter = formatter

    def aggregate_errors(
        self,
        errors: List[Union[FastAPIEasyException, Dict[str, Any]]],
        response_format: ResponseFormat = ResponseFormat.STANDARD,
    ) -> Dict[str, Any]:
        """
        Aggregate multiple errors into a single response.

        Args:
            errors: List of exceptions or error dictionaries
            response_format: Format for the aggregated response

        Returns:
            Aggregated error response
        """
        formatted_errors = []
        error_codes = set()
        status_codes = []

        for error in errors:
            if isinstance(error, FastAPIEasyException):
                formatted_error = self.formatter.format_error(error, response_format)
                error_codes.add(error.code)
                status_codes.append(error.status_code)
            elif isinstance(error, dict):
                formatted_error = error
                error_codes.add(error.get("code", "UNKNOWN"))
                status_codes.append(error.get("status", 500))
            else:
                # Convert generic exceptions
                exc = FastAPIEasyException(str(error))
                formatted_error = self.formatter.format_error(exc, response_format)
                error_codes.add(exc.code)
                status_codes.append(exc.status_code)

            formatted_errors.append(formatted_error)

        # Determine overall status code (use the highest)
        overall_status = max(status_codes) if status_codes else 500

        # Create aggregated response
        if response_format == ResponseFormat.API_PROBLEM:
            return {
                "type": "urn:fastapi-easy:errors:multiple",
                "title": "Multiple Errors",
                "status": overall_status,
                "detail": f"Multiple errors occurred: {', '.join(error_codes)}",
                "errors": formatted_errors,
            }
        else:
            return {
                "error": {
                    "code": "MULTIPLE_ERRORS",
                    "message": "Multiple errors occurred",
                    "status": overall_status,
                    "count": len(formatted_errors),
                    "errors": formatted_errors,
                }
            }


# Global formatter instance
default_formatter = ErrorFormatter()


# Convenience functions
def format_error_response(
    exception: FastAPIEasyException,
    format_type: Optional[ResponseFormat] = None,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    """Format an error response using the default formatter."""
    return default_formatter.format_error(
        exception=exception,
        format_type=format_type,
        request=request,
    )


def create_error_json_response(
    exception: FastAPIEasyException,
    format_type: Optional[ResponseFormat] = None,
    request: Optional[Request] = None,
) -> JSONResponse:
    """Create a JSON error response using the default formatter."""
    return default_formatter.create_json_response(
        exception=exception,
        format_type=format_type,
        request=request,
    )
