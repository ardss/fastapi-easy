"""Security middleware for FastAPI-Easy"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Set

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..core.jwt_auth import JWTAuth
from ..exceptions import (
    AuthenticationError,
    AuthorizationError,
)
from ..validation.input_validator import InputValidationError, SecurityValidator

logger = logging.getLogger(__name__)

# Rate limiting store (in production, use Redis or similar)
_rate_limit_store: Dict[str, List[float]] = {}
_blacklisted_ips: Set[str] = set()


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware for FastAPI"""

    def __init__(
        self,
        app,
        jwt_auth: Optional[JWTAuth] = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_hour: int = 1000,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        require_auth_paths: Optional[List[str]] = None,
        skip_auth_paths: Optional[List[str]] = None,
        enable_input_validation: bool = True,
        enable_cors: bool = True,
        allowed_origins: Optional[List[str]] = None,
    ):
        """Initialize security middleware

        Args:
            app: FastAPI app
            jwt_auth: JWT authentication instance
            rate_limit_per_minute: Rate limit per minute per IP
            rate_limit_per_hour: Rate limit per hour per IP
            max_request_size: Maximum request size in bytes
            require_auth_paths: Paths that require authentication
            skip_auth_paths: Paths to skip authentication
            enable_input_validation: Enable input validation and sanitization
            enable_cors: Enable CORS headers
            allowed_origins: List of allowed CORS origins
        """
        super().__init__(app)
        self.jwt_auth = jwt_auth
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_per_hour = rate_limit_per_hour
        self.max_request_size = max_request_size
        self.enable_input_validation = enable_input_validation
        self.enable_cors = enable_cors

        # Path configurations
        self.require_auth_paths = set(require_auth_paths or [])
        self.skip_auth_paths = set(
            skip_auth_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
        )

        # CORS configuration
        self.allowed_origins = allowed_origins or ["*"]

        # Security headers
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with security checks"""
        try:
            # Get client IP
            client_ip = self._get_client_ip(request)

            # Check if IP is blacklisted
            if client_ip in _blacklisted_ips:
                logger.warning(f"Blacklisted IP attempted access: {client_ip}")
                return self._create_error_response(
                    "Access denied", status.HTTP_403_FORBIDDEN, "IP_BLACKLISTED"
                )

            # Check rate limiting
            if not await self._check_rate_limit(client_ip):
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                return self._create_error_response(
                    "Rate limit exceeded", status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMIT_EXCEEDED"
                )

            # Check request size
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.max_request_size:
                logger.warning(f"Request too large from IP: {client_ip}, size: {content_length}")
                return self._create_error_response(
                    "Request too large",
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    "REQUEST_TOO_LARGE",
                )

            # Add security headers
            response = await self._process_request(request, call_next)

            # Add security headers to response
            for header, value in self.security_headers.items():
                response.headers[header] = value

            # Add CORS headers if enabled
            if self.enable_cors:
                self._add_cors_headers(request, response)

            return response

        except Exception as e:
            logger.error(f"Security middleware error: {e!s}", exc_info=True)
            return self._create_error_response(
                "Internal security error", status.HTTP_500_INTERNAL_SERVER_ERROR, "SECURITY_ERROR"
            )

    async def _process_request(self, request: Request, call_next) -> Response:
        """Process request with authentication and validation"""
        # Check if authentication is required for this path
        path = request.url.path
        requires_auth = self._requires_auth(path)

        # Validate and sanitize input if enabled
        if self.enable_input_validation and request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_request_body(request)

        # Check authentication if required
        if requires_auth and self.jwt_auth:
            await self._authenticate_request(request)

        # Process the request
        response = await call_next(request)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support"""
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

    async def _check_rate_limit(self, client_ip: str) -> bool:
        """Check if client has exceeded rate limits"""
        now = time.time()

        # Initialize rate limit entry if not exists
        if client_ip not in _rate_limit_store:
            _rate_limit_store[client_ip] = []

        # Clean old entries
        _rate_limit_store[client_ip] = [
            timestamp
            for timestamp in _rate_limit_store[client_ip]
            if now - timestamp < 3600  # Keep last hour
        ]

        # Check minute limit
        minute_requests = [
            timestamp for timestamp in _rate_limit_store[client_ip] if now - timestamp < 60
        ]
        if len(minute_requests) >= self.rate_limit_per_minute:
            return False

        # Check hour limit
        if len(_rate_limit_store[client_ip]) >= self.rate_limit_per_hour:
            return False

        # Add current request
        _rate_limit_store[client_ip].append(now)
        return True

    def _requires_auth(self, path: str) -> bool:
        """Check if path requires authentication"""
        # Skip auth for specified paths
        if any(path.startswith(skip_path) for skip_path in self.skip_auth_paths):
            return False

        # Require auth for specified paths
        if any(path.startswith(req_path) for req_path in self.require_auth_paths):
            return True

        # Default behavior - require auth for all non-public paths
        return not path.startswith("/public/") and path != "/"

    async def _validate_request_body(self, request: Request) -> None:
        """Validate and sanitize request body"""
        try:
            body = await request.json()
            # Validate and sanitize input
            sanitized = SecurityValidator.comprehensive_validation(body)

            # Replace request body with sanitized version
            # Note: In FastAPI, we need to use request.state to store sanitized data
            request.state.sanitized_body = sanitized

        except Exception as e:
            if isinstance(e, InputValidationError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid input: {e!s}"
                )
            # Non-JSON requests are skipped
            pass

    async def _authenticate_request(self, request: Request) -> None:
        """Authenticate request using JWT"""
        try:
            # Get authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                raise AuthenticationError("Missing authorization header")

            # Extract token
            if not authorization.startswith("Bearer "):
                raise AuthenticationError("Invalid authorization header format")

            token = authorization[7:]  # Remove "Bearer " prefix

            # Verify token
            if not self.jwt_auth:
                raise AuthenticationError("JWT authentication not configured")

            client_ip = self._get_client_ip(request)
            payload = self.jwt_auth.verify_token(token, client_identifier=client_ip)

            # Store payload in request state
            request.state.user = payload

        except (AuthenticationError, AuthorizationError) as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e),
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _add_cors_headers(self, request: Request, response: Response) -> None:
        """Add CORS headers to response"""
        origin = request.headers.get("Origin")

        # Check if origin is allowed
        if origin and (self.allowed_origins == ["*"] or origin in self.allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin

        # Add other CORS headers
        response.headers.update(
            {
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type, X-Requested-With",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "86400",  # 24 hours
            }
        )

    def _create_error_response(
        self, message: str, status_code: int, error_code: str
    ) -> JSONResponse:
        """Create standardized error response"""
        return JSONResponse(
            status_code=status_code,
            content={
                "error": message,
                "error_code": error_code,
                "status_code": status_code,
                "timestamp": time.time(),
            },
        )


# Rate limiter utility
class RateLimiter:
    """Advanced rate limiter with multiple strategies"""

    def __init__(self, storage=None):
        """Initialize rate limiter"""
        self.storage = storage or _rate_limit_store

    async def is_allowed(
        self, key: str, limit: int, window: int, strategy: str = "sliding_window"
    ) -> bool:
        """Check if request is allowed

        Args:
            key: Rate limit key (e.g., IP address, user ID)
            limit: Maximum requests allowed
            window: Time window in seconds
            strategy: Rate limiting strategy

        Returns:
            True if allowed, False otherwise
        """
        now = time.time()

        if key not in self.storage:
            self.storage[key] = []

        # Clean old entries
        self.storage[key] = [
            timestamp for timestamp in self.storage[key] if now - timestamp < window
        ]

        # Check limit
        return len(self.storage[key]) < limit

    async def record_request(self, key: str) -> None:
        """Record a request for rate limiting"""
        if key not in self.storage:
            self.storage[key] = []
        self.storage[key].append(time.time())

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key"""
        if key in self.storage:
            del self.storage[key]


# IP blacklist utility
class IPBlacklist:
    """IP blacklist management"""

    @staticmethod
    def add_ip(ip: str) -> None:
        """Add IP to blacklist"""
        _blacklisted_ips.add(ip)
        logger.info(f"IP added to blacklist: {ip}")

    @staticmethod
    def remove_ip(ip: str) -> None:
        """Remove IP from blacklist"""
        _blacklisted_ips.discard(ip)
        logger.info(f"IP removed from blacklist: {ip}")

    @staticmethod
    def is_blacklisted(ip: str) -> bool:
        """Check if IP is blacklisted"""
        return ip in _blacklisted_ips

    @staticmethod
    def get_all() -> Set[str]:
        """Get all blacklisted IPs"""
        return _blacklisted_ips.copy()


# Security headers utility
def get_security_headers(
    include_csp: bool = True, include_hsts: bool = True, csp_policy: Optional[str] = None
) -> Dict[str, str]:
    """Get security headers for responses

    Args:
        include_csp: Include Content-Security-Policy header
        include_hsts: Include Strict-Transport-Security header
        csp_policy: Custom CSP policy

    Returns:
        Dictionary of security headers
    """
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    }

    if include_csp:
        headers["Content-Security-Policy"] = (
            csp_policy
            or "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
        )

    if include_hsts:
        headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    return headers
