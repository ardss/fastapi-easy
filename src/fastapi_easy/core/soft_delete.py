"""Soft delete support for FastAPI-Easy"""

from datetime import datetime
from typing import Any, Type
from sqlalchemy import Boolean, DateTime, Column
from sqlalchemy.orm import DeclarativeBase


class SoftDeleteMixin:
    """Soft delete mixin for SQLAlchemy models

    Adds soft delete functionality to models. Instead of permanently
    deleting records, they are marked as deleted with a timestamp.
    """

    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)

    def soft_delete(self) -> None:
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore a soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None

    def is_soft_deleted(self) -> bool:
        """Check if record is soft deleted"""
        return self.is_deleted


class SoftDeleteAdapter:
    """Adapter for handling soft deletes in ORM operations"""

    def __init__(self, model: Type[DeclarativeBase], include_deleted: bool = False):
        """Initialize soft delete adapter

        Args:
            model: SQLAlchemy model class
            include_deleted: Whether to include deleted records in queries
        """
        self.model = model
        self.include_deleted = include_deleted

    def get_query_filter(self) -> Any:
        """Get filter for excluding deleted records

        Returns:
            SQLAlchemy filter expression
        """
        if self.include_deleted:
            return None

        # Check if model has soft delete columns
        if hasattr(self.model, "is_deleted"):
            return self.model.is_deleted  is False

        return None

    def apply_soft_delete_filter(self, query: Any) -> Any:
        """Apply soft delete filter to query

        Args:
            query: SQLAlchemy query

        Returns:
            Filtered query
        """
        filter_expr = self.get_query_filter()
        if filter_expr is not None:
            query = query.where(filter_expr)
        return query

    async def soft_delete(self, item: Any) -> Any:
        """Soft delete an item

        Args:
            item: Item to soft delete

        Returns:
            Soft deleted item
        """
        if hasattr(item, "soft_delete"):
            item.soft_delete()
        return item

    async def restore(self, item: Any) -> Any:
        """Restore a soft-deleted item

        Args:
            item: Item to restore

        Returns:
            Restored item
        """
        if hasattr(item, "restore"):
            item.restore()
        return item

    async def permanently_delete(self, item: Any) -> Any:
        """Permanently delete an item (bypass soft delete)

        Args:
            item: Item to permanently delete

        Returns:
            Deleted item
        """
        # This would be handled by the ORM adapter
        return item


class SoftDeleteConfig:
    """Configuration for soft delete behavior"""

    def __init__(
        self,
        enabled: bool = True,
        include_deleted_by_default: bool = False,
        auto_restore_on_update: bool = False,
    ):
        """Initialize soft delete configuration

        Args:
            enabled: Enable soft delete globally
            include_deleted_by_default: Include deleted records in queries by default
            auto_restore_on_update: Automatically restore deleted records on update
        """
        self.enabled = enabled
        self.include_deleted_by_default = include_deleted_by_default
        self.auto_restore_on_update = auto_restore_on_update
