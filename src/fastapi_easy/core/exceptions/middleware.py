"""
FastAPI middleware for comprehensive error handling.

This module provides middleware for automatically catching and formatting
exceptions in FastAPI applications with proper HTTP responses.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .base import ErrorContext, ErrorSeverity, FastAPIEasyException
from .formatters import ErrorFormatter, ResponseFormat, default_formatter
from .handlers import ErrorHandler, default_error_handler

logger = logging.getLogger(__name__)


class ErrorMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for comprehensive error handling.

    Automatically catches exceptions and returns properly formatted
    error responses with appropriate HTTP status codes.
    """

    def __init__(
        self,
        app,
        *,
        formatter: Optional[ErrorFormatter] = None,
        error_handler: Optional[ErrorHandler] = None,
        response_format: ResponseFormat = ResponseFormat.STANDARD,
        include_traceback: bool = False,
        log_errors: bool = True,
        handle_generic_exceptions: bool = True,
        skip_paths: Optional[List[str]] = None,
        custom_handlers: Optional[Dict[type, Callable]] = None,
    ):
        """
        Initialize error middleware.

        Args:
            app: FastAPI application instance
            formatter: Error formatter instance
            error_handler: Error handler instance
            response_format: Default response format
            include_traceback: Include tracebacks in development
            log_errors: Whether to log errors
            handle_generic_exceptions: Handle non-FastAPIEasy exceptions
            skip_paths: Paths to skip error handling
            custom_handlers: Custom exception handlers
        """
        super().__init__(app)

        self.formatter = formatter or default_formatter
        self.error_handler = error_handler or default_error_handler
        self.response_format = response_format
        self.include_traceback = include_traceback
        self.log_errors = log_errors
        self.handle_generic_exceptions = handle_generic_exceptions
        self.skip_paths = skip_paths or []
        self.custom_handlers = custom_handlers or {}

        # Determine response format based on environment
        if self.include_traceback:
            self.response_format = ResponseFormat.DEVELOPMENT

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and handle any exceptions.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            HTTP response with error handling applied
        """
        # Skip error handling for certain paths
        if self._should_skip_path(request):
            return await call_next(request)

        # Create error context
        context = self._create_error_context(request)

        try:
            response = await call_next(request)
            return response

        except FastAPIEasyException as exc:
            # Update exception with request context
            exc.context = context

            # Log error if enabled
            if self.log_errors:
                await self._log_exception(exc, request)

            # Handle with custom handler if available
            if type(exc) in self.custom_handlers:
                try:
                    custom_response = await self._handle_custom_exception(exc, request)
                    if custom_response:
                        return custom_response
                except Exception as handler_error:
                    logger.error(f"Custom exception handler failed: {handler_error}")

            # Format and return error response
            return self._format_error_response(exc, request)

        except Exception as exc:
            if not self.handle_generic_exceptions:
                # Re-raise if not handling generic exceptions
                raise

            # Convert to FastAPIEasyException
            fastapi_exc = FastAPIEasyException(
                message="An unexpected error occurred",
                cause=exc,
                should_track=True,
                include_traceback=self.include_traceback,
            )
            fastapi_exc.context = context

            # Log error if enabled
            if self.log_errors:
                await self._log_exception(fastapi_exc, request)

            # Try to handle with error handler
            try:
                result = await self.error_handler.handle_error_async(
                    fastapi_exc,
                    context=context,
                )
                if result is not None:
                    # If handler returned a result, format it as success response
                    return JSONResponse(
                        content=result,
                        status_code=status.HTTP_200_OK,
                    )
            except Exception as handler_error:
                logger.error(f"Error handler failed: {handler_error}")

            # Return generic error response
            return self._format_error_response(fastapi_exc, request)

    def _should_skip_path(self, request: Request) -> bool:
        """Check if path should be skipped."""
        path = request.url.path
        return any(skip_path in path for skip_path in self.skip_paths)

    def _create_error_context(self, request: Request) -> ErrorContext:
        """Create error context from request."""
        # Extract user ID from request (implementation dependent)
        user_id = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)

        # Extract request ID from headers
        request_id = request.headers.get("X-Request-ID")

        return ErrorContext(
            request_id=request_id,
            user_id=user_id,
            endpoint=request.url.path,
            method=request.method,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
            resource=None,  # Can be set by specific handlers
            action=None,  # Can be set by specific handlers
        )

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request."""
        # Check for forwarded IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Return client host
        if hasattr(request, "client") and request.client:
            return request.client.host

        return None

    async def _log_exception(self, exception: FastAPIEasyException, request: Request):
        """Log exception with request context."""
        log_data = {
            "exception_type": type(exception).__name__,
            "error_code": exception.code,
            "status_code": exception.status_code,
            "request": {
                "method": request.method,
                "url": str(request.url),
                "path_params": dict(request.path_params),
                "query_params": dict(request.query_params),
            },
        }

        if exception.context:
            log_data["context"] = exception.context.to_dict()

        if exception.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {exception}", extra=log_data, exc_info=exception)
        elif exception.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {exception}", extra=log_data, exc_info=exception)
        elif exception.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {exception}", extra=log_data)
        else:
            logger.info(f"Low severity error: {exception}", extra=log_data)

    async def _handle_custom_exception(
        self, exception: FastAPIEasyException, request: Request
    ) -> Optional[Response]:
        """Handle exception with custom handler."""
        handler = self.custom_handlers.get(type(exception))
        if handler:
            try:
                if hasattr(handler, "__call__") and not asyncio.iscoroutinefunction(handler):
                    result = handler(exception, request)
                else:
                    result = await handler(exception, request)

                if isinstance(result, Response):
                    return result
                elif result is not None:
                    return JSONResponse(content=result, status_code=exception.status_code)
            except Exception as e:
                logger.error(f"Custom handler failed: {e}")
                return None

        return None

    def _format_error_response(self, exception: FastAPIEasyException, request: Request) -> Response:
        """Format exception into HTTP response."""
        # Adjust format based on environment and exception severity
        format_type = self.response_format
        if self.include_traceback or exception.severity == ErrorSeverity.CRITICAL:
            format_type = ResponseFormat.DEVELOPMENT

        # Create response
        error_response = self.formatter.create_json_response(
            exception=exception,
            format_type=format_type,
            request=request,
            headers={
                "X-Error-Severity": exception.severity.value,
                "X-Error-Category": exception.category.value,
            },
        )

        return error_response


