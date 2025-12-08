"""
Authentication and authorization exception hierarchy for FastAPI-Easy.

This module provides comprehensive exceptions for authentication and authorization
failures with detailed error information and security considerations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .base import (
    ErrorCategory,
    ErrorCode,
    ErrorSeverity,
    FastAPIEasyException,
)


class AuthenticationException(FastAPIEasyException):
    """Base exception for authentication failures."""

    def __init__(
        self,
        message: str = "Authentication failed",
        auth_method: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AUTHENTICATION_FAILED,
            status_code=401,  # Unauthorized
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        if auth_method:
            self.with_context(auth_method=auth_method)

    def to_dict(self, include_debug: bool = False) -> Dict[str, Any]:
        """Override to prevent sensitive information leakage."""
        error_dict = super().to_dict(include_debug=include_debug)

        # Remove potentially sensitive context in production
        if not include_debug:
            if "context" in error_dict["error"]:
                sensitive_keys = ["user_agent", "ip_address", "token", "session_id"]
                for key in sensitive_keys:
                    error_dict["error"]["context"].pop(key, None)

        return error_dict


class AuthorizationException(FastAPIEasyException):
    """Base exception for authorization failures."""

    def __init__(
        self,
        message: str = "Permission denied",
        resource: Optional[str] = None,
        action: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AUTHORIZATION_FAILED,
            status_code=403,  # Forbidden
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        if resource:
            self.with_context(resource=resource)
        if action:
            self.with_context(action=action)


class TokenException(AuthenticationException):
    """Base exception for token-related authentication errors."""

    def __init__(
        self,
        message: str,
        token_type: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            auth_method=f"token_{token_type}" if token_type else "token",
            **kwargs,
        )

        if token_type:
            self.with_context(token_type=token_type)


class TokenExpiredException(TokenException):
    """Raised when authentication token has expired."""

    def __init__(
        self,
        expires_at: Optional[str] = None,
        token_type: str = "access",
        **kwargs,
    ):
        message = f"{token_type.title()} token has expired"
        if expires_at:
            message += f" (expired at: {expires_at})"

        super().__init__(
            message=message,
            code=ErrorCode.TOKEN_EXPIRED,
            token_type=token_type,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_details(
            suggestion="Please refresh your token and try again",
            documentation_url="https://docs.fastapi-easy.com/auth/token-refresh",
        )


class TokenInvalidException(TokenException):
    """Raised when authentication token is invalid or malformed."""

    def __init__(
        self,
        reason: Optional[str] = None,
        token_type: str = "access",
        **kwargs,
    ):
        message = f"{token_type.title()} token is invalid"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            code=ErrorCode.TOKEN_INVALID,
            token_type=token_type,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_details(
            suggestion=(
                "Please obtain a new valid token\n"
                "Common causes:\n"
                "- Token was tampered with\n"
                "- Incorrect token format\n"
                "- Invalid signature"
            ),
        )


class TokenMissingException(TokenException):
    """Raised when required authentication token is missing."""

    def __init__(
        self,
        location: Optional[str] = None,
        token_type: str = "access",
        **kwargs,
    ):
        message = f"{token_type.title()} token is required"
        if location:
            message += f" in {location}"

        super().__init__(
            message=message,
            code=ErrorCode.TOKEN_MISSING,
            token_type=token_type,
            severity=ErrorSeverity.LOW,
            **kwargs,
        )

        self.with_details(
            suggestion=f"Please provide a valid {token_type} token",
            documentation_url="https://docs.fastapi-easy.com/auth/token-usage",
        )


class CredentialsException(AuthenticationException):
    """Raised when user credentials are invalid."""

    def __init__(
        self,
        credential_type: Optional[str] = None,
        reason: Optional[str] = None,
        **kwargs,
    ):
        message = "Invalid credentials"
        if credential_type:
            message = f"Invalid {credential_type}"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            code=ErrorCode.CREDENTIALS_INVALID,
            auth_method="credentials",
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        # Note: Don't include specific reasons in error response for security
        self.with_details(
            suggestion=(
                "Please check your credentials and try again\n"
                "Make sure:\n"
                "- Username/email is correct\n"
                "- Password is correct\n"
                "- Account is not locked"
            ),
        )


class PermissionDeniedException(AuthorizationException):
    """Raised when user lacks specific permission."""

    def __init__(
        self,
        permission: str,
        resource: Optional[str] = None,
        user_permissions: Optional[list] = None,
        **kwargs,
    ):
        message = f"Permission '{permission}' is required"
        if resource:
            message += f" to access resource '{resource}'"

        super().__init__(
            message=message,
            code=ErrorCode.PERMISSION_DENIED,
            resource=resource,
            action=permission,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_context(required_permission=permission)
        self.with_details(
            suggestion=(
                "To resolve this issue:\n"
                "1. Contact your administrator to grant the required permission\n"
                "2. Ensure you're logged in with the correct account\n"
                "3. Check if your account has the necessary role"
            ),
        )


class AccountLockedException(AuthenticationException):
    """Raised when user account is locked."""

    def __init__(
        self,
        lock_reason: Optional[str] = None,
        locked_until: Optional[str] = None,
        **kwargs,
    ):
        message = "Account has been locked"
        if lock_reason:
            message += f" ({lock_reason})"
        if locked_until:
            message += f" until {locked_until}"

        super().__init__(
            message=message,
            code=ErrorCode.ACCOUNT_LOCKED,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )

        self.with_context(
            lock_reason=lock_reason,
            locked_until=locked_until,
        )
        self.with_details(
            suggestion=(
                "To unlock your account:\n"
                "1. Contact your system administrator\n"
                "2. Wait for the lock to expire (if temporary)\n"
                "3. Follow password reset procedures if applicable"
            ),
        )


class AccountExpiredException(AuthenticationException):
    """Raised when user account has expired."""

    def __init__(
        self,
        expired_at: Optional[str] = None,
        renewal_url: Optional[str] = None,
        **kwargs,
    ):
        message = "Account has expired"
        if expired_at:
            message += f" on {expired_at}"

        super().__init__(
            message=message,
            code=ErrorCode.ACCOUNT_EXPIRED,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_context(expired_at=expired_at)
        self.with_details(
            suggestion=(
                "To continue using your account:\n"
                "1. Contact your administrator for account renewal\n"
                "2. Update your account information if required\n"
                "3. Complete any necessary verification processes"
            ),
            documentation_url=renewal_url,
        )


class SessionExpiredException(AuthenticationException):
    """Raised when user session has expired."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        last_activity: Optional[str] = None,
        **kwargs,
    ):
        message = "Session has expired"
        if last_activity:
            message += f" (last activity: {last_activity})"

        super().__init__(
            message=message,
            auth_method="session",
            code=ErrorCode.TOKEN_EXPIRED,  # Reuse token expired code
            severity=ErrorSeverity.LOW,
            **kwargs,
        )

        self.with_context(session_id=session_id, last_activity=last_activity)
        self.with_details(
            suggestion="Please log in again to continue",
            documentation_url="https://docs.fastapi-easy.com/auth/session-management",
        )


