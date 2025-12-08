"""
Error handling utilities for FastAPI-Easy.

This module provides comprehensive error handling capabilities including
error processing, recovery strategies, and monitoring integration.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, TypeVar

from .base import (
    ErrorContext,
    ErrorSeverity,
    FastAPIEasyException,
)
from .database import DatabaseConnectionException, DatabaseException
from .formatters import ErrorFormatter, default_formatter
from .validation import ValidationException

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorHandlingStrategy(str, Enum):
    """Error handling strategies."""

    FAIL_FAST = "fail_fast"
    RETRY = "retry"
    FALLBACK = "fallback"
    IGNORE = "ignore"
    ESCALATE = "escalate"


@dataclass
class RetryConfig:
    """Configuration for retry logic."""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on: List[Type[Exception]] = field(
        default_factory=lambda: [
            DatabaseConnectionException,
            DatabaseException,
        ]
    )


@dataclass
class FallbackConfig:
    """Configuration for fallback logic."""

    fallback_func: Callable
    fallback_args: tuple = field(default_factory=tuple)
    fallback_kwargs: dict = field(default_factory=dict)
    execute_on: List[Type[Exception]] = field(
        default_factory=lambda: [
            DatabaseException,
            ValidationException,
        ]
    )


@dataclass
class ErrorMetrics:
    """Error handling metrics."""

    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    avg_resolution_time: float = 0.0
    last_error_time: Optional[datetime] = None


class ErrorHandler:
    """
    Comprehensive error handler with retry, fallback, and monitoring capabilities.
    """

    def __init__(
        self,
        formatter: Optional[ErrorFormatter] = None,
        track_metrics: bool = True,
        auto_recovery: bool = True,
    ):
        """
        Initialize error handler.

        Args:
            formatter: Error formatter for responses
            track_metrics: Whether to track error metrics
            auto_recovery: Whether to enable automatic error recovery
        """
        self.formatter = formatter or default_formatter
        self.track_metrics = track_metrics
        self.auto_recovery = auto_recovery

        # Error handling configurations
        self.retry_configs: Dict[Type[Exception], RetryConfig] = {}
        self.fallback_configs: Dict[Type[Exception], FallbackConfig] = {}
        self.error_handlers: Dict[Type[Exception], Callable] = {}

        # Metrics tracking
        self.metrics = ErrorMetrics()
        self._error_times: List[float] = []

    def configure_retry(
        self,
        exception_type: Type[Exception],
        config: RetryConfig,
    ):
        """Configure retry logic for a specific exception type."""
        self.retry_configs[exception_type] = config

    def configure_fallback(
        self,
        exception_type: Type[Exception],
        config: FallbackConfig,
    ):
        """Configure fallback logic for a specific exception type."""
        self.fallback_configs[exception_type] = config

    def register_handler(
        self,
        exception_type: Type[Exception],
        handler: Callable[[Exception], Any],
    ):
        """Register a custom error handler."""
        self.error_handlers[exception_type] = handler

    def handle_error(
        self,
        exception: Exception,
        context: Optional[ErrorContext] = None,
        strategy: Optional[ErrorHandlingStrategy] = None,
    ) -> Any:
        """
        Handle an error using configured strategies.

        Args:
            exception: The exception to handle
            context: Error context information
            strategy: Specific handling strategy

        Returns:
            Result of error handling (e.g., fallback value, retry result)
        """
        start_time = time.time()

        # Update context
        if context and isinstance(exception, FastAPIEasyException):
            exception.context = context

        # Track metrics
        if self.track_metrics:
            self._update_metrics(exception)

        # Log the error
        self._log_error(exception)

        # Try custom handler first
        for exc_type, handler in self.error_handlers.items():
            if isinstance(exception, exc_type):
                try:
                    return handler(exception)
                except Exception as handler_error:
                    logger.error(f"Custom error handler failed: {handler_error}")

        # Apply handling strategy
        if strategy == ErrorHandlingStrategy.IGNORE:
            return None
        elif strategy == ErrorHandlingStrategy.ESCALATE:
            self._escalate_error(exception)
            raise exception

        # Try retry
        if strategy in [None, ErrorHandlingStrategy.RETRY]:
            retry_result = self._try_retry(exception)
            if retry_result is not None:
                return retry_result

        # Try fallback
        if strategy in [None, ErrorHandlingStrategy.FALLBACK]:
            fallback_result = self._try_fallback(exception)
            if fallback_result is not None:
                return fallback_result

        # Default behavior: re-raise
        if isinstance(exception, FastAPIEasyException):
            raise exception
        else:
            raise FastAPIEasyException(
                message=str(exception),
                cause=exception,
            ) from exception

    async def handle_error_async(
        self,
        exception: Exception,
        context: Optional[ErrorContext] = None,
        strategy: Optional[ErrorHandlingStrategy] = None,
    ) -> Any:
        """
        Handle an error asynchronously.

        Args:
            exception: The exception to handle
            context: Error context information
            strategy: Specific handling strategy

        Returns:
            Result of error handling
        """
        start_time = time.time()

        # Update context
        if context and isinstance(exception, FastAPIEasyException):
            exception.context = context

        # Track metrics
        if self.track_metrics:
            self._update_metrics(exception)

        # Log the error
        self._log_error(exception)

        # Try custom handler first (async version)
        for exc_type, handler in self.error_handlers.items():
            if isinstance(exception, exc_type):
                try:
                    if asyncio.iscoroutinefunction(handler):
                        return await handler(exception)
                    else:
                        return handler(exception)
                except Exception as handler_error:
                    logger.error(f"Custom error handler failed: {handler_error}")

        # Apply handling strategy
        if strategy == ErrorHandlingStrategy.IGNORE:
            return None
        elif strategy == ErrorHandlingStrategy.ESCALATE:
            self._escalate_error(exception)
            raise exception

        # Try retry (async version)
        if strategy in [None, ErrorHandlingStrategy.RETRY]:
            retry_result = await self._try_retry_async(exception)
            if retry_result is not None:
                return retry_result

        # Try fallback
        if strategy in [None, ErrorHandlingStrategy.FALLBACK]:
            fallback_result = await self._try_fallback_async(exception)
            if fallback_result is not None:
                return fallback_result

        # Default behavior: re-raise
        if isinstance(exception, FastAPIEasyException):
            raise exception
        else:
            raise FastAPIEasyException(
                message=str(exception),
                cause=exception,
            ) from exception

    def _try_retry(self, exception: Exception) -> Any:
        """Try retry logic for the exception."""
        for exc_type, config in self.retry_configs.items():
            if isinstance(exception, exc_type):
                return self._execute_with_retry(exception, config)
        return None

    async def _try_retry_async(self, exception: Exception) -> Any:
        """Try retry logic asynchronously."""
        for exc_type, config in self.retry_configs.items():
            if isinstance(exception, exc_type):
                return await self._execute_with_retry_async(exception, config)
        return None

    def _execute_with_retry(self, exception: Exception, config: RetryConfig) -> Any:
        """Execute retry logic."""
        for attempt in range(config.max_attempts):
            if attempt == 0:
                continue  # Skip first attempt (already failed)

            delay = min(
                config.base_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay,
            )

            if config.jitter:
                import random

                delay *= 0.5 + random.random() * 0.5

            logger.warning(
                f"Retrying operation after {delay:.2f}s (attempt {attempt + 1}/{config.max_attempts})",
                extra={"exception": str(exception), "attempt": attempt + 1},
            )

            time.sleep(delay)

            # Note: In a real implementation, you'd retry the actual operation
            # This is a simplified example
            if attempt == config.max_attempts - 1:
                raise exception

        return None

    async def _execute_with_retry_async(self, exception: Exception, config: RetryConfig) -> Any:
        """Execute retry logic asynchronously."""
        for attempt in range(config.max_attempts):
            if attempt == 0:
                continue

            delay = min(
                config.base_delay * (config.exponential_base ** (attempt - 1)),
                config.max_delay,
            )

            if config.jitter:
                import random

                delay *= 0.5 + random.random() * 0.5

            logger.warning(
                f"Retrying operation after {delay:.2f}s (attempt {attempt + 1}/{config.max_attempts})",
                extra={"exception": str(exception), "attempt": attempt + 1},
            )

            await asyncio.sleep(delay)

            # Note: In a real implementation, you'd retry the actual operation
            if attempt == config.max_attempts - 1:
                raise exception

        return None

    def _try_fallback(self, exception: Exception) -> Any:
        """Try fallback logic for the exception."""
        for exc_type, config in self.fallback_configs.items():
            if isinstance(exception, exc_type):
                try:
                    logger.info(
                        f"Executing fallback for {exc_type.__name__}",
                        extra={"exception": str(exception)},
                    )
                    return config.fallback_func(*config.fallback_args, **config.fallback_kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback execution failed: {fallback_error}")
                    raise exception
        return None

    async def _try_fallback_async(self, exception: Exception) -> Any:
        """Try fallback logic asynchronously."""
        for exc_type, config in self.fallback_configs.items():
            if isinstance(exception, exc_type):
                try:
                    logger.info(
                        f"Executing fallback for {exc_type.__name__}",
                        extra={"exception": str(exception)},
                    )
                    if asyncio.iscoroutinefunction(config.fallback_func):
                        return await config.fallback_func(
                            *config.fallback_args, **config.fallback_kwargs
                        )
                    else:
                        return config.fallback_func(*config.fallback_args, **config.fallback_kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback execution failed: {fallback_error}")
                    raise exception
        return None

    def _update_metrics(self, exception: Exception):
        """Update error metrics."""
        self.metrics.total_errors += 1
        self.metrics.last_error_time = datetime.utcnow()

        exc_type = type(exception).__name__
        self.metrics.errors_by_type[exc_type] = self.metrics.errors_by_type.get(exc_type, 0) + 1

        if isinstance(exception, FastAPIEasyException):
            self.metrics.errors_by_severity[exception.severity.value] = (
                self.metrics.errors_by_severity.get(exception.severity.value, 0) + 1
            )
            self.metrics.errors_by_category[exception.category.value] = (
                self.metrics.errors_by_category.get(exception.category.value, 0) + 1
            )

    def _log_error(self, exception: Exception):
        """Log the error with appropriate level."""
        if isinstance(exception, FastAPIEasyException):
            if exception.severity == ErrorSeverity.CRITICAL:
                logger.critical(f"Critical error: {exception}", exc_info=exception)
            elif exception.severity == ErrorSeverity.HIGH:
                logger.error(f"High severity error: {exception}", exc_info=exception)
            elif exception.severity == ErrorSeverity.MEDIUM:
                logger.warning(f"Medium severity error: {exception}")
            else:
                logger.info(f"Low severity error: {exception}")
        else:
            logger.error(f"Unhandled exception: {exception}", exc_info=exception)

    def _escalate_error(self, exception: Exception):
        """Escalate error to higher level monitoring/alerting."""
        # In a real implementation, this might:
        # - Send alerts to monitoring systems
        # - Notify administrators
        # - Create incident tickets
        logger.critical(
            f"Error escalated: {exception}",
            extra={
                "escalated": True,
                "timestamp": datetime.utcnow().isoformat(),
            },
            exc_info=exception,
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current error handling metrics."""
        return {
            "total_errors": self.metrics.total_errors,
            "errors_by_type": dict(self.metrics.errors_by_type),
            "errors_by_severity": dict(self.metrics.errors_by_severity),
            "errors_by_category": dict(self.metrics.errors_by_category),
            "last_error_time": (
                self.metrics.last_error_time.isoformat() if self.metrics.last_error_time else None
            ),
            "configured_retry_handlers": len(self.retry_configs),
            "configured_fallback_handlers": len(self.fallback_configs),
            "custom_handlers": len(self.error_handlers),
        }

    def reset_metrics(self):
        """Reset error metrics."""
        self.metrics = ErrorMetrics()
        self._error_times = []