class SecurityErrorMiddleware(ErrorMiddleware):
    """
    Error middleware with enhanced security features.

    Adds additional security headers and sanitizes error messages
    to prevent information disclosure.
    """

    def __init__(
        self,
        app,
        *,
        security_headers: bool = True,
        sanitize_errors: bool = True,
        max_error_detail: int = 1000,
        **kwargs,
    ):
        """
        Initialize security error middleware.

        Args:
            app: FastAPI application instance
            security_headers: Add security headers to responses
            sanitize_errors: Sanitize error messages for security
            max_error_detail: Maximum error detail length
            **kwargs: Additional arguments for ErrorMiddleware
        """
        super().__init__(app, **kwargs)

        self.security_headers = security_headers
        self.sanitize_errors = sanitize_errors
        self.max_error_detail = max_error_detail

    def _format_error_response(self, exception: FastAPIEasyException, request: Request) -> Response:
        """Format error response with security enhancements."""
        # Sanitize error message if enabled
        if self.sanitize_errors:
            exception = self._sanitize_exception(exception)

        # Get base response
        response = super()._format_error_response(exception, request)

        # Add security headers if enabled
        if self.security_headers:
            self._add_security_headers(response, exception)

        return response

    def _sanitize_exception(self, exception: FastAPIEasyException) -> FastAPIEasyException:
        """Sanitize exception to prevent information disclosure."""
        # Truncate long messages
        if len(exception.message) > self.max_error_detail:
            exception.message = exception.message[: self.max_error_detail] + "..."

        # Remove sensitive information from details
        if exception.details and exception.details.debug_info:
            sensitive_keys = ["password", "token", "secret", "key", "credential"]
            for key in list(exception.details.debug_info.keys()):
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    exception.details.debug_info[key] = "***"

        return exception

    def _add_security_headers(self, response: Response, exception: FastAPIEasyException):
        """Add security headers to error response."""
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        # Add CSP header for high severity errors
        if exception.severity == ErrorSeverity.CRITICAL:
            headers["Content-Security-Policy"] = "default-src 'self'"

        for key, value in headers.items():
            response.headers[key] = value