class MultiFactorAuthException(AuthenticationException):
    """Raised when multi-factor authentication fails."""

    def __init__(
        self,
        factor_type: str,
        reason: Optional[str] = None,
        attempts_remaining: Optional[int] = None,
        **kwargs,
    ):
        message = f"Multi-factor authentication failed for {factor_type}"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            auth_method="mfa",
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_context(factor_type=factor_type, attempts_remaining=attempts_remaining)
        self.with_details(
            suggestion=(
                f"Please check your {factor_type} and try again\n"
                "Common issues:\n"
                "- Time-based codes may have expired\n"
                "- Backup codes may have been used\n"
                "- Device may not be registered"
            ),
        )


class RateLimitExceededException(AuthenticationException):
    """Raised when authentication rate limit is exceeded."""

    def __init__(
        self,
        limit_type: str,
        reset_time: Optional[str] = None,
        **kwargs,
    ):
        message = f"Rate limit exceeded for {limit_type}"
        if reset_time:
            message += f". Resets at {reset_time}"

        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMITED,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_context(limit_type=limit_type, reset_time=reset_time)
        self.with_details(
            suggestion=(
                "Please wait before trying again\n"
                "To avoid rate limits:\n"
                "- Implement proper retry logic with backoff\n"
                "- Use caching where appropriate\n"
                "- Contact admin for higher limits if needed"
            ),
        )


class SecurityPolicyException(AuthorizationException):
    """Raised when security policy violation occurs."""

    def __init__(
        self,
        policy: str,
        violation: str,
        **kwargs,
    ):
        message = f"Security policy violation: {violation}"

        super().__init__(
            message=message,
            code=ErrorCode.FORBIDDEN,  # Use generic forbidden code
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )

        self.with_context(policy=policy, violation=violation)
        self.with_details(
            suggestion=(
                "Security policies are in place to protect the system\n"
                "To resolve this issue:\n"
                "1. Review the security policy requirements\n"
                "2. Ensure your request complies with all policies\n"
                "3. Contact security team for clarification if needed"
            ),
        )
