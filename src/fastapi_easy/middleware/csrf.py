"""CSRF protection middleware for FastAPI-Easy"""

from __future__ import annotations

import logging
import secrets
from typing import Optional, Set

from fastapi import FastAPI, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware"""

    def __init__(
        self,
        app: FastAPI,
        secret_key: Optional[str] = None,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        safe_methods: Set[str] = {"GET", "HEAD", "OPTIONS", "TRACE"},
        cookie_secure: bool = True,
        cookie_httponly: bool = False,
        cookie_samesite: str = "lax",
        token_length: int = 32,
    ):
        """Initialize CSRF middleware

        Args:
            app: FastAPI application
            secret_key: Secret key for signing (default: random)
            cookie_name: CSRF token cookie name
            header_name: CSRF token header name
            safe_methods: HTTP methods that don't need CSRF protection
            cookie_secure: Set Secure flag on cookie
            cookie_httponly: Set HttpOnly flag on cookie
            cookie_samesite: SameSite attribute
            token_length: Length of CSRF token
        """
        super().__init__(app)
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.safe_methods = safe_methods
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite
        self.token_length = token_length

    async def dispatch(self, request: Request, call_next):
        """Process request and apply CSRF protection"""

        # Skip CSRF protection for safe methods
        if request.method.upper() in self.safe_methods:
            response = await call_next(request)
            # Set CSRF token cookie for safe methods
            self._set_csrf_cookie(request, response)
            return response

        # Validate CSRF token for unsafe methods
        await self._validate_csrf_token(request)

        response = await call_next(request)
        return response

    def _set_csrf_cookie(self, request: Request, response: Response):
        """Set CSRF token cookie"""
        if self.cookie_name in request.cookies:
            return  # Token already exists

        token = secrets.token_urlsafe(self.token_length)
        response.set_cookie(
            key=self.cookie_name,
            value=token,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite,
            max_age=3600,  # 1 hour
        )

    async def _validate_csrf_token(self, request: Request):
        """Validate CSRF token"""
        # Get token from cookie
        cookie_token = request.cookies.get(self.cookie_name)
        if not cookie_token:
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing from cookie",
                headers={"X-Error": "CSRF protection"},
            )

        # Get token from header
        header_token = request.headers.get(self.header_name)
        if not header_token:
            raise HTTPException(
                status_code=403,
                detail="CSRF token missing from header",
                headers={"X-Error": "CSRF protection"},
            )

        # Validate tokens match
        if not secrets.compare_digest(cookie_token, header_token):
            logger.warning(
                "CSRF token mismatch: cookie=%s, header=%s",
                cookie_token[:8] + "...",
                header_token[:8] + "...",
            )
            raise HTTPException(
                status_code=403,
                detail="CSRF token invalid",
                headers={"X-Error": "CSRF protection"},
            )

    @staticmethod
    def get_csrf_token(request: Request) -> Optional[str]:
        """Get CSRF token from request cookies"""
        return request.cookies.get("csrf_token")
