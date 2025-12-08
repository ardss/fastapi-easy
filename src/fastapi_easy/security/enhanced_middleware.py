"""Enhanced security middleware for FastAPI-Easy with defense-in-depth security measures"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add comprehensive security headers to all responses"""

    def __init__(
        self,
        app: FastAPI,
        include_csp: bool = True,
        csp_policy: Optional[str] = None,
        hsts_max_age: int = 31536000,
        report_uri: Optional[str] = None,
    ):
        """Initialize security headers middleware

        Args:
            app: FastAPI application
            include_csp: Include Content-Security-Policy header
            csp_policy: Custom CSP policy
            hsts_max_age: HSTS max-age in seconds
            report_uri: CSP report URI for violation reports
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.report_uri = report_uri

        # Default CSP policy
        self.csp_policy = csp_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response"""
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS protection in browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HTTP Strict Transport Security
        if request.url.scheme == "https":
            hsts_value = f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            response.headers["Strict-Transport-Security"] = hsts_value

        # Content Security Policy
        if self.csp_policy:
            response.headers["Content-Security-Policy"] = self.csp_policy
            if self.report_uri:
                response.headers["Content-Security-Policy-Report-Only"] = self.csp_policy.replace(
                    "; report-uri", f"; report-uri {self.report_uri}"
                )

        # Permissions Policy
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        response.headers["Permissions-Policy"] = permissions_policy

        return response


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """Sanitize and validate request inputs to prevent injection attacks"""

    def __init__(
        self,
        app: FastAPI,
        blocked_patterns: Optional[List[str]] = None,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        enabled_paths: Optional[Set[str]] = None,
    ):
        """Initialize input sanitization middleware

        Args:
            app: FastAPI application
            blocked_patterns: List of regex patterns to block
            max_request_size: Maximum request size in bytes
            enabled_paths: Paths where middleware is enabled
        """
        super().__init__(app)

        # Default blocked patterns for injection attacks
        self.blocked_patterns = [
            r"<script[^>]*>.*?</script>",  # XSS
            r"javascript:",  # XSS
            r"on\w+\s*=",  # Event handlers
            r"union\s+select",  # SQL injection
            r"drop\s+table",  # SQL injection
            r"insert\s+into",  # SQL injection
            r"delete\s+from",  # SQL injection
            r"eval\s*\(",  # Code injection
            r"exec\s*\(",  # Code injection
            r"system\s*\(",  # Command injection
            r"\$\{.*\}",  # Template injection
            r"<\?php.*\?>",  # PHP injection
            r"@\w+\(",  # C# injection
        ]

        # Custom blocked patterns
        if blocked_patterns:
            self.blocked_patterns.extend(blocked_patterns)

        # Compile regex patterns
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in self.blocked_patterns
        ]

        self.max_request_size = max_request_size
        self.enabled_paths = enabled_paths or {"/", "/api/"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate and sanitize request inputs"""
        # Check if middleware should run for this path
        if not self._should_process_path(request.url.path):
            return await call_next(request)

        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            raise HTTPException(
                status_code=413,
                detail="Request entity too large",
            )

        # Validate JSON data
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.body()
                if body:
                    import json

                    data = json.loads(body.decode())
                    self._validate_data(data)
            except json.JSONDecodeError:
                pass  # Will be handled by FastAPI
            except Exception as e:
                logger.warning(f"Input validation failed: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid input detected",
                )

        # Validate query parameters
        self._validate_query_params(request.query_params)

        # Validate headers
        self._validate_headers(request.headers)

        response = await call_next(request)
        return response

    def _should_process_path(self, path: str) -> bool:
        """Check if middleware should process this path"""
        return any(path.startswith(enabled_path) for enabled_path in self.enabled_paths)

    def _validate_data(self, data: Any, path: str = "") -> None:
        """Recursively validate data structure"""
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                self._validate_data(value, current_path)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                self._validate_data(item, current_path)
        elif isinstance(data, str):
            self._validate_string(data, path)

    def _validate_string(self, value: str, path: str = "") -> None:
        """Validate string for malicious patterns"""
        for pattern in self.compiled_patterns:
            if pattern.search(value):
                logger.warning(f"Malicious input detected at {path}: {pattern.pattern}")
                raise HTTPException(
                    status_code=400,
                    detail="Malicious input detected",
                )

    def _validate_query_params(self, params: Dict[str, str]) -> None:
        """Validate query parameters"""
        for key, value in params.items():
            self._validate_string(value, f"query.{key}")

    def _validate_headers(self, headers: Dict[str, str]) -> None:
        """Validate request headers"""
        # Check for suspicious headers
        suspicious_headers = ["X-Forwarded-Host", "X-Originating-IP"]
        for header in suspicious_headers:
            if header in headers:
                logger.warning(f"Suspicious header detected: {header}")


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Advanced rate limiting with multiple strategies"""

    def __init__(
        self,
        app: FastAPI,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        enabled_paths: Optional[Set[str]] = None,
        exclude_paths: Optional[Set[str]] = None,
    ):
        """Initialize rate limiting middleware

        Args:
            app: FastAPI application
            requests_per_minute: Base rate limit
            burst_size: Maximum burst size
            enabled_paths: Paths where rate limiting is enabled
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)

        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.enabled_paths = enabled_paths or {"/api/"}
        self.exclude_paths = exclude_paths or {"/health", "/metrics"}

        # In-memory rate limiter (for production, use Redis)
        self.clients: Dict[str, Dict[str, Any]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to request"""
        path = request.url.path

        # Skip if path should be excluded
        if self._should_exclude_path(path):
            return await call_next(request)

        # Check if path should be rate limited
        if not self._should_limit_path(path):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        current_time = datetime.now(timezone.utc)

        # Initialize client data if not exists
        if client_ip not in self.clients:
            self.clients[client_ip] = {
                "tokens": self.burst_size,
                "last_refill": current_time,
                "blocked_until": None,
            }

        client_data = self.clients[client_ip]

        # Check if client is temporarily blocked
        if client_data["blocked_until"] and current_time < client_data["blocked_until"]:
            retry_after = int((client_data["blocked_until"] - current_time).total_seconds())
            raise HTTPException(
                status_code=429,
                detail="Too many requests - temporarily blocked",
                headers={"Retry-After": str(retry_after)},
            )

        # Refill tokens based on elapsed time
        time_elapsed = (current_time - client_data["last_refill"]).total_seconds()
        tokens_to_add = (time_elapsed / 60) * self.requests_per_minute
        client_data["tokens"] = min(self.burst_size, client_data["tokens"] + tokens_to_add)
        client_data["last_refill"] = current_time

        # Check if client has tokens available
        if client_data["tokens"] >= 1:
            client_data["tokens"] -= 1
        else:
            # Block client temporarily
            client_data["blocked_until"] = current_time + timezone.utc.timedelta(minutes=5)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "300"},
            )

        response = await call_next(request)

        # Add rate limiting headers
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(int(client_data["tokens"]))
        response.headers["X-RateLimit-Reset"] = str(
            int((current_time + timezone.utc.timedelta(minutes=1)).timestamp())
        )

        return response

    def _should_exclude_path(self, path: str) -> bool:
        """Check if path should be excluded from rate limiting"""
        return path in self.exclude_paths

    def _should_limit_path(self, path: str) -> bool:
        """Check if path should be rate limited"""
        return any(path.startswith(enabled_path) for enabled_path in self.enabled_paths)

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded IP headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to client IP
        return request.client.host if request.client else "unknown"


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """Monitor security events and generate alerts"""

    def __init__(
        self,
        app: FastAPI,
        alert_thresholds: Optional[Dict[str, int]] = None,
        log_all_requests: bool = False,
    ):
        """Initialize security monitoring middleware

        Args:
            app: FastAPI application
            alert_thresholds: Thresholds for various security metrics
            log_all_requests: Whether to log all requests
        """
        super().__init__(app)

        self.alert_thresholds = {
            "failed_auth_per_minute": 10,
            "suspicious_requests_per_minute": 50,
            "large_requests_per_hour": 20,
            **(alert_thresholds or {}),
        }

        self.log_all_requests = log_all_requests

        # Metrics tracking
        self.metrics = {
            "failed_auth_count": 0,
            "suspicious_request_count": 0,
            "large_request_count": 0,
            "last_reset": datetime.now(timezone.utc),
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request for security events"""
        start_time = datetime.now(timezone.utc)
        response = await call_next(request)
        end_time = datetime.now(timezone.utc)

        # Calculate processing time
        processing_time = (end_time - start_time).total_seconds()

        # Log security events
        await self._log_security_event(request, response, processing_time)

        # Check for alert conditions
        await self._check_alert_conditions()

        return response

    async def _log_security_event(
        self,
        request: Request,
        response: Response,
        processing_time: float,
    ) -> None:
        """Log security-related events"""
        if not self.log_all_requests and response.status_code < 400:
            return

        # Check for suspicious patterns
        is_suspicious = self._is_suspicious_request(request, response, processing_time)

        if is_suspicious:
            self.metrics["suspicious_request_count"] += 1

        # Check for failed authentication
        if response.status_code in [401, 403]:
            self.metrics["failed_auth_count"] += 1

        # Check for large requests
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 1024 * 1024:  # 1MB
            self.metrics["large_request_count"] += 1

        # Log the event
        logger.info(
            "Security event logged",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "processing_time": processing_time,
                "ip_address": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent"),
                "is_suspicious": is_suspicious,
            },
        )

    def _is_suspicious_request(
        self,
        request: Request,
        response: Response,
        processing_time: float,
    ) -> bool:
        """Check if request is suspicious"""
        suspicious_indicators = [
            processing_time > 5.0,  # Slow processing time
            response.status_code >= 400,  # Error status
            len(request.url.path) > 1000,  # Very long path
            request.url.path.count("//") > 2,  # Multiple slashes
            request.url.path.count("%") > 10,  # Many encoded characters
        ]

        return any(suspicious_indicators)

    async def _check_alert_conditions(self) -> None:
        """Check if any alert thresholds are exceeded"""
        now = datetime.now(timezone.utc)
        time_elapsed = (now - self.metrics["last_reset"]).total_seconds()

        # Reset metrics if more than 1 hour has passed
        if time_elapsed > 3600:
            self.metrics = {
                **self.metrics,
                "failed_auth_count": 0,
                "suspicious_request_count": 0,
                "large_request_count": 0,
                "last_reset": now,
            }

        # Check thresholds (per minute, scaled)
        minutes_elapsed = max(1, time_elapsed / 60)

        failed_auth_per_minute = self.metrics["failed_auth_count"] / minutes_elapsed
        if failed_auth_per_minute > self.alert_thresholds["failed_auth_per_minute"]:
            await self._trigger_alert("HIGH_FAILED_AUTH_RATE", failed_auth_per_minute)

        suspicious_per_minute = self.metrics["suspicious_request_count"] / minutes_elapsed
        if suspicious_per_minute > self.alert_thresholds["suspicious_requests_per_minute"]:
            await self._trigger_alert("HIGH_SUSPICIOUS_REQUEST_RATE", suspicious_per_minute)

    async def _trigger_alert(self, alert_type: str, value: float) -> None:
        """Trigger security alert"""
        logger.warning(
            f"Security alert triggered: {alert_type}",
            extra={
                "alert_type": alert_type,
                "value": value,
                "threshold": self.alert_thresholds.get(
                    alert_type.split("_")[-1].lower() + "_per_minute"
                ),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"


def configure_security_middleware(
    app: FastAPI,
    config: Optional[Dict[str, Any]] = None,
) -> None:
    """Configure all security middleware for FastAPI application

    Args:
        app: FastAPI application
        config: Security configuration
    """
    config = config or {}

    # Trusted Host middleware
    if config.get("trusted_hosts"):
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=config["trusted_hosts"],
        )

    # Security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        include_csp=config.get("include_csp", True),
        csp_policy=config.get("csp_policy"),
        hsts_max_age=config.get("hsts_max_age", 31536000),
    )

    # Input sanitization
    app.add_middleware(
        InputSanitizationMiddleware,
        blocked_patterns=config.get("blocked_patterns"),
        max_request_size=config.get("max_request_size", 10 * 1024 * 1024),
        enabled_paths=config.get("sanitization_paths"),
    )

    # Rate limiting
    app.add_middleware(
        RateLimitingMiddleware,
        requests_per_minute=config.get("requests_per_minute", 60),
        burst_size=config.get("burst_size", 10),
        enabled_paths=config.get("rate_limit_paths"),
        exclude_paths=config.get("rate_limit_exclude_paths"),
    )

    # Security monitoring
    app.add_middleware(
        SecurityMonitoringMiddleware,
        alert_thresholds=config.get("alert_thresholds"),
        log_all_requests=config.get("log_all_requests", False),
    )
