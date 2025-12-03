"""Tortoise ORM adapter"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from tortoise import Model
from tortoise.exceptions import IntegrityError

from ..core.errors import AppError, ConflictError, ErrorCode
from .base import BaseORMAdapter


class TortoiseAdapter(BaseORMAdapter):
    """Tortoise ORM adapter

    Supports Tortoise ORM with async/await.
    """

    # Supported filter operators
    SUPPORTED_OPERATORS = {"exact", "ne", "gt", "gte", "lt", "lte", "in", "like", "ilike"}

    def __init__(
        self,
        model: Type[Model],
        session_factory: Optional[Callable] = None,
        pk_field: str = "id",
    ):
        """Initialize Tortoise adapter

        Args:
            model: Tortoise ORM model class
            session_factory: Not used for Tortoise (included for interface compatibility)
            pk_field: Primary key field name
        """
        super().__init__(model, session_factory)
        self.pk_field = pk_field

    def _apply_filters(self, query, filters: Dict[str, Any]) -> Tuple[Any, Dict[str, Any]]:
        """Apply filter conditions to query (DRY principle)

        Args:
            query: Tortoise query object
            filters: Filter conditions

        Returns:
            Tuple of (query, filter_kwargs)

        Raises:
            ValueError: If filter parameters are invalid
        """
        filter_kwargs = {}

        for filter_key, filter_value in filters.items():
            if not isinstance(filter_value, dict):
                continue

            # Validate and extract filter parameters
            field_name = filter_value.get("field")
            if not field_name or not isinstance(field_name, str):
                raise ValueError(f"Invalid field name: {field_name}")

            operator = filter_value.get("operator", "exact")
            if operator not in self.SUPPORTED_OPERATORS:
                raise ValueError(
                    f"Unsupported operator: {operator}. Supported: {self.SUPPORTED_OPERATORS}"
                )

            value = filter_value.get("value")
            if value is None:
                raise ValueError(f"Filter value cannot be None for field: {field_name}")

            # Apply filter using operator mapping
            if operator == "exact":
                filter_kwargs[field_name] = value
            elif operator == "ne":
                # Tortoise doesn't support != directly, use exclude
                query = query.exclude(**{field_name: value})
            elif operator == "gt":
                filter_kwargs[f"{field_name}__gt"] = value
            elif operator == "gte":
                filter_kwargs[f"{field_name}__gte"] = value
            elif operator == "lt":
                filter_kwargs[f"{field_name}__lt"] = value
            elif operator == "lte":
                filter_kwargs[f"{field_name}__lte"] = value
            elif operator == "in":
                values = value.split(",") if isinstance(value, str) else value
                filter_kwargs[f"{field_name}__in"] = values
            elif operator in ("like", "ilike"):
                # Tortoise uses icontains for case-insensitive contains
                filter_kwargs[f"{field_name}__icontains"] = value

        return query, filter_kwargs

    async def get_all(
        self,
        filters: Dict[str, Any],
        sorts: Dict[str, Any],
        pagination: Dict[str, Any],
    ) -> List[Any]:
        """Get all items with filtering, sorting, and pagination

        Args:
            filters: Filter conditions
            sorts: Sort conditions
            pagination: Pagination info (skip, limit)

        Returns:
            List of items
        """
        try:
            query = self.model.all()

            # Apply filters (using extracted method)
            query, filter_kwargs = self._apply_filters(query, filters)
            if filter_kwargs:
                query = query.filter(**filter_kwargs)

            # Apply sorting
            order_by = []
            for field_name, direction in sorts.items():
                if direction == "desc":
                    order_by.append(f"-{field_name}")
                else:
                    order_by.append(field_name)

            if order_by:
                query = query.order_by(*order_by)

            # Apply pagination
            skip = pagination.get("skip", 0)
            limit = pagination.get("limit", 10)
            query = query.offset(skip).limit(limit)

            return await query
        except ValueError as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                message=f"Database error (validation): {str(e)}",
            )
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {str(e)}"
            )

    async def get_one(self, id: Any) -> Optional[Any]:
        """Get single item by id

        Args:
            id: Item id

        Returns:
            Item or None
        """
        try:
            pk_field = self.pk_field
            return await self.model.get_or_none(**{pk_field: id})
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {str(e)}"
            )

    async def create(self, data: Dict[str, Any]) -> Any:
        """Create new item

        Args:
            data: Item data

        Returns:
            Created item

        Raises:
            ConflictError: If item already exists (unique constraint violation)
            AppError: For other database errors
        """
        try:
            item = await self.model.create(**data)
            return item
        except IntegrityError as e:
            raise ConflictError(f"Item already exists: {str(e)}")
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {str(e)}"
            )

    async def update(self, id: Any, data: Dict[str, Any]) -> Any:
        """Update item

        Args:
            id: Item id
            data: Updated data

        Returns:
            Updated item

        Raises:
            ConflictError: If unique constraint violation
            AppError: For other database errors
        """
        try:
            pk_field = self.pk_field
            item = await self.model.get_or_none(**{pk_field: id})

            if item is None:
                return None

            await item.update_from_dict(data)
            await item.save()
            return item
        except IntegrityError as e:
            raise ConflictError(f"Update conflict: {str(e)}")
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {str(e)}"
            )

    async def delete_one(self, id: Any) -> Any:
        """Delete single item

        Args:
            id: Item id

        Returns:
            Deleted item

        Raises:
            AppError: For database errors
        """
        try:
            pk_field = self.pk_field
            item = await self.model.get_or_none(**{pk_field: id})

            if item is None:
                return None

            await item.delete()
            return item
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {str(e)}"
            )

    async def delete_all(self) -> List[Any]:
        """Delete all items

        Returns:
            List of deleted items

        Raises:
            AppError: For database errors
        """
        try:
            # Get all items first
            items = await self.model.all()

            # Delete all
            await self.model.all().delete()

            return items
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {str(e)}"
            )

    async def count(self, filters: Dict[str, Any]) -> int:
        """Count items

        Args:
            filters: Filter conditions

        Returns:
            Total count
        """
        try:
            query = self.model.all()

            # Apply filters (using extracted method - DRY!)
            query, filter_kwargs = self._apply_filters(query, filters)
            if filter_kwargs:
                query = query.filter(**filter_kwargs)

            return await query.count()
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {str(e)}"
            )
