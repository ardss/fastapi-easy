"""
全局异常处理中间件

提供统一的异常捕获、处理和响应格式化。
支持错误日志记录、监控和错误上下文管理。
"""

import time
import uuid
import traceback
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

import logging

from ..core.exceptions import (
    BaseException,
    exception_registry,
    ErrorContext,
    ErrorSeverity
)

logger = logging.getLogger(__name__)


class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """
    全局异常处理中间件

    功能：
    1. 统一异常捕获和处理
    2. 请求上下文管理
    3. 错误日志记录
    4. 响应格式标准化
    5. 性能监控
    """

    def __init__(
        self,
        app: ASGIApp,
        include_traceback: bool = False,
        log_errors: bool = True,
        error_context_builder: Optional[Callable[[Request], ErrorContext]] = None
    ):
        """
        初始化异常处理中间件

        Args:
            app: ASGI应用
            include_traceback: 是否在响应中包含堆栈信息（仅开发环境）
            log_errors: 是否记录错误日志
            error_context_builder: 自定义错误上下文构建函数
        """
        super().__init__(app)
        self.include_traceback = include_traceback
        self.log_errors = log_errors
        self.error_context_builder = error_context_builder

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并捕获异常"""
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 记录请求开始时间
        start_time = time.time()

        try:
            # 执行请求
            response = await call_next(request)

            # 记录请求处理时间
            process_time = time.time() - start_time
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(process_time, 4))

            return response

        except Exception as exc:
            # 计算处理时间
            process_time = time.time() - start_time

            # 构建错误上下文
            context = self._build_error_context(request, exc, request_id, process_time)

            # 处理异常
            error_response = await self._handle_exception(exc, context)

            # 添加响应头
            error_response.headers["X-Request-ID"] = request_id
            error_response.headers["X-Process-Time"] = str(round(process_time, 4))

            return error_response

    def _build_error_context(
        self,
        request: Request,
        exception: Exception,
        request_id: str,
        process_time: float
    ) -> ErrorContext:
        """构建错误上下文"""
        # 基础上下文
        context = ErrorContext(
            request_id=request_id,
            metadata={
                "method": request.method,
                "url": str(request.url),
                "user_agent": request.headers.get("user-agent"),
                "process_time": process_time,
                "timestamp": time.time()
            }
        )

        # 尝试获取用户信息（如果已认证）
        if hasattr(request.state, 'user') and request.state.user:
            context.user_id = getattr(request.state.user, 'id', None)

        # 资源和动作信息
        context.resource = f"{request.method} {request.url.path}"
        context.action = request.method.lower()

        # 自定义上下文构建器
        if self.error_context_builder:
            try:
                custom_context = self.error_context_builder(request)
                if isinstance(custom_context, ErrorContext):
                    # 合并上下文信息
                    if custom_context.user_id:
                        context.user_id = custom_context.user_id
                    if custom_context.resource:
                        context.resource = custom_context.resource
                    if custom_context.action:
                        context.action = custom_context.action
                    context.metadata.update(custom_context.metadata)
            except Exception as ctx_exc:
                logger.warning(f"Error building custom context: {ctx_exc}")

        return context

    async def _handle_exception(self, exception: Exception, context: ErrorContext) -> JSONResponse:
        """处理异常并生成响应"""
        # 为基础异常添加上下文
        if isinstance(exception, BaseException):
            exception.context = context

        # 记录错误日志
        if self.log_errors:
            await self._log_error(exception, context)

        # 处理FastAPI HTTPException
        if isinstance(exception, HTTPException):
            return await self._handle_http_exception(exception, context)

        # 使用异常注册表处理异常
        try:
            error_data = exception_registry.handle_exception(exception)
        except Exception as handler_exc:
            # 异常处理器自身出错，使用兜底处理
            logger.error(f"Error in exception handler: {handler_exc}", exc_info=True)
            error_data = {
                "error": {
                    "code": "HANDLER_ERROR",
                    "message": "An error occurred while handling another error",
                    "category": "internal",
                    "severity": "critical"
                }
            }

        # 添加调试信息
        if self.include_traceback and isinstance(exception, BaseException):
            if exception.cause:
                error_data["error"]["traceback"] = traceback.format_exception(
                    type(exception.cause),
                    exception.cause,
                    exception.cause.__traceback__
                )
            else:
                error_data["error"]["traceback"] = traceback.format_exception(
                    type(exception),
                    exception,
                    exception.__traceback__
                )

        # 确定状态码
        status_code = 500
        if isinstance(exception, BaseException):
            status_code = exception.status_code
        elif isinstance(exception, HTTPException):
            status_code = exception.status_code

        return JSONResponse(
            status_code=status_code,
            content=error_data
        )

    async def _handle_http_exception(
        self,
        exception: HTTPException,
        context: ErrorContext
    ) -> JSONResponse:
        """处理FastAPI HTTPException"""
        error_data = {
            "error": {
                "code": f"HTTP_{exception.status_code}",
                "message": exception.detail,
                "category": "internal" if exception.status_code >= 500 else "client",
                "severity": "high" if exception.status_code >= 500 else "medium",
                "details": exception.headers if exception.headers else {},
                "context": {
                    "request_id": context.request_id,
                    "resource": context.resource,
                    "action": context.action,
                    "metadata": context.metadata
                }
            }
        }

        return JSONResponse(
            status_code=exception.status_code,
            content=error_data,
            headers=exception.headers
        )

    async def _log_error(self, exception: Exception, context: ErrorContext):
        """记录错误日志"""
        if isinstance(exception, BaseException):
            # 根据严重程度选择日志级别
            log_level = {
                ErrorSeverity.LOW: logging.INFO,
                ErrorSeverity.MEDIUM: logging.WARNING,
                ErrorSeverity.HIGH: logging.ERROR,
                ErrorSeverity.CRITICAL: logging.CRITICAL
            }.get(exception.severity, logging.ERROR)

            logger.log(
                log_level,
                f"Application error [{exception.code}]: {exception.message}",
                extra={
                    "error_code": exception.code,
                    "error_category": exception.category.value,
                    "error_severity": exception.severity.value,
                    "request_id": context.request_id,
                    "user_id": context.user_id,
                    "resource": context.resource,
                    "action": context.action,
                    "details": {**exception.details, **context.metadata}
                },
                exc_info=exception if log_level >= logging.ERROR else None
            )
        else:
            # 未知异常
            logger.error(
                f"Unhandled exception: {type(exception).__name__} - {str(exception)}",
                extra={
                    "request_id": context.request_id,
                    "user_id": context.user_id,
                    "resource": context.resource,
                    "action": context.action,
                    "details": context.metadata
                },
                exc_info=True
            )


class CircuitBreakerMiddleware(BaseHTTPMiddleware):
    """
    熔断器中间件

    防止级联故障，在错误率过高时暂时停止服务。
    """

    def __init__(
        self,
        app: ASGIApp,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        """
        初始化熔断器

        Args:
            app: ASGI应用
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时时间（秒）
            expected_exception: 预期的异常类型
        """
        super().__init__(app)
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": {
                            "code": "SERVICE_UNAVAILABLE",
                            "message": "Service temporarily unavailable",
                            "category": "external",
                            "severity": "high"
                        }
                    }
                )

        try:
            response = await call_next(request)

            if self.state == "HALF_OPEN":
                self._reset()

            return response

        except self.expected_exception as exc:
            self._record_failure()
            raise exc

    def _should_attempt_reset(self) -> bool:
        """是否应该尝试重置"""
        if self.last_failure_time is None:
            return False

        return time.time() - self.last_failure_time >= self.recovery_timeout

    def _record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def _reset(self):
        """重置熔断器"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"