"""Logging system for FastAPI-Easy"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class LogLevel(str, Enum):
    """Log level enumeration"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormatter(logging.Formatter):
    """Custom log formatter with structured logging support"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record

        Args:
            record: Log record

        Returns:
            Formatted log message
        """
        from datetime import timezone

        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger for FastAPI-Easy"""

    def __init__(
        self,
        name: str = "fastapi_easy",
        level: str = LogLevel.INFO,
        use_json: bool = True,
    ):
        """Initialize structured logger

        Args:
            name: Logger name
            level: Log level
            use_json: Use JSON formatting
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level))
        self.use_json = use_json

        # Create console handler
        handler = logging.StreamHandler()
        handler.setLevel(getattr(logging, level))

        # Create formatter
        if use_json:
            formatter = LogFormatter()
        else:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def debug(
        self,
        message: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log debug message

        Args:
            message: Log message
            extra_fields: Extra fields to include
        """
        self._log(logging.DEBUG, message, extra_fields)

    def info(
        self,
        message: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log info message

        Args:
            message: Log message
            extra_fields: Extra fields to include
        """
        self._log(logging.INFO, message, extra_fields)

    def warning(
        self,
        message: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log warning message

        Args:
            message: Log message
            extra_fields: Extra fields to include
        """
        self._log(logging.WARNING, message, extra_fields)

    def error(
        self,
        message: str,
        extra_fields: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        """Log error message

        Args:
            message: Log message
            extra_fields: Extra fields to include
            exception: Exception to log
        """
        if exception:
            self.logger.error(
                message, exc_info=exception, extra={"extra_fields": extra_fields or {}}
            )
        else:
            self._log(logging.ERROR, message, extra_fields)

    def critical(
        self,
        message: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log critical message

        Args:
            message: Log message
            extra_fields: Extra fields to include
        """
        self._log(logging.CRITICAL, message, extra_fields)

    def _log(
        self,
        level: int,
        message: str,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Internal log method

        Args:
            level: Log level
            message: Log message
            extra_fields: Extra fields to include
        """
        extra = {}
        if extra_fields:
            extra["extra_fields"] = extra_fields

        self.logger.log(level, message, extra=extra)


class OperationLogger:
    """Logger for tracking operations"""

    def __init__(self, logger: StructuredLogger):
        """Initialize operation logger

        Args:
            logger: StructuredLogger instance
        """
        self.logger = logger

    def log_create(
        self,
        entity_type: str,
        entity_id: Any,
        user_id: Optional[int] = None,
    ) -> None:
        """Log create operation

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            user_id: ID of user
        """
        self.logger.info(
            f"Created {entity_type}",
            extra_fields={
                "operation": "CREATE",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
            },
        )

    def log_read(
        self,
        entity_type: str,
        entity_id: Any,
        user_id: Optional[int] = None,
    ) -> None:
        """Log read operation

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            user_id: ID of user
        """
        self.logger.debug(
            f"Read {entity_type}",
            extra_fields={
                "operation": "READ",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
            },
        )

    def log_update(
        self,
        entity_type: str,
        entity_id: Any,
        changes: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ) -> None:
        """Log update operation

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            changes: Changes made
            user_id: ID of user
        """
        self.logger.info(
            f"Updated {entity_type}",
            extra_fields={
                "operation": "UPDATE",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "changes": changes,
                "user_id": user_id,
            },
        )

    def log_delete(
        self,
        entity_type: str,
        entity_id: Any,
        user_id: Optional[int] = None,
    ) -> None:
        """Log delete operation

        Args:
            entity_type: Type of entity
            entity_id: ID of entity
            user_id: ID of user
        """
        self.logger.warning(
            f"Deleted {entity_type}",
            extra_fields={
                "operation": "DELETE",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "user_id": user_id,
            },
        )

    def log_error(
        self,
        operation: str,
        entity_type: str,
        error: Exception,
        user_id: Optional[int] = None,
    ) -> None:
        """Log error operation

        Args:
            operation: Operation type
            entity_type: Type of entity
            error: Error that occurred
            user_id: ID of user
        """
        self.logger.error(
            f"Error during {operation} on {entity_type}",
            extra_fields={
                "operation": operation,
                "entity_type": entity_type,
                "error": str(error),
                "user_id": user_id,
            },
            exception=error,
        )


class LoggerConfig:
    """Configuration for logging"""

    def __init__(
        self,
        enabled: bool = True,
        level: str = LogLevel.INFO,
        use_json: bool = True,
        log_operations: bool = True,
        log_errors: bool = True,
    ):
        """Initialize logger configuration

        Args:
            enabled: Enable logging
            level: Log level
            use_json: Use JSON formatting
            log_operations: Log operations
            log_errors: Log errors
        """
        self.enabled = enabled
        self.level = level
        self.use_json = use_json
        self.log_operations = log_operations
        self.log_errors = log_errors


# Global logger instance
_logger: Optional[StructuredLogger] = None


def get_logger(
    name: str = "fastapi_easy",
    level: str = LogLevel.INFO,
    use_json: bool = True,
) -> StructuredLogger:
    """Get or create logger instance

    Args:
        name: Logger name
        level: Log level
        use_json: Use JSON formatting

    Returns:
        StructuredLogger instance
    """
    global _logger

    if _logger is None:
        _logger = StructuredLogger(name=name, level=level, use_json=use_json)

    return _logger


def get_operation_logger() -> OperationLogger:
    """Get operation logger

    Returns:
        OperationLogger instance
    """
    return OperationLogger(get_logger())
