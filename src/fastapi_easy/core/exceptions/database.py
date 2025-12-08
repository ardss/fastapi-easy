"""
Database exception hierarchy for FastAPI-Easy.

This module provides a comprehensive set of database-related exceptions
with specific error codes, suggestions, and context.
"""

from __future__ import annotations

from typing import Any, Optional

from .base import (
    ErrorCategory,
    ErrorCode,
    ErrorSeverity,
    FastAPIEasyException,
)


class DatabaseException(FastAPIEasyException):
    """Base exception for all database-related errors."""

    def __init__(
        self,
        message: str,
        database: Optional[str] = None,
        table: Optional[str] = None,
        query: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            status_code=500,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )

        # Add database-specific context
        if database:
            self.with_context(database=database)
        if table:
            self.with_context(table=table)
        if query:
            self.with_context(query=query[:200] + "..." if len(query) > 200 else query)


class DatabaseConnectionException(DatabaseException):
    """Raised when database connection fails."""

    def __init__(
        self,
        database: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        original_error: Optional[Exception] = None,
        **kwargs,
    ):
        message = f"Failed to connect to database '{database}'"
        if host and port:
            message += f" at {host}:{port}"

        super().__init__(
            message=message,
            database=database,
            code=ErrorCode.DATABASE_CONNECTION_ERROR,
            status_code=503,  # Service Unavailable
            severity=ErrorSeverity.CRITICAL,
            cause=original_error,
            **kwargs,
        )

        self.with_details(
            suggestion=(
                "Check the following:\n"
                "1. Database server is running\n"
                "2. Connection string is correct\n"
                "3. Network connectivity\n"
                "4. Firewall settings\n"
                "5. Database credentials"
            ),
            documentation_url="https://docs.fastapi-easy.com/database/troubleshooting#connection-issues",
        )


