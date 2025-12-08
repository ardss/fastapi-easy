"""Enhanced security logging for FastAPI-Easy"""

import json
import logging
import logging.handlers
import os
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import Request, Response


# Security event types
class SecurityEventType(str, Enum):
    """Security event types"""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_ISSUED = "token_issued"
    TOKEN_VERIFIED = "token_verified"
    TOKEN_INVALID = "token_invalid"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REVOKED = "token_revoked"

    # Authorization events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"

    # Input validation events
    INPUT_VALIDATION_FAILED = "input_validation_failed"
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    CSRF_ATTEMPT = "csrf_attempt"
    PATH_TRAVERSAL_ATTEMPT = "path_traversal_attempt"
    COMMAND_INJECTION_ATTEMPT = "command_injection_attempt"

    # Rate limiting events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    IP_BLOCKED = "ip_blocked"

    # Data access events
    SENSITIVE_DATA_ACCESS = "sensitive_data_access"
    DATA_EXPORT = "data_export"
    DATA_BULK_ACCESS = "data_bulk_access"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"

    # System events
    SECURITY_POLICY_VIOLATION = "security_policy_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_MISCONFIGURATION = "security_misconfiguration"

    # Network events
    SUSPICIOUS_REQUEST = "suspicious_request"
    ANOMALOUS_TRAFFIC = "anomalous_traffic"
    UNUSUAL_USER_AGENT = "unusual_user_agent"
    UNEXPECTED_HEADERS = "unexpected_headers"


