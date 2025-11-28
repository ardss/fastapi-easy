"""Security module for FastAPI-Easy

This module provides authentication and authorization features:
- JWT token generation and verification
- Role-based access control (RBAC)
- Permission-based access control
- Decorators for route protection
"""

from .jwt_auth import JWTAuth
from .decorators import (
    init_jwt_auth,
    get_jwt_auth,
    get_current_user,
    get_current_user_optional,
    require_role,
    require_permission,
    require_all_roles,
    require_all_permissions,
)
from .exceptions import (
    SecurityException,
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    TokenExpiredError,
    InvalidCredentialsError,
    UserNotFoundError,
    AccountLockedError,
    InsufficientPermissionError,
    RoleNotFoundError,
)
from .models import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    TokenRequest,
    TokenResponse,
    RefreshTokenRequest,
    TokenPayload,
    RoleBase,
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    PermissionBase,
    PermissionResponse,
    LoginResponse,
    ErrorResponse,
)

__all__ = [
    # JWT Auth
    "JWTAuth",
    # Decorators
    "init_jwt_auth",
    "get_jwt_auth",
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_permission",
    "require_all_roles",
    "require_all_permissions",
    # Exceptions
    "SecurityException",
    "AuthenticationError",
    "AuthorizationError",
    "InvalidTokenError",
    "TokenExpiredError",
    "InvalidCredentialsError",
    "UserNotFoundError",
    "AccountLockedError",
    "InsufficientPermissionError",
    "RoleNotFoundError",
    # Models
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "TokenRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "TokenPayload",
    "RoleBase",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    "PermissionBase",
    "PermissionResponse",
    "LoginResponse",
    "ErrorResponse",
]
