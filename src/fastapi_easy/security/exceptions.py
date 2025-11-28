"""Security exceptions for FastAPI-Easy"""

from typing import Optional


class SecurityException(Exception):
    """Base security exception"""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: Optional[str] = None,
    ):
        """Initialize security exception

        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Error code for client
        """
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)


class AuthenticationError(SecurityException):
    """Authentication failed (401)"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_FAILED",
        )


class AuthorizationError(SecurityException):
    """Authorization failed (403)"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_FAILED",
        )


class InvalidTokenError(AuthenticationError):
    """Invalid JWT token"""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message)
        self.error_code = "INVALID_TOKEN"


class TokenExpiredError(AuthenticationError):
    """JWT token expired"""

    def __init__(self, message: str = "Token expired"):
        super().__init__(message=message)
        self.error_code = "TOKEN_EXPIRED"


class InvalidCredentialsError(AuthenticationError):
    """Invalid username or password"""

    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(message=message)
        self.error_code = "INVALID_CREDENTIALS"


class UserNotFoundError(AuthenticationError):
    """User not found"""

    def __init__(self, message: str = "User not found"):
        super().__init__(message=message)
        self.error_code = "USER_NOT_FOUND"


class AccountLockedError(AuthenticationError):
    """Account is locked due to too many failed login attempts"""

    def __init__(self, message: str = "Account is locked"):
        super().__init__(message=message)
        self.error_code = "ACCOUNT_LOCKED"


class InsufficientPermissionError(AuthorizationError):
    """User does not have required permission"""

    def __init__(self, message: str = "Insufficient permission"):
        super().__init__(message=message)
        self.error_code = "INSUFFICIENT_PERMISSION"


class RoleNotFoundError(AuthorizationError):
    """Role not found"""

    def __init__(self, message: str = "Role not found"):
        super().__init__(message=message)
        self.error_code = "ROLE_NOT_FOUND"
