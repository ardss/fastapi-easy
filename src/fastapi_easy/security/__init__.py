"""Security module for FastAPI-Easy

This module provides authentication and authorization features:
- JWT token generation and verification
- Role-based access control (RBAC)
- Permission-based access control
- Decorators for route protection
- Password hashing and verification
- Rate limiting and brute force protection
- Audit logging for security events
"""

from .audit_log import AuditEventType, AuditLog, AuditLogger
from .decorators import (
    get_current_user,
    get_current_user_optional,
    get_jwt_auth,
    init_jwt_auth,
    require_all_permissions,
    require_all_roles,
    require_permission,
    require_role,
)
from .exceptions import (
    AccountLockedError,
    AuthenticationError,
    AuthorizationError,
    InsufficientPermissionError,
    InvalidCredentialsError,
    InvalidTokenError,
    RoleNotFoundError,
    SecurityException,
    TokenExpiredError,
    UserNotFoundError,
)
from .jwt_auth import JWTAuth
from .models import (
    ErrorResponse,
    LoginResponse,
    PermissionBase,
    PermissionResponse,
    RefreshTokenRequest,
    RoleBase,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    TokenPayload,
    TokenRequest,
    TokenResponse,
    UserBase,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from .password import PasswordManager
from .permission_engine import PermissionEngine
from .permission_loader import (
    CachedPermissionLoader,
    DatabasePermissionLoader,
    PermissionLoader,
    StaticPermissionLoader,
)
from .rate_limit import LoginAttemptTracker
from .resource_checker import (
    CachedResourceChecker,
    DatabaseResourceChecker,
    ResourcePermissionChecker,
    StaticResourceChecker,
)
from .security_config import SecurityConfig

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
    # Password & Security
    "PasswordManager",
    "LoginAttemptTracker",
    "AuditLogger",
    "AuditLog",
    "AuditEventType",
    # Permission Loaders
    "PermissionLoader",
    "StaticPermissionLoader",
    "DatabasePermissionLoader",
    "CachedPermissionLoader",
    # Resource Checkers
    "ResourcePermissionChecker",
    "StaticResourceChecker",
    "DatabaseResourceChecker",
    "CachedResourceChecker",
    # Security Config & Engine
    "SecurityConfig",
    "PermissionEngine",
]
