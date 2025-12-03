"""Audit logging for security events in FastAPI-Easy"""

import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class AuditEventType(str, Enum):
    """Audit event types"""

    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGIN_LOCKED = "login_locked"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_EXPIRED = "token_expired"
    PERMISSION_DENIED = "permission_denied"
    PERMISSION_GRANTED = "permission_granted"
    UNAUTHORIZED = "unauthorized"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PASSWORD_CHANGED = "password_changed"
    ROLE_CHANGED = "role_changed"
    PERMISSION_CHANGED = "permission_changed"


class AuditLog:
    """Audit log entry"""

    def __init__(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Initialize audit log entry

        Args:
            event_type: Type of event
            user_id: User ID
            username: Username
            resource: Resource being accessed
            action: Action performed
            status: Status of action (success/failure)
            details: Additional details
            ip_address: IP address of requester
            user_agent: User agent string
        """
        self.event_type = event_type
        self.user_id = user_id
        self.username = username
        self.resource = resource
        self.action = action
        self.status = status
        self.details = details or {}
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary

        Returns:
            Dictionary representation
        """
        return {
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "username": self.username,
            "resource": self.resource,
            "action": self.action,
            "status": self.status,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "timestamp": self.timestamp.isoformat(),
        }


class AuditLogger:
    """Audit logger for security events"""

    def __init__(self, max_logs: int = 10000):
        """Initialize audit logger

        Args:
            max_logs: Maximum number of logs to keep in memory
        """
        self.max_logs = max_logs
        self._lock = threading.RLock()
        # Use deque for automatic old log removal
        self.logs: deque = deque(maxlen=max_logs)
        # Indexes for fast queries
        self.user_index: Dict[str, List[int]] = defaultdict(list)
        self.username_index: Dict[str, List[int]] = defaultdict(list)
        # Global counter to track log positions (fixes index sync issue)
        self._log_counter = 0

    def log(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log an audit event

        Args:
            event_type: Type of event
            user_id: User ID
            username: Username
            resource: Resource being accessed
            action: Action performed
            status: Status of action
            details: Additional details
            ip_address: IP address
            user_agent: User agent

        Returns:
            Audit log entry
        """
        with self._lock:
            log_entry = AuditLog(
                event_type=event_type,
                user_id=user_id,
                username=username,
                resource=resource,
                action=action,
                status=status,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # Use global counter for index (fixes deque rotation issue)
            idx = self._log_counter
            self._log_counter += 1
            self.logs.append(log_entry)

            # Update indexes for fast queries
            if log_entry.user_id:
                self.user_index[log_entry.user_id].append(idx)
            if log_entry.username:
                self.username_index[log_entry.username].append(idx)

            return log_entry

    def get_logs(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit logs with optional filtering

        Args:
            user_id: Filter by user ID
            username: Filter by username
            event_type: Filter by event type
            limit: Maximum number of logs to return

        Returns:
            List of audit log entries
        """
        with self._lock:
            # Use indexes for fast filtering
            if user_id:
                indices = self.user_index.get(user_id, [])
                filtered_logs = [self.logs[i] for i in indices if i < len(self.logs)]
            elif username:
                indices = self.username_index.get(username, [])
                filtered_logs = [self.logs[i] for i in indices if i < len(self.logs)]
            else:
                filtered_logs = list(self.logs)

            # Apply event_type filter if needed
            if event_type:
                filtered_logs = [log for log in filtered_logs if log.event_type == event_type]

            # Return most recent logs
            return [log.to_dict() for log in filtered_logs[-limit:]]

    def get_user_activity(
        self, user_id: Optional[str] = None, username: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user activity logs

        Args:
            user_id: User ID
            username: Username
            limit: Maximum number of logs

        Returns:
            List of user activity logs
        """
        return self.get_logs(user_id=user_id, username=username, limit=limit)

    def get_failed_logins(self, username: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get failed login attempts for a user

        Args:
            username: Username
            limit: Maximum number of logs

        Returns:
            List of failed login logs
        """
        with self._lock:
            failed_logins = [
                log
                for log in self.logs
                if log.username == username and log.event_type == AuditEventType.LOGIN_FAILURE
            ]

            return [log.to_dict() for log in failed_logins[-limit:]]

    def clear_logs(self) -> None:
        """Clear all logs"""
        with self._lock:
            self.logs.clear()

    def export_logs(self) -> List[Dict[str, Any]]:
        """Export all logs

        Returns:
            List of all audit log entries
        """
        with self._lock:
            return [log.to_dict() for log in self.logs]
