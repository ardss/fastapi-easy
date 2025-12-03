"""Bulk operations support for FastAPI-Easy"""

from typing import Any, Dict, List, Optional, Type


class BulkOperationResult:
    """Result of a bulk operation"""

    def __init__(
        self,
        success_count: int = 0,
        failure_count: int = 0,
        errors: Optional[List[Dict[str, Any]]] = None,
    ):
        """Initialize bulk operation result

        Args:
            success_count: Number of successful operations
            failure_count: Number of failed operations
            errors: List of errors
        """
        self.success_count = success_count
        self.failure_count = failure_count
        self.errors = errors or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_count": self.success_count + self.failure_count,
            "errors": self.errors,
        }


class BulkOperationAdapter:
    """Adapter for bulk operations"""

    def __init__(self, model: Type, session_factory):
        """Initialize bulk operation adapter

        Args:
            model: SQLAlchemy model class
            session_factory: Async session factory
        """
        self.model = model
        self.session_factory = session_factory

    async def bulk_create(self, items: List[Dict[str, Any]]) -> BulkOperationResult:
        """Create multiple items

        Args:
            items: List of item data dictionaries

        Returns:
            BulkOperationResult with success/failure counts
        """
        result = BulkOperationResult()

        async with self.session_factory() as session:
            for idx, item_data in enumerate(items):
                try:
                    item = self.model(**item_data)
                    session.add(item)
                    result.success_count += 1
                except Exception as e:
                    result.failure_count += 1
                    result.errors.append(
                        {
                            "index": idx,
                            "error": str(e),
                        }
                    )

            try:
                await session.commit()
            except Exception as e:
                # 只增加失败计数，不覆盖之前的成功/失败计数
                failed_items = len(items) - result.success_count
                result.failure_count += failed_items
                result.errors.append(
                    {
                        "error": f"Commit failed: {str(e)}",
                        "type": "transaction_error",
                        "failed_count": failed_items,
                    }
                )
                await session.rollback()

        return result

    async def bulk_update(
        self,
        updates: List[Dict[str, Any]],
        id_field: str = "id",
    ) -> BulkOperationResult:
        """Update multiple items

        Args:
            updates: List of update dictionaries (must include id)
            id_field: Name of the ID field

        Returns:
            BulkOperationResult with success/failure counts
        """
        result = BulkOperationResult()

        async with self.session_factory() as session:
            for idx, update_data in enumerate(updates):
                try:
                    if id_field not in update_data:
                        raise ValueError(f"Missing {id_field} in update data")

                    item_id = update_data[id_field]
                    update_dict = {k: v for k, v in update_data.items() if k != id_field}

                    # Get the item
                    item = await session.get(self.model, item_id)
                    if item is None:
                        raise ValueError(f"Item with {id_field}={item_id} not found")

                    # Update fields
                    for key, value in update_dict.items():
                        if hasattr(item, key):
                            setattr(item, key, value)

                    result.success_count += 1
                except Exception as e:
                    result.failure_count += 1
                    result.errors.append(
                        {
                            "index": idx,
                            "error": str(e),
                        }
                    )

            try:
                await session.commit()
            except Exception as e:
                result.failure_count = len(updates)
                result.success_count = 0
                result.errors.append(
                    {
                        "error": f"Commit failed: {str(e)}",
                    }
                )
                await session.rollback()

        return result

    async def bulk_delete(
        self,
        ids: List[Any],
        id_field: str = "id",
    ) -> BulkOperationResult:
        """Delete multiple items

        Args:
            ids: List of item IDs to delete
            id_field: Name of the ID field

        Returns:
            BulkOperationResult with success/failure counts
        """
        result = BulkOperationResult()

        async with self.session_factory() as session:
            for idx, item_id in enumerate(ids):
                try:
                    item = await session.get(self.model, item_id)
                    if item is None:
                        raise ValueError(f"Item with {id_field}={item_id} not found")

                    await session.delete(item)
                    result.success_count += 1
                except Exception as e:
                    result.failure_count += 1
                    result.errors.append(
                        {
                            "index": idx,
                            "error": str(e),
                        }
                    )

            try:
                await session.commit()
            except Exception as e:
                result.failure_count = len(ids)
                result.success_count = 0
                result.errors.append(
                    {
                        "error": f"Commit failed: {str(e)}",
                    }
                )
                await session.rollback()

        return result


class BulkOperationConfig:
    """Configuration for bulk operations"""

    def __init__(
        self,
        enabled: bool = True,
        max_batch_size: int = 1000,
        transaction_mode: str = "all_or_nothing",  # or "partial"
    ):
        """Initialize bulk operation configuration

        Args:
            enabled: Enable bulk operations
            max_batch_size: Maximum items per bulk operation
            transaction_mode: "all_or_nothing" or "partial"
        """
        self.enabled = enabled
        self.max_batch_size = max_batch_size
        self.transaction_mode = transaction_mode
