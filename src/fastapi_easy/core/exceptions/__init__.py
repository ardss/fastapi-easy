"""
FastAPI-Easy Exception System

This package provides a comprehensive error handling system for FastAPI-Easy applications.
It includes:

- Base exception classes with structured error information
- Error context management and tracking
- Consistent error response formatting
- Error severity levels and categories
- Error monitoring and recovery utilities

Main Components:
- FastAPIEasyException: Base exception class for all FastAPI-Easy errors
- DatabaseException: Hierarchy for database-related errors
- AuthenticationException: Hierarchy for authentication/authorization errors
- ValidationException: Hierarchy for validation errors
- MigrationException: Hierarchy for migration-related errors
- ConfigurationException: Hierarchy for configuration errors
- PermissionException: Hierarchy for permission errors
"""

from __future__ import annotations

from .authentication import (
    AccountExpiredException,
    AccountLockedException,
    AuthenticationException,
    AuthorizationException,
    CredentialsException,
    PermissionDeniedException,
    TokenException,
    TokenExpiredException,
    TokenInvalidException,
    TokenMissingException,
)
from .base import (
    ErrorCategory,
    ErrorCode,
    ErrorContext,
    ErrorDetails,
    ErrorSeverity,
    ErrorTracker,
    FastAPIEasyException,
)
from .configuration import (
    ConfigurationException,
    EnvironmentConfigurationException,
    InvalidConfigurationException,
    MissingConfigurationException,
    SecurityConfigurationException,
)

# Import all exception hierarchies
from .database import (
    DatabaseConnectionException,
    DatabaseConstraintException,
    DatabaseException,
    DatabaseMigrationException,
    DatabasePoolException,
    DatabaseQueryException,
    DatabaseTimeoutException,
    DatabaseTransactionException,
)
from .migration import (
    MigrationConflictException,
    MigrationDependencyException,
    MigrationException,
    MigrationExecutionException,
    MigrationNotFoundException,
    MigrationRollbackException,
    MigrationValidationException,
)
from .permission import (
    ActionPermissionException,
    PermissionException,
    ResourcePermissionException,
    RolePermissionException,
    ScopePermissionException,
)
from .validation import (
    BusinessRuleValidationException,
    FieldValidationException,
    FormatValidationException,
    RangeValidationException,
    RequiredFieldException,
    TypeValidationException,
    UniqueConstraintException,
    ValidationException,
)

# Legacy compatibility
NotFoundError = FastAPIEasyException

__all__ = [
    # Base classes and enums
    "FastAPIEasyException",
    "NotFoundError",  # Legacy compatibility
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
    "ErrorCode",
    "ErrorDetails",
    "ErrorTracker",
    # Database exceptions
    "DatabaseException",
    "DatabaseConnectionException",
    "DatabaseTimeoutException",
    "DatabaseConstraintException",
    "DatabaseQueryException",
    "DatabaseTransactionException",
    "DatabaseMigrationException",
    "DatabasePoolException",
    # Authentication exceptions
    "AuthenticationException",
    "AuthorizationException",
    "TokenException",
    "TokenExpiredException",
    "TokenInvalidException",
    "TokenMissingException",
    "CredentialsException",
    "PermissionDeniedException",
    "AccountLockedException",
    "AccountExpiredException",
    # Validation exceptions
    "ValidationException",
    "FieldValidationException",
    "TypeValidationException",
    "FormatValidationException",
    "RangeValidationException",
    "RequiredFieldException",
    "UniqueConstraintException",
    "BusinessRuleValidationException",
    # Migration exceptions
    "MigrationException",
    "MigrationNotFoundException",
    "MigrationExecutionException",
    "MigrationConflictException",
    "MigrationDependencyException",
    "MigrationRollbackException",
    "MigrationValidationException",
    # Configuration exceptions
    "ConfigurationException",
    "MissingConfigurationException",
    "InvalidConfigurationException",
    "EnvironmentConfigurationException",
    "SecurityConfigurationException",
    # Permission exceptions
    "PermissionException",
    "ResourcePermissionException",
    "ActionPermissionException",
    "RolePermissionException",
    "ScopePermissionException",
]
