"""Base middleware system for FastAPI-Easy"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


class BaseMiddleware(ABC):
    """Base middleware class"""

    def __init__(self, name: str = ""):
        """Initialize middleware

        Args:
            name: Middleware name
        """
        self.name = name or self.__class__.__name__
        self.enabled = True

    @abstractmethod
    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request

        Args:
            context: Request context

        Returns:
            Modified context
        """
        pass

    @abstractmethod
    async def process_response(self, context: Dict[str, Any], response: Any) -> Any:
        """Process response

        Args:
            context: Request context
            response: Response data

        Returns:
            Modified response
        """
        pass

    async def process_error(self, context: Dict[str, Any], error: Exception) -> Exception:
        """Process error

        Args:
            context: Request context
            error: Exception

        Returns:
            Modified exception
        """
        return error

    def enable(self) -> None:
        """Enable middleware"""
        self.enabled = True

    def disable(self) -> None:
        """Disable middleware"""
        self.enabled = False


class ErrorHandlingMiddleware(BaseMiddleware):
    """Middleware for error handling"""

    def __init__(self, name: str = "ErrorHandling"):
        """Initialize error handling middleware

        Args:
            name: Middleware name
        """
        super().__init__(name)
        self.error_handlers: Dict[type, Callable] = {}

    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request

        Args:
            context: Request context

        Returns:
            Modified context
        """
        context["errors"] = []
        return context

    async def process_response(self, context: Dict[str, Any], response: Any) -> Any:
        """Process response

        Args:
            context: Request context
            response: Response data

        Returns:
            Modified response
        """
        return response

    async def process_error(self, context: Dict[str, Any], error: Exception) -> Exception:
        """Process error with custom handlers

        Args:
            context: Request context
            error: Exception

        Returns:
            Modified exception
        """
        error_type = type(error)

        if error_type in self.error_handlers:
            handler = self.error_handlers[error_type]
            if asyncio.iscoroutinefunction(handler):
                return await handler(error)
            else:
                return handler(error)

        return error

    def register_handler(self, error_type: type, handler: Callable) -> None:
        """Register error handler

        Args:
            error_type: Error type
            handler: Handler function
        """
        self.error_handlers[error_type] = handler


class LoggingMiddleware(BaseMiddleware):
    """Middleware for logging"""

    def __init__(self, name: str = "Logging", logger: Optional[Any] = None):
        """Initialize logging middleware

        Args:
            name: Middleware name
            logger: Logger instance
        """
        super().__init__(name)
        self.logger = logger

    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request

        Args:
            context: Request context

        Returns:
            Modified context
        """
        if self.logger:
            self.logger.info(
                f"Request: {context.get('method', 'UNKNOWN')} {context.get('path', '/')}",
                extra_fields={
                    "method": context.get("method"),
                    "path": context.get("path"),
                    "params": context.get("params"),
                },
            )

        return context

    async def process_response(self, context: Dict[str, Any], response: Any) -> Any:
        """Process response

        Args:
            context: Request context
            response: Response data

        Returns:
            Modified response
        """
        if self.logger:
            self.logger.info(
                f"Response: {context.get('method', 'UNKNOWN')} {context.get('path', '/')}",
                extra_fields={
                    "method": context.get("method"),
                    "path": context.get("path"),
                    "status": context.get("status", 200),
                },
            )

        return response

    async def process_error(self, context: Dict[str, Any], error: Exception) -> Exception:
        """Process error

        Args:
            context: Request context
            error: Exception

        Returns:
            Modified exception
        """
        if self.logger:
            self.logger.error(
                f"Error: {context.get('method', 'UNKNOWN')} {context.get('path', '/')}",
                extra_fields={
                    "method": context.get("method"),
                    "path": context.get("path"),
                    "error": str(error),
                },
                exception=error,
            )

        return error


class MonitoringMiddleware(BaseMiddleware):
    """Middleware for monitoring"""

    def __init__(self, name: str = "Monitoring"):
        """Initialize monitoring middleware

        Args:
            name: Middleware name
        """
        super().__init__(name)
        self.request_count = 0
        self.error_count = 0
        self.total_time = 0.0

    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request

        Args:
            context: Request context

        Returns:
            Modified context
        """
        import time

        self.request_count += 1
        context["start_time"] = time.time()

        return context

    async def process_response(self, context: Dict[str, Any], response: Any) -> Any:
        """Process response

        Args:
            context: Request context
            response: Response data

        Returns:
            Modified response
        """
        import time

        start_time = context.get("start_time", time.time())
        elapsed = time.time() - start_time
        self.total_time += elapsed

        return response

    async def process_error(self, context: Dict[str, Any], error: Exception) -> Exception:
        """Process error

        Args:
            context: Request context
            error: Exception

        Returns:
            Modified exception
        """
        self.error_count += 1
        return error

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics

        Returns:
            Statistics dictionary
        """
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "total_time": self.total_time,
            "avg_time": self.total_time / self.request_count if self.request_count > 0 else 0,
        }


class MiddlewareChain:
    """Chain of middlewares"""

    def __init__(self):
        """Initialize middleware chain"""
        self.middlewares: list[BaseMiddleware] = []

    def add(self, middleware: BaseMiddleware) -> None:
        """Add middleware to chain

        Args:
            middleware: Middleware instance
        """
        self.middlewares.append(middleware)

    def remove(self, middleware: BaseMiddleware) -> None:
        """Remove middleware from chain

        Args:
            middleware: Middleware instance
        """
        if middleware in self.middlewares:
            self.middlewares.remove(middleware)

    async def process_request(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request through all middlewares

        Args:
            context: Request context

        Returns:
            Modified context
        """
        for middleware in self.middlewares:
            if middleware.enabled:
                context = await middleware.process_request(context)

        return context

    async def process_response(self, context: Dict[str, Any], response: Any) -> Any:
        """Process response through all middlewares

        Args:
            context: Request context
            response: Response data

        Returns:
            Modified response
        """
        for middleware in reversed(self.middlewares):
            if middleware.enabled:
                response = await middleware.process_response(context, response)

        return response

    async def process_error(self, context: Dict[str, Any], error: Exception) -> Exception:
        """Process error through all middlewares

        Args:
            context: Request context
            error: Exception

        Returns:
            Modified exception
        """
        for middleware in reversed(self.middlewares):
            if middleware.enabled:
                error = await middleware.process_error(context, error)

        return error