class MonitoringErrorMiddleware(ErrorMiddleware):
    """
    Error middleware with monitoring and metrics collection.

    Integrates with external monitoring systems and collects
    detailed error metrics.
    """

    def __init__(
        self,
        app,
        *,
        metrics_collector: Optional[Callable] = None,
        alert_threshold: int = 100,
        time_window: int = 300,  # 5 minutes
        **kwargs,
    ):
        """
        Initialize monitoring error middleware.

        Args:
            app: FastAPI application instance
            metrics_collector: Function to collect metrics
            alert_threshold: Error count threshold for alerts
            time_window: Time window for threshold check (seconds)
            **kwargs: Additional arguments for ErrorMiddleware
        """
        super().__init__(app, **kwargs)

        self.metrics_collector = metrics_collector
        self.alert_threshold = alert_threshold
        self.time_window = time_window
        self.error_counts: List[float] = []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with monitoring."""
        try:
            response = await super().dispatch(request, call_next)

            # Check if response was an error
            if response.status_code >= 400:
                self._record_error()

            # Check alert threshold
            self._check_alert_threshold()

            return response

        except Exception:
            self._record_error()
            self._check_alert_threshold()
            raise

    def _record_error(self):
        """Record an error occurrence."""
        import time

        current_time = time.time()
        self.error_counts.append(current_time)

        # Remove old errors outside time window
        cutoff_time = current_time - self.time_window
        self.error_counts = [t for t in self.error_counts if t > cutoff_time]

    def _check_alert_threshold(self):
        """Check if error threshold is exceeded and trigger alert."""
        if len(self.error_counts) >= self.alert_threshold:
            self._trigger_alert()

    def _trigger_alert(self):
        """Trigger alert for high error rate."""
        logger.critical(
            f"High error rate detected: {len(self.error_counts)} errors in {self.time_window}s",
            extra={
                "alert_type": "high_error_rate",
                "error_count": len(self.error_counts),
                "time_window": self.time_window,
                "threshold": self.alert_threshold,
            },
        )

        # Send metrics if collector is configured
        if self.metrics_collector:
            try:
                self.metrics_collector(
                    {
                        "metric_type": "error_rate_alert",
                        "error_count": len(self.error_counts),
                        "threshold": self.alert_threshold,
                    }
                )
            except Exception as e:
                logger.error(f"Metrics collector failed: {e}")


# Utility function to add error middleware to FastAPI app
def add_error_middleware(
    app,
    *,
    formatter: Optional[ErrorFormatter] = None,
    error_handler: Optional[ErrorHandler] = None,
    response_format: ResponseFormat = ResponseFormat.STANDARD,
    security_headers: bool = True,
    monitor_errors: bool = False,
    **kwargs,
) -> None:
    """
    Add error handling middleware to FastAPI application.

    Args:
        app: FastAPI application instance
        formatter: Error formatter instance
        error_handler: Error handler instance
        response_format: Default response format
        security_headers: Whether to add security headers
        monitor_errors: Whether to enable error monitoring
        **kwargs: Additional middleware arguments
    """
    if monitor_errors:
        middleware_class = MonitoringErrorMiddleware
    elif security_headers:
        middleware_class = SecurityErrorMiddleware
    else:
        middleware_class = ErrorMiddleware

    app.add_middleware(
        middleware_class,
        formatter=formatter,
        error_handler=error_handler,
        response_format=response_format,
        security_headers=security_headers,
        **kwargs,
    )
