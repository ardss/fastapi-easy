"""
Migration exception hierarchy for FastAPI-Easy.

This module provides comprehensive exceptions for database migration
operations with detailed error information and recovery suggestions.
"""

from __future__ import annotations

from typing import List, Optional

from .base import (
    ErrorCategory,
    ErrorCode,
    ErrorSeverity,
    FastAPIEasyException,
)


class MigrationException(FastAPIEasyException):
    """Base exception for migration-related errors."""

    def __init__(
        self,
        message: str,
        migration_version: Optional[str] = None,
        migration_name: Optional[str] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_MIGRATION_ERROR,
            status_code=500,
            category=ErrorCategory.MIGRATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )

        self.with_context(
            migration_version=migration_version,
            migration_name=migration_name,
            database=database,
        )


class MigrationNotFoundException(MigrationException):
    """Raised when a specific migration cannot be found."""

    def __init__(
        self,
        migration_id: str,
        available_migrations: Optional[List[str]] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = f"Migration '{migration_id}' not found"
        if available_migrations:
            message += f". Available: {', '.join(available_migrations[:5])}"
            if len(available_migrations) > 5:
                message += f"... (and {len(available_migrations) - 5} more)"

        super().__init__(
            message=message,
            migration_version=migration_id,
            database=database,
            **kwargs,
        )

        self.with_context(
            migration_id=migration_id,
            available_migrations=available_migrations or [],
        )
        self.with_details(
            suggestion=(
                "Check the following:\n"
                "1. Migration ID is correct\n"
                "2. Migration file exists in the migrations directory\n"
                "3. Migration is properly registered in migration system"
            ),
            documentation_url="https://docs.fastapi-easy.com/migrations/finding-migrations",
        )


class MigrationExecutionException(MigrationException):
    """Raised when migration execution fails."""

    def __init__(
        self,
        migration_version: str,
        sql_error: Optional[str] = None,
        step: Optional[str] = None,
        **kwargs,
    ):
        message = f"Migration '{migration_version}' execution failed"
        if step:
            message += f" during step: {step}"
        if sql_error:
            # Sanitize SQL error to remove sensitive information
            sanitized_error = self._sanitize_sql_error(sql_error)
            message += f": {sanitized_error}"

        super().__init__(
            message=message,
            migration_version=migration_version,
            **kwargs,
        )

        self.with_context(step=step)
        self.with_details(
            constraint=step,
            debug_info={"sql_error": sanitized_error} if sql_error else None,
            suggestion=self._get_migration_suggestion(sql_error),
        )

    def _sanitize_sql_error(self, error: str) -> str:
        """Remove sensitive information from SQL errors."""
        import re

        # Remove password information
        error = re.sub(
            r"(password|pwd|passwd)\s*=\s*[^\s,;]+", r"\1=***", error, flags=re.IGNORECASE
        )

        # Remove host information
        error = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "***.***.***.***", error)

        # Remove database names that might be sensitive
        error = re.sub(r"(database|db)\s*=\s*[^\s,;]+", r"\1=***", error, flags=re.IGNORECASE)

        return error

    def _get_migration_suggestion(self, sql_error: Optional[str]) -> Optional[str]:
        """Get specific suggestion based on SQL error."""
        if not sql_error:
            return None

        error_lower = sql_error.lower()

        if "permission" in error_lower or "access denied" in error_lower:
            return (
                "Permission error solutions:\n"
                "1. Check database user permissions\n"
                "2. Ensure user has ALTER/CREATE/DROP privileges\n"
                "3. Verify database ownership"
            )
        elif "already exists" in error_lower:
            return (
                "Object already exists solutions:\n"
                "1. Check if migration was already applied\n"
                "2. Use 'if not exists' clauses where possible\n"
                "3. Consider manual state cleanup"
            )
        elif "does not exist" in error_lower or "unknown" in error_lower:
            return (
                "Object doesn't exist solutions:\n"
                "1. Verify migration dependencies\n"
                "2. Check migration order\n"
                "3. Ensure previous migrations ran successfully"
            )
        elif "constraint" in error_lower or "foreign key" in error_lower:
            return (
                "Constraint violation solutions:\n"
                "1. Check data integrity before migration\n"
                "2. Handle existing data that violates constraints\n"
                "3. Consider temporary constraint disabling"
            )
        elif "timeout" in error_lower:
            return (
                "Timeout solutions:\n"
                "1. Increase migration timeout settings\n"
                "2. Break large migrations into smaller steps\n"
                "3. Run during off-peak hours"
            )

        return (
            "General migration failure solutions:\n"
            "1. Check migration SQL syntax\n"
            "2. Verify database state before migration\n"
            "3. Review error logs for details\n"
            "4. Consider manual intervention if needed"
        )


class MigrationConflictException(MigrationException):
    """Raised when migration conflicts occur."""

    def __init__(
        self,
        migration_version: str,
        conflict_type: str,
        conflict_details: Optional[str] = None,
        **kwargs,
    ):
        message = f"Migration '{migration_version}' has {conflict_type} conflict"
        if conflict_details:
            message += f": {conflict_details}"

        super().__init__(
            message=message,
            migration_version=migration_version,
            **kwargs,
        )

        self.with_context(
            conflict_type=conflict_type,
            conflict_details=conflict_details,
        )
        self.with_details(
            suggestion=(
                "Conflict resolution options:\n"
                "1. Resolve conflicts in migration files\n"
                "2. Use migration merging strategies\n"
                "3. Create a new migration to resolve conflicts"
            ),
        )


