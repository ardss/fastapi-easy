"""
统一异常处理系统

提供全局统一的异常定义、处理和中间件支持。
遵循SOLID原则，实现单一职责和开闭原则。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """错误严重程度"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """错误分类"""

    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INTERNAL = "internal"
    EXTERNAL = "external"
    BUSINESS = "business"


@dataclass
class ErrorContext:
    """错误上下文信息"""

    user_id: Optional[str] = None
    request_id: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseException(Exception):
    """
    基础异常类

    所有应用异常的基类，提供统一的错误信息格式和处理机制。
    """

    def __init__(
        self,
        message: str,
        code: str = None,
        status_code: int = 500,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Dict[str, Any] = None,
        context: ErrorContext = None,
        cause: Exception = None,
    ):
        self.message = message
        self.code = code or self.__class__.__name__.upper()
        self.status_code = status_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.context = context or ErrorContext()
        self.cause = cause

        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "category": self.category.value,
                "severity": self.severity.value,
                "details": self.details,
                "context": {
                    "user_id": self.context.user_id,
                    "request_id": self.context.request_id,
                    "resource": self.context.resource,
                    "action": self.context.action,
                    "metadata": self.context.metadata,
                },
            }
        }

    def with_context(self, **kwargs) -> BaseException:
        """添加上下文信息"""
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
            else:
                self.context.metadata[key] = value
        return self


class ValidationError(BaseException):
    """验证错误"""

    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        details = kwargs.pop("details", {})
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details=details,
            **kwargs,
        )


class AuthenticationError(BaseException):
    """认证错误"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message=message,
            code="AUTHENTICATION_ERROR",
            status_code=401,
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class AuthorizationError(BaseException):
    """授权错误"""

    def __init__(self, message: str = "Permission denied", **kwargs):
        super().__init__(
            message=message,
            code="AUTHORIZATION_ERROR",
            status_code=403,
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class NotFoundError(BaseException):
    """资源未找到错误"""

    def __init__(self, resource: str, identifier: Any = None, **kwargs):
        message = f"{resource} not found"
        if identifier:
            message = f"{resource} with identifier '{identifier}' not found"

        details = kwargs.pop("details", {})
        details.update(
            {"resource_type": resource, "identifier": str(identifier) if identifier else None}
        )

        super().__init__(
            message=message,
            code="NOT_FOUND_ERROR",
            status_code=404,
            category=ErrorCategory.NOT_FOUND,
            severity=ErrorSeverity.LOW,
            details=details,
            **kwargs,
        )


class ConflictError(BaseException):
    """冲突错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__(
            message=message,
            code="CONFLICT_ERROR",
            status_code=409,
            category=ErrorCategory.CONFLICT,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )


class BusinessRuleError(BaseException):
    """业务规则错误"""

    def __init__(self, message: str, rule: str = None, **kwargs):
        details = kwargs.pop("details", {})
        if rule:
            details["rule"] = rule

        super().__init__(
            message=message,
            code="BUSINESS_RULE_ERROR",
            status_code=422,
            category=ErrorCategory.BUSINESS,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            **kwargs,
        )


class ExternalServiceError(BaseException):
    """外部服务错误"""

    def __init__(self, service: str, message: str, **kwargs):
        details = kwargs.pop("details", {})
        details["service"] = service

        super().__init__(
            message=f"External service '{service}' error: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
            category=ErrorCategory.EXTERNAL,
            severity=ErrorSeverity.HIGH,
            details=details,
            **kwargs,
        )


class InternalError(BaseException):
    """内部系统错误"""

    def __init__(self, message: str = "Internal server error", **kwargs):
        super().__init__(
            message=message,
            code="INTERNAL_ERROR",
            status_code=500,
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.CRITICAL,
            **kwargs,
        )


# 异常处理函数类型
ExceptionHandler = Callable[[Exception], Dict[str, Any]]


class ExceptionHandlerRegistry:
    """异常处理器注册表"""

    def __init__(self):
        self._handlers: Dict[Type[Exception], ExceptionHandler] = {}

    def register(self, exception_type: Type[Exception], handler: ExceptionHandler):
        """注册异常处理器"""
        self._handlers[exception_type] = handler

    def get_handler(self, exception: Exception) -> Optional[ExceptionHandler]:
        """获取异常处理器"""
        exc_type = type(exception)

        # 精确匹配
        if exc_type in self._handlers:
            return self._handlers[exc_type]

        # 继承关系匹配
        for registered_type, handler in self._handlers.items():
            if issubclass(exc_type, registered_type):
                return handler

        return None

    def handle_exception(self, exception: Exception) -> Dict[str, Any]:
        """处理异常"""
        handler = self.get_handler(exception)

        if handler:
            return handler(exception)

        # 默认处理
        if isinstance(exception, BaseException):
            return exception.to_dict()

        # 未知异常
        return InternalError(
            message="An unexpected error occurred",
            details={"original_error": str(exception), "type": type(exception).__name__},
        ).to_dict()


# 全局异常处理器注册表
exception_registry = ExceptionHandlerRegistry()


# 注册默认处理器
def register_default_handlers():
    """注册默认异常处理器"""

    def handle_base_exception(exc: BaseException) -> Dict[str, Any]:
        """处理基础异常"""
        logger.error(
            f"Application error: {exc.code} - {exc.message}",
            extra={
                "error_code": exc.code,
                "error_category": exc.category.value,
                "error_severity": exc.severity.value,
                "details": exc.details,
                "context": exc.context.__dict__,
            },
            exc_info=exc,
        )
        return exc.to_dict()

    def handle_general_exception(exc: Exception) -> Dict[str, Any]:
        """处理通用异常"""
        logger.error(f"Unhandled exception: {type(exc).__name__} - {exc!s}", exc_info=True)
        return InternalError(message="An unexpected error occurred", cause=exc).to_dict()

    exception_registry.register(BaseException, handle_base_exception)
    exception_registry.register(Exception, handle_general_exception)


# 初始化默认处理器
register_default_handlers()
