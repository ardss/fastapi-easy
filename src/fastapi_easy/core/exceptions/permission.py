"""
Permission exception hierarchy for FastAPI-Easy.

This module provides exceptions for permission and access control errors
with detailed information about required and missing permissions.
"""

from __future__ import annotations

from typing import Any, List, Optional, Set

from .base import (
    ErrorCategory,
    ErrorCode,
    ErrorSeverity,
    FastAPIEasyException,
)


class PermissionException(FastAPIEasyException):
    """Base exception for permission-related errors."""

    def __init__(
        self,
        message: str,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.PERMISSION_DENIED,
            status_code=403,  # Forbidden
            category=ErrorCategory.PERMISSION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_context(
            resource=resource,
            action=action,
        )


class ResourcePermissionException(PermissionException):
    """Raised when user lacks permission for a specific resource."""

    def __init__(
        self,
        resource: str,
        resource_id: Optional[Any] = None,
        action: str = "access",
        user_permissions: Optional[List[str]] = None,
        required_permissions: Optional[List[str]] = None,
        **kwargs,
    ):
        message = f"Permission denied for {action} on resource '{resource}'"
        if resource_id:
            message += f" (ID: {resource_id})"

        super().__init__(
            message=message,
            resource=resource,
            action=action,
            **kwargs,
        )

        self.with_context(
            resource_id=resource_id,
            user_permissions=user_permissions or [],
            required_permissions=required_permissions or [],
        )
        self.with_details(
            suggestion=(
                "Resource access solutions:\n"
                "1. Request the required permissions from administrator\n"
                "2. Check if you're accessing the correct resource\n"
                "3. Verify your authentication status\n"
                "4. Contact resource owner if applicable"
            ),
        )


class ActionPermissionException(PermissionException):
    """Raised when user lacks permission for a specific action."""

    def __init__(
        self,
        action: str,
        resource_type: Optional[str] = None,
        user_roles: Optional[List[str]] = None,
        allowed_roles: Optional[List[str]] = None,
        **kwargs,
    ):
        message = f"Permission denied for action '{action}'"
        if resource_type:
            message += f" on resource type '{resource_type}'"

        super().__init__(
            message=message,
            resource=resource_type,
            action=action,
            **kwargs,
        )

        self.with_context(
            user_roles=user_roles or [],
            allowed_roles=allowed_roles or [],
        )
        self.with_details(
            suggestion=(
                "Action permission solutions:\n"
                "1. Ensure you have the required role(s)\n"
                "2. Request role assignment from administrator\n"
                "3. Check if action requires additional privileges\n"
                "4. Verify action is available for your user type"
            ),
        )


class RolePermissionException(PermissionException):
    """Raised when user role lacks required permissions."""

    def __init__(
        self,
        role: str,
        missing_permissions: List[str],
        resource_type: Optional[str] = None,
        available_roles: Optional[List[str]] = None,
        **kwargs,
    ):
        message = f"Role '{role}' lacks required permissions"
        if missing_permissions:
            message += f": {', '.join(missing_permissions)}"
        if resource_type:
            message += f" for resource type '{resource_type}'"

        super().__init__(
            message=message,
            resource=resource_type,
            **kwargs,
        )

        self.with_context(
            user_role=role,
            missing_permissions=missing_permissions,
            available_roles=available_roles or [],
        )
        self.with_details(
            suggestion=(
                "Role permission solutions:\n"
                "1. Assign additional permissions to your role\n"
                "2. Request a role with appropriate permissions\n"
                "3. Check if there's a more suitable role available\n"
                "4. Contact administrator for role management"
            ),
        )


class ScopePermissionException(PermissionException):
    """Raised when user lacks permission for a specific scope."""

    def __init__(
        self,
        required_scope: str,
        granted_scopes: Optional[Set[str]] = None,
        operation: Optional[str] = None,
        **kwargs,
    ):
        message = f"Required scope '{required_scope}' not granted"
        if operation:
            message += f" for operation: {operation}"

        super().__init__(
            message=message,
            action=operation,
            **kwargs,
        )

        self.with_context(
            required_scope=required_scope,
            granted_scopes=list(granted_scopes or []),
        )
        self.with_details(
            suggestion=(
                "Scope permission solutions:\n"
                "1. Request the required scope during authentication\n"
                "2. Re-authenticate with additional scopes\n"
                "3. Check if your application is registered for this scope\n"
                "4. Contact API provider for scope access"
            ),
        )


class OwnershipPermissionException(PermissionException):
    """Raised when user is not the owner of a resource."""

    def __init__(
        self,
        resource: str,
        resource_id: Any,
        owner_id: Optional[Any] = None,
        **kwargs,
    ):
        message = f"Access denied: you are not the owner of {resource} '{resource_id}'"

        super().__init__(
            message=message,
            resource=resource,
            **kwargs,
        )

        self.with_context(
            resource_id=resource_id,
            owner_id=owner_id,
        )
        self.with_details(
            suggestion=(
                "Ownership verification solutions:\n"
                "1. Ensure you're accessing your own resources\n"
                "2. Check if you're logged in with the correct account\n"
                "3. Contact resource owner for access permission\n"
                "4. Request shared access if applicable"
            ),
        )


class TemporalPermissionException(PermissionException):
    """Raised when permission is time-restricted and not currently valid."""

    def __init__(
        self,
        permission: str,
        valid_from: Optional[str] = None,
        valid_until: Optional[str] = None,
        current_time: Optional[str] = None,
        **kwargs,
    ):
        message = f"Permission '{permission}' is not currently valid"
        if valid_from and valid_until:
            message += f" (valid from {valid_from} to {valid_until})"
        elif valid_from:
            message += f" (valid from {valid_from})"
        elif valid_until:
            message += f" (valid until {valid_until})"

        super().__init__(
            message=message,
            severity=ErrorSeverity.LOW,
            **kwargs,
        )

        self.with_context(
            permission=permission,
            valid_from=valid_from,
            valid_until=valid_until,
            current_time=current_time,
        )
        self.with_details(
            suggestion=(
                "Time-restricted permission solutions:\n"
                "1. Wait until permission becomes valid\n"
                "2. Contact administrator about time restrictions\n"
                "3. Check system clock for accuracy\n"
                "4. Request temporary access if needed"
            ),
        )


class ConditionalPermissionException(PermissionException):
    """Raised when permission is conditional and conditions are not met."""

    def __init__(
        self,
        permission: str,
        condition: str,
        condition_met: bool = False,
        **kwargs,
    ):
        message = f"Permission '{permission}' requires condition: {condition}"
        message += f" (condition met: {condition_met})"

        super().__init__(
            message=message,
            **kwargs,
        )

        self.with_context(
            permission=permission,
            condition=condition,
            condition_met=condition_met,
        )
        self.with_details(
            suggestion=(
                "Conditional permission solutions:\n"
                "1. Satisfy the required condition\n"
                "2. Check if additional verification is needed\n"
                "3. Review permission requirements\n"
                "4. Contact administrator for condition details"
            ),
        )


class HierarchicalPermissionException(PermissionException):
    """Raised when hierarchical permission checks fail."""

    def __init__(
        self,
        action: str,
        resource_hierarchy: List[str],
        max_allowed_level: Optional[int] = None,
        current_level: Optional[int] = None,
        **kwargs,
    ):
        message = f"Permission denied for hierarchical access to '{action}'"
        if current_level is not None and max_allowed_level is not None:
            message += f" (access level {current_level} exceeds allowed level {max_allowed_level})"

        super().__init__(
            message=message,
            action=action,
            **kwargs,
        )

        self.with_context(
            resource_hierarchy=resource_hierarchy,
            max_allowed_level=max_allowed_level,
            current_level=current_level,
        )
        self.with_details(
            suggestion=(
                "Hierarchical permission solutions:\n"
                "1. Check if you have access to parent resources\n"
                "2. Request higher level permissions\n"
                "3. Verify hierarchical structure is correct\n"
                "4. Consider using different access path"
            ),
        )


class PermissionRevocationException(PermissionException):
    """Raised when permission has been revoked."""

    def __init__(
        self,
        permission: str,
        revocation_reason: Optional[str] = None,
        revoked_at: Optional[str] = None,
        **kwargs,
    ):
        message = f"Permission '{permission}' has been revoked"
        if revocation_reason:
            message += f" ({revocation_reason})"
        if revoked_at:
            message += f" at {revoked_at}"

        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_context(
            permission=permission,
            revocation_reason=revocation_reason,
            revoked_at=revoked_at,
        )
        self.with_details(
            suggestion=(
                "Revoked permission solutions:\n"
                "1. Contact administrator about revocation\n"
                "2. Request re-granting of permission if needed\n"
                "3. Check if alternative permissions are available\n"
                "4. Review permission policies and guidelines"
            ),
        )