class MigrationDependencyException(MigrationException):
    """Raised when migration dependencies are not satisfied."""

    def __init__(
        self,
        migration_version: str,
        missing_dependencies: List[str],
        **kwargs,
    ):
        message = f"Migration '{migration_version}' has unsatisfied dependencies"
        if missing_dependencies:
            message += f": {', '.join(missing_dependencies)}"

        super().__init__(
            message=message,
            migration_version=migration_version,
            **kwargs,
        )

        self.with_context(
            missing_dependencies=missing_dependencies,
            dependency_count=len(missing_dependencies),
        )
        self.with_details(
            suggestion=(
                "Dependency resolution:\n"
                "1. Run dependent migrations first\n"
                "2. Check migration dependency graph\n"
                "3. Ensure all prerequisites are applied\n"
                "4. Use 'migrate up' to auto-resolve dependencies"
            ),
        )


class MigrationRollbackException(MigrationException):
    """Raised when migration rollback fails."""

    def __init__(
        self,
        migration_version: str,
        rollback_reason: Optional[str] = None,
        **kwargs,
    ):
        message = f"Migration '{migration_version}' rollback failed"
        if rollback_reason:
            message += f": {rollback_reason}"

        super().__init__(
            message=message,
            migration_version=migration_version,
            **kwargs,
        )

        self.with_context(rollback_reason=rollback_reason)
        self.with_details(
            suggestion=(
                "Rollback failure solutions:\n"
                "1. Check rollback SQL for errors\n"
                "2. Manually verify database state\n"
                "3. Consider creating a manual fix migration\n"
                "4. Contact database administrator if needed"
            ),
        )


class MigrationValidationException(MigrationException):
    """Raised when migration validation fails."""

    def __init__(
        self,
        migration_version: str,
        validation_errors: List[str],
        validation_type: str = "schema",
        **kwargs,
    ):
        message = f"Migration '{migration_version}' validation failed ({validation_type})"

        super().__init__(
            message=message,
            migration_version=migration_version,
            **kwargs,
        )

        self.with_context(
            validation_type=validation_type,
            validation_errors=validation_errors,
        )
        self.with_details(
            debug_info={"validation_errors": validation_errors},
            suggestion=(
                "Validation failure solutions:\n"
                "1. Review and fix validation errors\n"
                "2. Ensure migration maintains data integrity\n"
                "3. Check that migration follows best practices\n"
                "4. Run validation in development environment first"
            ),
        )


class MigrationTimeoutException(MigrationException):
    """Raised when migration operation times out."""

    def __init__(
        self,
        migration_version: str,
        timeout_duration: int,
        operation: str = "execution",
        **kwargs,
    ):
        message = f"Migration '{migration_version}' {operation} timed out after {timeout_duration} seconds"

        super().__init__(
            message=message,
            migration_version=migration_version,
            **kwargs,
        )

        self.with_context(
            timeout_duration=timeout_duration,
            operation=operation,
        )
        self.with_details(
            suggestion=(
                "Timeout solutions:\n"
                "1. Increase migration timeout settings\n"
                "2. Break large migrations into smaller steps\n"
                "3. Run migrations during low-traffic periods\n"
                "4. Optimize migration SQL for performance"
            ),
        )


class MigrationLockException(MigrationException):
    """Raised when migration lock cannot be acquired."""

    def __init__(
        self,
        lock_holder: Optional[str] = None,
        lock_acquired_at: Optional[str] = None,
        **kwargs,
    ):
        message = "Cannot acquire migration lock"
        if lock_holder:
            message += f" (held by: {lock_holder})"
        if lock_acquired_at:
            message += f" (acquired at: {lock_acquired_at})"

        super().__init__(
            message=message,
            **kwargs,
        )

        self.with_context(
            lock_holder=lock_holder,
            lock_acquired_at=lock_acquired_at,
        )
        self.with_details(
            suggestion=(
                "Lock conflict solutions:\n"
                "1. Wait for the other migration to complete\n"
                "2. Check for stuck or failed migrations\n"
                "3. Force release the lock (use with caution)\n"
                "4. Ensure only one migration process runs at a time"
            ),
        )


class MigrationStateException(MigrationException):
    """Raised when migration system is in invalid state."""

    def __init__(
        self,
        state_issue: str,
        expected_state: Optional[str] = None,
        actual_state: Optional[str] = None,
        **kwargs,
    ):
        message = f"Migration system state error: {state_issue}"
        if expected_state and actual_state:
            message += f" (expected: {expected_state}, actual: {actual_state})"

        super().__init__(
            message=message,
            **kwargs,
        )

        self.with_context(
            state_issue=state_issue,
            expected_state=expected_state,
            actual_state=actual_state,
        )
        self.with_details(
            suggestion=(
                "State resolution:\n"
                "1. Check migration table integrity\n"
                "2. Verify migration history consistency\n"
                "3. Consider resetting migration state\n"
                "4. Rebuild migration table if necessary"
            ),
        )


class MigrationBackupException(MigrationException):
    """Raised when migration backup operations fail."""

    def __init__(
        self,
        backup_operation: str,
        backup_path: Optional[str] = None,
        error_detail: Optional[str] = None,
        **kwargs,
    ):
        message = f"Migration backup failed during {backup_operation}"
        if backup_path:
            message += f" at {backup_path}"
        if error_detail:
            message += f": {error_detail}"

        super().__init__(
            message=message,
            **kwargs,
        )

        self.with_context(
            backup_operation=backup_operation,
            backup_path=backup_path,
        )
        self.with_details(
            suggestion=(
                "Backup failure solutions:\n"
                "1. Check disk space and permissions\n"
                "2. Verify backup directory exists and is writable\n"
                "3. Check database backup permissions\n"
                "4. Consider manual backup before proceeding"
            ),
        )
