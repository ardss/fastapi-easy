"""Security decorators for FastAPI-Easy"""

from functools import wraps
from typing import Callable, List, Optional

from fastapi import Depends, Header, HTTPException

from .exceptions import (
    AuthenticationError,
    AuthorizationError,
    InvalidTokenError,
    TokenExpiredError,
)
from .jwt_auth import JWTAuth

# Global JWT auth instance
_jwt_auth: Optional[JWTAuth] = None


def init_jwt_auth(
    secret_key: Optional[str] = None,
    algorithm: str = "HS256",
    access_token_expire_minutes: int = 15,
    refresh_token_expire_days: int = 7,
) -> JWTAuth:
    """Initialize global JWT auth instance

    Args:
        secret_key: Secret key for signing tokens
        algorithm: JWT algorithm
        access_token_expire_minutes: Access token expiration time
        refresh_token_expire_days: Refresh token expiration time

    Returns:
        JWTAuth instance
    """
    global _jwt_auth
    _jwt_auth = JWTAuth(
        secret_key=secret_key,
        algorithm=algorithm,
        access_token_expire_minutes=access_token_expire_minutes,
        refresh_token_expire_days=refresh_token_expire_days,
    )
    return _jwt_auth


def get_jwt_auth() -> JWTAuth:
    """Get global JWT auth instance

    Returns:
        JWTAuth instance

    Raises:
        RuntimeError: If JWT auth is not initialized
    """
    if _jwt_auth is None:
        raise RuntimeError("JWT auth is not initialized. Call init_jwt_auth() first.")
    return _jwt_auth


async def get_current_user(
    authorization: Optional[str] = Header(None),
) -> dict:
    """Get current user from JWT token

    Args:
        authorization: Authorization header

    Returns:
        User payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    if not authorization:
        raise HTTPException(status_code=403, detail="Missing authorization header")

    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=403, detail="Invalid authorization header")

    token = parts[1]
    jwt_auth = get_jwt_auth()

    try:
        payload = jwt_auth.verify_token(token)
        return {
            "user_id": payload.sub,
            "roles": payload.roles,
            "permissions": payload.permissions,
            "token_type": payload.type,
        }
    except TokenExpiredError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
) -> Optional[dict]:
    """Get current user from JWT token (optional)

    Args:
        authorization: Authorization header (optional)

    Returns:
        User payload or None

    Raises:
        HTTPException: If token is invalid or expired
    """
    if authorization is None:
        return None

    return await get_current_user(authorization)


def require_role(*roles: str):
    """Require user to have one of the specified roles

    Args:
        *roles: Required roles

    Returns:
        Dependency function
    """

    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        """Check if user has required role

        Args:
            current_user: Current user payload

        Returns:
            Current user payload

        Raises:
            HTTPException: If user does not have required role
        """
        user_roles = current_user.get("roles", [])
        if not any(role in user_roles for role in roles):
            raise HTTPException(
                status_code=403,
                detail=f"User does not have required role. Required: {roles}",
            )
        return current_user

    return role_checker


def require_permission(*permissions: str):
    """Require user to have one of the specified permissions

    Args:
        *permissions: Required permissions

    Returns:
        Dependency function
    """

    async def permission_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        """Check if user has required permission

        Args:
            current_user: Current user payload

        Returns:
            Current user payload

        Raises:
            HTTPException: If user does not have required permission
        """
        user_permissions = current_user.get("permissions", [])
        if not any(perm in user_permissions for perm in permissions):
            raise HTTPException(
                status_code=403,
                detail=f"User does not have required permission. Required: {permissions}",
            )
        return current_user

    return permission_checker


def require_all_roles(*roles: str):
    """Require user to have all specified roles

    Args:
        *roles: Required roles

    Returns:
        Dependency function
    """

    async def all_roles_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        """Check if user has all required roles

        Args:
            current_user: Current user payload

        Returns:
            Current user payload

        Raises:
            HTTPException: If user does not have all required roles
        """
        user_roles = current_user.get("roles", [])
        if not all(role in user_roles for role in roles):
            raise HTTPException(
                status_code=403,
                detail=f"User does not have all required roles. Required: {roles}",
            )
        return current_user

    return all_roles_checker


def require_all_permissions(*permissions: str):
    """Require user to have all specified permissions

    Args:
        *permissions: Required permissions

    Returns:
        Dependency function
    """

    async def all_permissions_checker(
        current_user: dict = Depends(get_current_user),
    ) -> dict:
        """Check if user has all required permissions

        Args:
            current_user: Current user payload

        Returns:
            Current user payload

        Raises:
            HTTPException: If user does not have all required permissions
        """
        user_permissions = current_user.get("permissions", [])
        if not all(perm in user_permissions for perm in permissions):
            raise HTTPException(
                status_code=403,
                detail=f"User does not have all required permissions. Required: {permissions}",
            )
        return current_user

    return all_permissions_checker
