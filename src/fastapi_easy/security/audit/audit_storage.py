"""Audit log storage interface and implementations"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Protocol

logger = logging.getLogger(__name__)


class AuditStorage(Protocol):
    """Protocol for audit log storage"""

    async def save(self, log: Dict[str, Any]) -> None:
        """Save audit log

        Args:
            log: Audit log entry

        Raises:
            Exception: If save fails
        """
        ...

    async def query(self, **filters: Any) -> List[Dict[str, Any]]:
        """Query audit logs

        Args:
            **filters: Query filters

        Returns:
            List of matching audit logs

        Raises:
            Exception: If query fails
        """
        ...

    async def delete(self, **filters: Any) -> int:
        """Delete audit logs

        Args:
            **filters: Delete filters

        Returns:
            Number of deleted logs

        Raises:
            Exception: If delete fails
        """
        ...


class MemoryAuditStorage:
    """In-memory audit log storage"""

    def __init__(self, max_logs: int = 10000):
        """Initialize memory storage

        Args:
            max_logs: Maximum number of logs to keep
        """
        if not isinstance(max_logs, int) or max_logs <= 0:
            raise ValueError("max_logs must be a positive integer")

        self.logs: List[Dict[str, Any]] = []
        self.max_logs = max_logs

        logger.debug(f"MemoryAuditStorage initialized with max_logs={max_logs}")

    async def save(self, log: Dict[str, Any]) -> None:
        """Save audit log to memory

        Args:
            log: Audit log entry

        Raises:
            TypeError: If log is not a dict
        """
        if not isinstance(log, dict):
            raise TypeError("log must be a dict")

        self.logs.append(log)

        # Remove oldest log if exceeds max
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)

        logger.debug(f"Saved audit log, total: {len(self.logs)}")

    async def query(self, **filters: Any) -> List[Dict[str, Any]]:
        """Query audit logs from memory

        Args:
            **filters: Query filters (e.g., user_id="user1")

        Returns:
            List of matching audit logs
        """
        if not filters:
            return self.logs.copy()

        result = []
        for log in self.logs:
            match = True
            for key, value in filters.items():
                if log.get(key) != value:
                    match = False
                    break
            if match:
                result.append(log)

        logger.debug(f"Queried {len(result)} logs with filters: {filters}")
        return result

    async def delete(self, **filters: Any) -> int:
        """Delete audit logs from memory

        Args:
            **filters: Delete filters

        Returns:
            Number of deleted logs
        """
        if not filters:
            count = len(self.logs)
            self.logs.clear()
            logger.debug(f"Deleted all {count} logs")
            return count

        original_count = len(self.logs)
        self.logs = [
            log
            for log in self.logs
            if not all(log.get(key) == value for key, value in filters.items())
        ]
        deleted_count = original_count - len(self.logs)

        logger.debug(f"Deleted {deleted_count} logs with filters: {filters}")
        return deleted_count

    def clear(self) -> None:
        """Clear all logs"""
        self.logs.clear()
        logger.debug("Cleared all logs")

    def get_count(self) -> int:
        """Get total number of logs

        Returns:
            Total number of logs
        """
        return len(self.logs)


class DatabaseAuditStorage:
    """Database audit log storage (placeholder)"""

    def __init__(self, db_session=None):
        """Initialize database storage

        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session
        logger.debug("DatabaseAuditStorage initialized")

    async def save(self, log: Dict[str, Any]) -> None:
        """Save audit log to database

        Args:
            log: Audit log entry
        """
        if not isinstance(log, dict):
            raise TypeError("log must be a dict")

        # Placeholder: In real implementation, save to database
        logger.debug(f"Saved audit log to database: {log}")

    async def query(self, **filters: Any) -> List[Dict[str, Any]]:
        """Query audit logs from database

        Args:
            **filters: Query filters

        Returns:
            List of matching audit logs
        """
        # Placeholder: In real implementation, query database
        logger.debug(f"Queried logs from database with filters: {filters}")
        return []

    async def delete(self, **filters: Any) -> int:
        """Delete audit logs from database

        Args:
            **filters: Delete filters

        Returns:
            Number of deleted logs
        """
        # Placeholder: In real implementation, delete from database
        logger.debug(f"Deleted logs from database with filters: {filters}")
        return 0