class SecurityLogger:
    """Enhanced security logger with structured logging"""

    def __init__(
        self,
        log_file: Optional[str] = None,
        log_level: int = logging.INFO,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        enable_json_format: bool = True,
        sensitive_fields: Optional[list] = None,
    ):
        """Initialize security logger

        Args:
            log_file: Path to log file (default: logs/security.log)
            log_level: Logging level
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup log files
            enable_json_format: Enable JSON structured logging
            sensitive_fields: List of sensitive field names to redact
        """
        self.log_file = log_file or "logs/security.log"
        self.log_level = log_level
        self.enable_json_format = enable_json_format
        self.sensitive_fields = sensitive_fields or [
            "password",
            "token",
            "secret",
            "key",
            "authorization",
            "cookie",
            "session",
            "credit_card",
            "ssn",
            "social_security",
        ]

        # Create logs directory if it doesn't exist
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Set up logger
        self.logger = logging.getLogger("fastapi_easy.security")
        self.logger.setLevel(log_level)

        # Clear existing handlers
        self.logger.handlers.clear()

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setLevel(log_level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console

        # Set up formatters
        if enable_json_format:
            formatter = self._get_json_formatter()
        else:
            formatter = self._get_text_formatter()

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(self._get_text_formatter())

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Don't propagate to root logger to avoid duplicate logs
        self.logger.propagate = False

    def _get_json_formatter(self) -> logging.Formatter:
        """Get JSON formatter for structured logging"""

        class JsonFormatter(logging.Formatter):
            def format(self, record):
                # Create log entry
                log_entry = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }

                # Add security event data if available
                if hasattr(record, "security_event"):
                    log_entry.update(record.security_event)

                return json.dumps(log_entry, ensure_ascii=False)

        return JsonFormatter()

    def _get_text_formatter(self) -> logging.Formatter:
        """Get text formatter for human-readable logging"""
        return logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    def _redact_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive data from log entry

        Args:
            data: Dictionary to redact

        Returns:
            Redacted dictionary
        """
        if not isinstance(data, dict):
            return data

        redacted = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                redacted[key] = "[REDACTED]"
            elif isinstance(value, dict):
                redacted[key] = self._redact_sensitive_data(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_sensitive_data(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                redacted[key] = value

        return redacted

    def log_security_event(
        self,
        event_type: SecurityEventType,
        message: str,
        severity: str = "info",
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_path: Optional[str] = None,
        request_method: Optional[str] = None,
        response_status: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Log a security event

        Args:
            event_type: Type of security event
            message: Log message
            severity: Event severity (debug, info, warning, error, critical)
            user_id: User ID if available
            ip_address: Client IP address
            user_agent: User agent string
            request_path: Request path
            request_method: HTTP method
            response_status: HTTP response status
            details: Additional event details
            request_id: Request ID for tracing
            session_id: Session ID
        """
        # Build security event data
        security_event = {
            "event_type": event_type.value,
            "severity": severity.lower(),
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_path": request_path,
            "request_method": request_method,
            "response_status": response_status,
            "request_id": request_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add additional details if provided
        if details:
            security_event["details"] = self._redact_sensitive_data(details)

        # Log with appropriate level
        log_method = getattr(self.logger, severity.lower(), self.logger.info)
        log_method(message, extra={"security_event": security_event})

    def log_authentication_event(
        self,
        event_type: SecurityEventType,
        user_id: str,
        ip_address: str,
        user_agent: Optional[str] = None,
        success: bool = True,
        failure_reason: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log authentication events

        Args:
            event_type: Authentication event type
            user_id: User ID
            ip_address: Client IP address
            user_agent: User agent string
            success: Whether authentication succeeded
            failure_reason: Reason for failure (if unsuccessful)
            additional_info: Additional information
        """
        message = f"Authentication {event_type.value} for user {user_id}"
        severity = "info" if success else "warning"

        if not success and failure_reason:
            message += f" - Reason: {failure_reason}"
            severity = "warning"

        details = {"success": success}
        if failure_reason:
            details["failure_reason"] = failure_reason
        if additional_info:
            details.update(additional_info)

        self.log_security_event(
            event_type=event_type,
            message=message,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
        )

    def log_authorization_event(
        self,
        event_type: SecurityEventType,
        user_id: str,
        resource: str,
        action: str,
        ip_address: str,
        granted: bool,
        reason: Optional[str] = None,
    ) -> None:
        """Log authorization events

        Args:
            event_type: Authorization event type
            user_id: User ID
            resource: Resource being accessed
            action: Action being performed
            ip_address: Client IP address
            granted: Whether permission was granted
            reason: Reason for denial (if denied)
        """
        message = f"Authorization {event_type.value}: {action} on {resource}"
        severity = "info" if granted else "warning"

        if not granted:
            message += f" - DENIED"
            if reason:
                message += f" ({reason})"
            severity = "warning"

        details = {
            "resource": resource,
            "action": action,
            "granted": granted,
        }
        if reason:
            details["reason"] = reason

        self.log_security_event(
            event_type=event_type,
            message=message,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
        )

    def log_security_violation(
        self,
        violation_type: SecurityEventType,
        description: str,
        ip_address: str,
        user_id: Optional[str] = None,
        request_data: Optional[Dict[str, Any]] = None,
        severity: str = "warning",
    ) -> None:
        """Log security violations

        Args:
            violation_type: Type of violation
            description: Description of the violation
            ip_address: Client IP address
            user_id: User ID if available
            request_data: Request data that caused violation
            severity: Violation severity
        """
        message = f"Security violation: {violation_type.value} - {description}"

        details = {"violation_type": violation_type.value}
        if request_data:
            details["request_data"] = self._redact_sensitive_data(request_data)

        self.log_security_event(
            event_type=violation_type,
            message=message,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
        )

    def log_request_response(
        self,
        request: Request,
        response: Response,
        duration_ms: float,
        user_id: Optional[str] = None,
    ) -> None:
        """Log HTTP request and response

        Args:
            request: FastAPI request
            response: FastAPI response
            duration_ms: Request duration in milliseconds
            user_id: User ID if authenticated
        """
        # Skip logging for health checks and static files
        if request.url.path in ["/health", "/metrics", "/favicon.ico"]:
            return

        # Check for suspicious patterns
        suspicious = self._check_suspicious_request(request)

        message = f"HTTP {request.method} {request.url.path} - {response.status_code}"
        severity = "info"

        if response.status_code >= 400:
            severity = "warning"
        if response.status_code >= 500:
            severity = "error"

        # Log suspicious requests with higher severity
        if suspicious["is_suspicious"]:
            severity = "warning"
            message += f" [SUSPICIOUS: {', '.join(suspicious['reasons'])}]"

        details = {
            "duration_ms": duration_ms,
            "query_params": dict(request.query_params),
            "headers_size": len(str(request.headers)),
        }

        # Add suspicious details if found
        if suspicious["is_suspicious"]:
            details["suspicious_indicators"] = suspicious["details"]

        self.log_security_event(
            event_type=(
                SecurityEventType.SUSPICIOUS_REQUEST
                if suspicious["is_suspicious"]
                else SecurityEventType.LOGIN_SUCCESS
            ),
            message=message,
            severity=severity,
            user_id=user_id,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            request_path=request.url.path,
            request_method=request.method,
            response_status=response.status_code,
            details=details,
            request_id=getattr(request.state, "request_id", None),
        )

    def log_data_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str],
        action: str,
        ip_address: str,
        is_sensitive: bool = False,
        record_count: Optional[int] = None,
    ) -> None:
        """Log data access events

        Args:
            user_id: User ID accessing data
            resource_type: Type of resource (e.g., "user", "order")
            resource_id: Specific resource ID
            action: Action performed (read, write, delete)
            ip_address: Client IP address
            is_sensitive: Whether accessed data is sensitive
            record_count: Number of records accessed
        """
        message = f"Data access: {action} on {resource_type}"
        if resource_id:
            message += f" (ID: {resource_id})"
        if record_count:
            message += f" - {record_count} records"

        severity = "info"
        if is_sensitive:
            severity = "warning"
            message += " [SENSITIVE DATA]"
        if record_count and record_count > 100:
            severity = "warning"
            message += " [BULK ACCESS]"

        details = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "is_sensitive": is_sensitive,
        }
        if record_count:
            details["record_count"] = record_count

        event_type = (
            SecurityEventType.SENSITIVE_DATA_ACCESS
            if is_sensitive
            else SecurityEventType.LOGIN_SUCCESS
        )
        if record_count and record_count > 100:
            event_type = SecurityEventType.DATA_BULK_ACCESS

        self.log_security_event(
            event_type=event_type,
            message=message,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
        )

    def _check_suspicious_request(self, request: Request) -> Dict[str, Any]:
        """Check for suspicious request patterns

        Args:
            request: FastAPI request

        Returns:
            Dictionary with suspicious indicators
        """
        suspicious = {
            "is_suspicious": False,
            "reasons": [],
            "details": {},
        }

        # Check for unusual user agents
        user_agent = request.headers.get("user-agent", "").lower()
        suspicious_agents = ["sqlmap", "nikto", "nmap", "curl", "wget", "python-requests"]
        if any(agent in user_agent for agent in suspicious_agents):
            suspicious["is_suspicious"] = True
            suspicious["reasons"].append("unusual_user_agent")
            suspicious["details"]["user_agent"] = user_agent

        # Check for suspicious headers
        suspicious_headers = ["x-forwarded-for", "x-real-ip", "x-originating-ip"]
        for header in suspicious_headers:
            if header in request.headers:
                suspicious["is_suspicious"] = True
                suspicious["reasons"].append("proxy_headers")
                suspicious["details"]["proxy_headers"] = [
                    h for h in suspicious_headers if h in request.headers
                ]
                break

        # Check for suspicious query parameters
        query_params = dict(request.query_params)
        suspicious_patterns = ["../", "..\\", "<script", "javascript:", "select *", "union all"]
        for key, value in query_params.items():
            for pattern in suspicious_patterns:
                if pattern.lower() in value.lower():
                    suspicious["is_suspicious"] = True
                    suspicious["reasons"].append("suspicious_query_params")
                    suspicious["details"]["suspicious_params"] = {key: value}
                    break

        # Check for very long URLs
        if len(str(request.url)) > 2048:
            suspicious["is_suspicious"] = True
            suspicious["reasons"].append("long_url")
            suspicious["details"]["url_length"] = len(str(request.url))

        return suspicious

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support

        Args:
            request: FastAPI request

        Returns:
            Client IP address
        """
        # Check for forwarded IP
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to client IP
        return request.client.host if request.client else "unknown"

    def get_security_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """Get security metrics from logs

        Args:
            hours: Number of hours to analyze

        Returns:
            Security metrics dictionary
        """
        # This is a simplified version - in production, you'd use a log analysis tool
        # or database to efficiently query logs
        metrics = {
            "period_hours": hours,
            "authentication": {
                "successful_logins": 0,
                "failed_logins": 0,
                "unique_ips": set(),
            },
            "authorization": {
                "permissions_denied": 0,
                "unauthorized_attempts": 0,
            },
            "security_violations": {
                "sql_injection_attempts": 0,
                "xss_attempts": 0,
                "rate_limit_violations": 0,
            },
        }

        # In a real implementation, you'd parse the log file or query a log database
        # For now, return empty metrics
        return {k: v if not isinstance(v, set) else list(v) for k, v in metrics.items()}

    def export_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[SecurityEventType]] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Export security logs with filtering

        Args:
            start_time: Start time for filtering
            end_time: End time for filtering
            event_types: Filter by event types
            user_id: Filter by user ID

        Returns:
            List of log entries
        """
        # This is a placeholder - in production, you'd implement actual log export
        # functionality using log files or a log management system
        return []


# Global security logger instance
_security_logger = None


def get_security_logger() -> SecurityLogger:
    """Get global security logger instance"""
    global _security_logger
    if _security_logger is None:
        _security_logger = SecurityLogger()
    return _security_logger


def configure_security_logging(
    log_file: Optional[str] = None,
    log_level: int = logging.INFO,
    enable_json_format: bool = True,
) -> None:
    """Configure global security logging

    Args:
        log_file: Path to log file
        log_level: Logging level
        enable_json_format: Enable JSON format
    """
    global _security_logger
    _security_logger = SecurityLogger(
        log_file=log_file, log_level=log_level, enable_json_format=enable_json_format
    )


# Convenience functions for logging
def log_security_event(event_type: SecurityEventType, message: str, **kwargs) -> None:
    """Log a security event using the global logger"""
    get_security_logger().log_security_event(event_type, message, **kwargs)


def log_auth_event(event_type: SecurityEventType, user_id: str, ip_address: str, **kwargs) -> None:
    """Log an authentication event using the global logger"""
    get_security_logger().log_authentication_event(event_type, user_id, ip_address, **kwargs)


def log_security_violation(
    violation_type: SecurityEventType, description: str, ip_address: str, **kwargs
) -> None:
    """Log a security violation using the global logger"""
    get_security_logger().log_security_violation(violation_type, description, ip_address, **kwargs)