# Decorators for error handling
def handle_errors(
    strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.FAIL_FAST,
    exceptions: Optional[List[Type[Exception]]] = None,
    return_value: Any = None,
    handler: Optional[ErrorHandler] = None,
):
    """
    Decorator for automatic error handling.

    Args:
        strategy: Error handling strategy
        exceptions: Specific exceptions to handle
        return_value: Value to return on error (for IGNORE strategy)
        handler: Custom error handler instance
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            error_handler = handler or ErrorHandler()

            try:
                return func(*args, **kwargs)
            except Exception as e:
                if exceptions and not any(isinstance(e, exc_type) for exc_type in exceptions):
                    raise

                if strategy == ErrorHandlingStrategy.IGNORE:
                    return return_value
                else:
                    return error_handler.handle_error(e, strategy=strategy)

        return wrapper

    return decorator


def handle_errors_async(
    strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.FAIL_FAST,
    exceptions: Optional[List[Type[Exception]]] = None,
    return_value: Any = None,
    handler: Optional[ErrorHandler] = None,
):
    """
    Async decorator for automatic error handling.

    Args:
        strategy: Error handling strategy
        exceptions: Specific exceptions to handle
        return_value: Value to return on error (for IGNORE strategy)
        handler: Custom error handler instance
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            error_handler = handler or ErrorHandler()

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if exceptions and not any(isinstance(e, exc_type) for exc_type in exceptions):
                    raise

                if strategy == ErrorHandlingStrategy.IGNORE:
                    return return_value
                else:
                    return await error_handler.handle_error_async(e, strategy=strategy)

        return wrapper

    return decorator


@asynccontextmanager
async def error_context(
    handler: Optional[ErrorHandler] = None,
    strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.FAIL_FAST,
):
    """
    Async context manager for error handling.

    Args:
        handler: Error handler instance
        strategy: Error handling strategy
    """
    error_handler = handler or ErrorHandler()

    try:
        yield error_handler
    except Exception as e:
        await error_handler.handle_error_async(e, strategy=strategy)


# Global error handler instance
default_error_handler = ErrorHandler()

# Configure default retry and fallback strategies
default_error_handler.configure_retry(
    DatabaseConnectionException,
    RetryConfig(max_attempts=3, base_delay=1.0),
)

default_error_handler.configure_fallback(
    ValidationException,
    FallbackConfig(fallback_func=lambda: {"error": "Validation failed"}),
)
