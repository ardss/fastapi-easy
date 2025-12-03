"""Audit logging support for FastAPI-Easy"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class AuditAction(str, Enum):
    """Audit action enumeration"""

    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    RESTORE = "RESTORE"


class AuditLog:
    """Audit log entry"""

    def __init__(
        self,
        entity_type: str,
        entity_id: Any,
        action: str,
        user_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Initialize audit log entry

        Args:
            entity_type: Type of entity (e.g., 'User', 'Product')
            entity_id: ID of the entity
            action: Action performed (CREATE, READ, UPDATE, DELETE, RESTORE)
            user_id: ID of the user who performed the action
            changes: Dictionary of changes (old_value -> new_value)
            timestamp: When the action occurred
            ip_address: IP address of the request
            user_agent: User agent of the request
        """
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.action = action
        self.user_id = user_id
        self.changes = changes or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.ip_address = ip_address
        self.user_agent = user_agent

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "user_id": self.user_id,
            "changes": self.changes,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }


class AuditLogger:
    """Audit logger for tracking operations"""

    def __init__(self):
        """Initialize audit logger"""
        self.logs: List[AuditLog] = []

    def log(
        self,
        entity_type: str,
        entity_id: Any,
        action: str,
        user_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log an action

        Args:
            entity_type: Type of entity
            entity_id: ID of the entity
            action: Action performed
            user_id: ID of the user
            changes: Dictionary of changes
            ip_address: IP address
            user_agent: User agent

        Returns:
            AuditLog entry
        """
        log_entry = AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            user_id=user_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.logs.append(log_entry)
        return log_entry

    def get_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
    ) -> List[AuditLog]:
        """Get audit logs with optional filters

        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            user_id: Filter by user ID
            action: Filter by action

        Returns:
            List of matching audit logs
        """
        results = self.logs

        if entity_type:
            results = [log for log in results if log.entity_type == entity_type]

        if entity_id is not None:
            results = [log for log in results if log.entity_id == entity_id]

        if user_id is not None:
            results = [log for log in results if log.user_id == user_id]

        if action:
            results = [log for log in results if log.action == action]

        return results

    def get_entity_history(
        self,
        entity_type: str,
        entity_id: Any,
    ) -> List[AuditLog]:
        """Get complete history for an entity

        Args:
            entity_type: Type of entity
            entity_id: ID of the entity

        Returns:
            List of audit logs for the entity
        """
        return self.get_logs(entity_type=entity_type, entity_id=entity_id)

    def get_user_actions(self, user_id: int) -> List[AuditLog]:
        """Get all actions performed by a user

        Args:
            user_id: ID of the user

        Returns:
            List of audit logs for the user
        """
        return self.get_logs(user_id=user_id)

    def clear(self) -> None:
        """Clear all logs"""
        self.logs.clear()

    def export_logs(self) -> List[Dict[str, Any]]:
        """Export all logs as dictionaries

        Returns:
            List of log dictionaries
        """
        return [log.to_dict() for log in self.logs]


class AuditLogContext:
    """Context for audit logging"""

    def __init__(
        self,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Initialize audit log context

        Args:
            user_id: ID of the user
            ip_address: IP address
            user_agent: User agent
        """
        self.user_id = user_id
        self.ip_address = ip_address
        self.user_agent = user_agent


class AuditLogConfig:
    """Configuration for audit logging"""

    def __init__(
        self,
        enabled: bool = True,
        log_reads: bool = False,
        log_changes_only: bool = True,
        max_logs: int = 10000,
        retention_days: int = 90,
    ):
        """Initialize audit log configuration

        Args:
            enabled: Enable audit logging
            log_reads: Log READ operations
            log_changes_only: Only log if changes occurred
            max_logs: Maximum number of logs to keep
            retention_days: Days to retain logs
        """
        self.enabled = enabled
        self.log_reads = log_reads
        self.log_changes_only = log_changes_only
        self.max_logs = max_logs
        self.retention_days = retention_days


class AuditLogDecorator:
    """Decorator for audit logging"""

    def __init__(self, logger: AuditLogger, config: AuditLogConfig):
        """Initialize decorator

        Args:
            logger: AuditLogger instance
            config: AuditLogConfig instance
        """
        self.logger = logger
        self.config = config

    def track_operation(
        self,
        entity_type: str,
        action: str,
    ):
        """Decorator to track operations

        Args:
            entity_type: Type of entity
            action: Action being performed
        """

        def decorator(func):
            async def wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)

                # Skip READ operations if not configured to log them
                if action == AuditAction.READ and not self.config.log_reads:
                    return result

                # Extract entity ID from result
                entity_id = None
                if hasattr(result, "id"):
                    entity_id = result.id
                elif isinstance(result, dict) and "id" in result:
                    entity_id = result["id"]

                # Log the operation
                if entity_id is not None:
                    self.logger.log(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        action=action,
                    )

                return result

            return wrapper

        return decorator