class DatabaseTimeoutException(DatabaseException):
    """Raised when database operation times out."""

    def __init__(
        self,
        operation: str,
        timeout: Optional[int] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = f"Database operation '{operation}' timed out"
        if timeout:
            message += f" after {timeout} seconds"

        super().__init__(
            message=message,
            database=database,
            code=ErrorCode.DATABASE_TIMEOUT,
            status_code=504,  # Gateway Timeout
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )

        self.with_details(
            field="timeout",
            value=timeout,
            suggestion=(
                "Try the following:\n"
                "1. Optimize the query with indexes\n"
                "2. Increase timeout settings\n"
                "3. Use pagination for large datasets\n"
                "4. Consider database query optimization"
            ),
        )


class DatabaseConstraintException(DatabaseException):
    """Raised when database constraint is violated."""

    def __init__(
        self,
        constraint: str,
        table: Optional[str] = None,
        field: Optional[str] = None,
        value: Any = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = f"Database constraint '{constraint}' violated"
        if table and field:
            message += f" for field '{field}' in table '{table}'"

        super().__init__(
            message=message,
            database=database,
            table=table,
            code=ErrorCode.DATABASE_CONSTRAINT_ERROR,
            status_code=422,  # Unprocessable Entity
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_details(
            field=field,
            value=value,
            constraint=constraint,
            suggestion=(
                "Check the following:\n"
                "1. Value meets constraint requirements\n"
                "2. Unique constraint - ensure value is unique\n"
                "3. Foreign key constraint - ensure referenced record exists\n"
                "4. Check constraint - ensure value meets validation rules"
            ),
        )


class DatabaseQueryException(DatabaseException):
    """Raised when database query fails due to syntax or logic errors."""

    def __init__(
        self,
        query: str,
        error_detail: Optional[str] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = "Database query execution failed"
        if error_detail:
            message += f": {error_detail}"

        super().__init__(
            message=message,
            database=database,
            query=query,
            code=ErrorCode.DATABASE_QUERY_ERROR,
            status_code=400,  # Bad Request
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_details(
            suggestion=(
                "Check the following:\n"
                "1. SQL syntax is correct\n"
                "2. Table and column names exist\n"
                "3. Query parameters match expected types\n"
                "4. Database schema is up to date"
            ),
        )


class DatabaseTransactionException(DatabaseException):
    """Raised when database transaction fails."""

    def __init__(
        self,
        transaction_id: Optional[str] = None,
        operation: Optional[str] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = "Database transaction failed"
        if operation:
            message += f" during {operation}"
        if transaction_id:
            message += f" (ID: {transaction_id})"

        super().__init__(
            message=message,
            database=database,
            code=ErrorCode.DATABASE_TRANSACTION_ERROR,
            status_code=500,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )

        self.with_context(transaction_id=transaction_id, operation=operation)
        self.with_details(
            suggestion=(
                "Try the following:\n"
                "1. Rollback and retry the transaction\n"
                "2. Check for deadlocks or lock contention\n"
                "3. Ensure sufficient database resources\n"
                "4. Verify transaction isolation level"
            ),
        )


class DatabaseMigrationException(DatabaseException):
    """Raised when database migration fails."""

    def __init__(
        self,
        migration_version: str,
        migration_name: Optional[str] = None,
        error_detail: Optional[str] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = f"Database migration {migration_version} failed"
        if migration_name:
            message += f" ({migration_name})"
        if error_detail:
            message += f": {error_detail}"

        super().__init__(
            message=message,
            database=database,
            code=ErrorCode.DATABASE_MIGRATION_ERROR,
            status_code=500,
            severity=ErrorSeverity.CRITICAL,
            **kwargs,
        )

        self.with_context(migration_version=migration_version, migration_name=migration_name)
        self.with_details(
            suggestion=(
                "Try the following:\n"
                "1. Check migration SQL syntax\n"
                "2. Verify database permissions\n"
                "3. Ensure schema state is compatible\n"
                "4. Review migration dependencies\n"
                "5. Consider manual rollback if needed"
            ),
            documentation_url="https://docs.fastapi-easy.com/migrations/troubleshooting",
        )


class DatabasePoolException(DatabaseException):
    """Raised when database connection pool issues occur."""

    def __init__(
        self,
        pool_type: str,
        issue: str,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = f"Database connection pool issue: {issue}"

        super().__init__(
            message=message,
            database=database,
            code=ErrorCode.DATABASE_POOL_ERROR,
            status_code=503,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )

        self.with_context(pool_type=pool_type)
        self.with_details(
            suggestion=(
                "Try the following:\n"
                "1. Increase pool size\n"
                "2. Configure proper pool timeout\n"
                "3. Implement connection retry logic\n"
                "4. Monitor connection usage\n"
                "5. Check for connection leaks"
            ),
        )


class DatabaseDeadlockException(DatabaseTransactionException):
    """Raised when database deadlock occurs."""

    def __init__(
        self,
        transaction_id: Optional[str] = None,
        resources: Optional[list] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = "Database deadlock detected"
        if resources:
            message += f" on resources: {', '.join(str(r) for r in resources)}"

        super().__init__(
            transaction_id=transaction_id,
            operation="deadlock_detection",
            database=database,
            **kwargs,
        )

        self.message = message
        self.with_context(resources=resources)
        self.with_details(
            suggestion=(
                "Try the following:\n"
                "1. Retry the transaction after a delay\n"
                "2. Acquire locks in consistent order\n"
                "3. Keep transactions short\n"
                "4. Use lower isolation level if appropriate\n"
                "5. Implement retry with exponential backoff"
            ),
        )


class DatabaseLockException(DatabaseException):
    """Raised when database lock cannot be acquired."""

    def __init__(
        self,
        lock_type: str,
        resource: str,
        timeout: Optional[int] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = f"Failed to acquire {lock_type} lock on resource '{resource}'"
        if timeout:
            message += f" within {timeout} seconds"

        super().__init__(
            message=message,
            database=database,
            code=ErrorCode.DATABASE_TIMEOUT,  # Reuse timeout code
            status_code=409,  # Conflict
            severity=ErrorSeverity.MEDIUM,
            **kwargs,
        )

        self.with_context(lock_type=lock_type, resource=resource, timeout=timeout)
        self.with_details(
            suggestion=(
                "Try the following:\n"
                "1. Wait and retry the operation\n"
                "2. Check for long-running transactions\n"
                "3. Use shorter lock timeout\n"
                "4. Implement retry with exponential backoff"
            ),
        )


class DatabaseIntegrityException(DatabaseException):
    """Raised when data integrity is compromised."""

    def __init__(
        self,
        integrity_issue: str,
        table: Optional[str] = None,
        record_id: Optional[Any] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        message = f"Data integrity issue: {integrity_issue}"
        if table and record_id:
            message += f" in table '{table}' for record {record_id}"

        super().__init__(
            message=message,
            database=database,
            table=table,
            code=ErrorCode.DATABASE_CONSTRAINT_ERROR,  # Reuse constraint error code
            status_code=422,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )

        self.with_context(record_id=record_id)
        self.with_details(
            suggestion=(
                "Try the following:\n"
                "1. Verify data consistency\n"
                "2. Check for orphaned records\n"
                "3. Validate foreign key relationships\n"
                "4. Run data integrity checks"
            ),
        )
