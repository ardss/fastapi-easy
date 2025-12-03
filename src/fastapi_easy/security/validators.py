"""Input validation for security module"""

import re
from typing import Optional

from pydantic import BaseModel, field_validator


class PermissionCheckRequest(BaseModel):
    """Validation model for permission check requests"""

    user_id: str
    permission: str
    resource_id: Optional[str] = None

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        """Validate user_id

        Args:
            v: User ID value

        Returns:
            Validated user ID

        Raises:
            ValueError: If user_id is invalid
        """
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        if len(v) > 255:
            raise ValueError("user_id too long (max 255 characters)")
        if not re.match(r"^[a-zA-Z0-9_\-\.@]+$", v):
            raise ValueError(
                "user_id contains invalid characters " "(allowed: alphanumeric, _, -, ., @)"
            )
        return v

    @field_validator("permission")
    @classmethod
    def validate_permission(cls, v):
        """Validate permission

        Args:
            v: Permission value

        Returns:
            Validated permission

        Raises:
            ValueError: If permission is invalid
        """
        if not v or not v.strip():
            raise ValueError("permission cannot be empty")
        if len(v) > 100:
            raise ValueError("permission too long (max 100 characters)")
        if not re.match(r"^[a-z_]+$", v):
            raise ValueError("permission contains invalid characters " "(allowed: lowercase, _)")
        return v

    @field_validator("resource_id")
    @classmethod
    def validate_resource_id(cls, v):
        """Validate resource_id

        Args:
            v: Resource ID value

        Returns:
            Validated resource ID

        Raises:
            ValueError: If resource_id is invalid
        """
        if v is None:
            return v

        if not v or not v.strip():
            raise ValueError("resource_id cannot be empty if provided")
        if len(v) > 255:
            raise ValueError("resource_id too long (max 255 characters)")
        if not re.match(r"^[a-zA-Z0-9_\-\.:/]+$", v):
            raise ValueError(
                "resource_id contains invalid characters " "(allowed: alphanumeric, _, -, ., :, /)"
            )
        return v


class ResourceOwnershipCheckRequest(BaseModel):
    """Validation model for resource ownership check requests"""

    user_id: str
    resource_id: str

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        """Validate user_id"""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        if len(v) > 255:
            raise ValueError("user_id too long (max 255 characters)")
        if not re.match(r"^[a-zA-Z0-9_\-\.@]+$", v):
            raise ValueError(
                "user_id contains invalid characters " "(allowed: alphanumeric, _, -, ., @)"
            )
        return v

    @field_validator("resource_id")
    @classmethod
    def validate_resource_id(cls, v):
        """Validate resource_id"""
        if not v or not v.strip():
            raise ValueError("resource_id cannot be empty")
        if len(v) > 255:
            raise ValueError("resource_id too long (max 255 characters)")
        if not re.match(r"^[a-zA-Z0-9_\-\.:/]+$", v):
            raise ValueError(
                "resource_id contains invalid characters " "(allowed: alphanumeric, _, -, ., :, /)"
            )
        return v


class BatchPermissionCheckRequest(BaseModel):
    """Validation model for batch permission check requests"""

    user_id: str
    permissions: list

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v):
        """Validate user_id"""
        if not v or not v.strip():
            raise ValueError("user_id cannot be empty")
        if len(v) > 255:
            raise ValueError("user_id too long (max 255 characters)")
        if not re.match(r"^[a-zA-Z0-9_\-\.@]+$", v):
            raise ValueError(
                "user_id contains invalid characters " "(allowed: alphanumeric, _, -, ., @)"
            )
        return v

    @field_validator("permissions")
    @classmethod
    def validate_permissions(cls, v):
        """Validate permissions list"""
        if not v or len(v) == 0:
            raise ValueError("permissions list cannot be empty")
        if len(v) > 100:
            raise ValueError("permissions list too long (max 100 items)")

        for perm in v:
            if not isinstance(perm, str):
                raise ValueError("each permission must be a string")
            if not perm or not perm.strip():
                raise ValueError("permission cannot be empty")
            if len(perm) > 100:
                raise ValueError("permission too long (max 100 characters)")
            if not re.match(r"^[a-z_]+$", perm):
                raise ValueError(
                    "permission contains invalid characters " "(allowed: lowercase, _)"
                )

        return v
