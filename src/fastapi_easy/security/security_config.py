"""Unified security configuration"""

import logging
from typing import Optional

from .audit_log import AuditLogger
from .jwt_auth import JWTAuth
from .permission_loader import PermissionLoader
from .resource_checker import ResourcePermissionChecker

logger = logging.getLogger(__name__)


class SecurityConfig:
    """Unified security configuration for the security module"""

    def __init__(
        self,
        jwt_auth: JWTAuth,
        permission_loader: Optional[PermissionLoader] = None,
        resource_checker: Optional[ResourcePermissionChecker] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """Initialize security configuration

        Args:
            jwt_auth: JWT authentication handler
            permission_loader: Permission loader (optional)
            resource_checker: Resource permission checker (optional)
            audit_logger: Audit logger (optional)

        Raises:
            ValueError: If jwt_auth is None
            TypeError: If parameters have invalid types
        """
        if jwt_auth is None:
            raise ValueError("jwt_auth is required")

        if not isinstance(jwt_auth, JWTAuth):
            raise TypeError("jwt_auth must be a JWTAuth instance")

        self.jwt_auth = jwt_auth
        self.permission_loader = permission_loader
        self.resource_checker = resource_checker
        self.audit_logger = audit_logger or AuditLogger()

        logger.debug("SecurityConfig initialized")

    def validate(self) -> None:
        """Validate configuration

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.jwt_auth:
            raise ValueError("jwt_auth is required")

        logger.debug("SecurityConfig validation passed")

    @classmethod
    def from_env(
        cls,
        permission_loader: Optional[PermissionLoader] = None,
        resource_checker: Optional[ResourcePermissionChecker] = None,
        audit_logger: Optional[AuditLogger] = None,
    ) -> "SecurityConfig":
        """Create security configuration from environment variables

        Args:
            permission_loader: Permission loader (optional)
            resource_checker: Resource permission checker (optional)
            audit_logger: Audit logger (optional)

        Returns:
            SecurityConfig instance

        Raises:
            ValueError: If required environment variables are missing
        """
        jwt_auth = JWTAuth()  # Will read from environment variables
        config = cls(
            jwt_auth=jwt_auth,
            permission_loader=permission_loader,
            resource_checker=resource_checker,
            audit_logger=audit_logger,
        )
        config.validate()
        logger.info("SecurityConfig created from environment variables")
        return config

    def get_jwt_auth(self) -> JWTAuth:
        """Get JWT authentication handler

        Returns:
            JWTAuth instance
        """
        return self.jwt_auth

    def get_permission_loader(self) -> Optional[PermissionLoader]:
        """Get permission loader

        Returns:
            PermissionLoader instance or None
        """
        return self.permission_loader

    def get_resource_checker(self) -> Optional[ResourcePermissionChecker]:
        """Get resource permission checker

        Returns:
            ResourcePermissionChecker instance or None
        """
        return self.resource_checker

    def get_audit_logger(self) -> AuditLogger:
        """Get audit logger

        Returns:
            AuditLogger instance
        """
        return self.audit_logger

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"SecurityConfig("
            f"jwt_auth={self.jwt_auth.__class__.__name__}, "
            f"permission_loader={self.permission_loader.__class__.__name__ if self.permission_loader else None}, "
            f"resource_checker={self.resource_checker.__class__.__name__ if self.resource_checker else None}, "
            f"audit_logger={self.audit_logger.__class__.__name__}"
            f")"
        )
