"""SQLAlchemy async ORM adapter with enhanced security"""

import logging
from typing import Any, Callable, Dict, List, Optional, Type

from sqlalchemy import delete, func, select, text, and_, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase

from ..core.errors import AppError, ConflictError, ErrorCode
from ..security.validation.input_validator import SecurityValidator
from .base import BaseORMAdapter

logger = logging.getLogger(__name__)


class SQLAlchemyAdapter(BaseORMAdapter):
    """SQLAlchemy async ORM adapter

    Supports SQLAlchemy 2.0+ with async/await.
    """

    # Supported filter operators
    SUPPORTED_OPERATORS = {"exact", "ne", "gt", "gte", "lt", "lte", "in", "like", "ilike"}

    def __init__(
        self,
        model: Type[DeclarativeBase],
        session_factory: Callable,
        pk_field: str = "id",
    ):
        """Initialize SQLAlchemy adapter

        Args:
            model: SQLAlchemy ORM model class
            session_factory: Async session factory
            pk_field: Primary key field name
        """
        super().__init__(model, session_factory)
        self.pk_field = pk_field

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filter conditions to query with security validation (DRY principle)

        Args:
            query: SQLAlchemy query object
            filters: Filter conditions

        Returns:
            Query with filters applied

        Raises:
            ValueError: If filter parameters are invalid
        """
        for filter_key, filter_value in filters.items():
            if not isinstance(filter_value, dict):
                continue

            # Validate and extract filter parameters
            field_name = filter_value.get("field")
            if not field_name or not isinstance(field_name, str):
                raise ValueError(f"Invalid field name: {field_name}")

            # Security: Validate field name to prevent injection
            try:
                field_name = SecurityValidator.validate_field_name(field_name)
            except Exception as e:
                logger.warning(f"Invalid field name in filter: {field_name}")
                raise ValueError(f"Invalid field name: {field_name}")

            operator = filter_value.get("operator", "exact")
            if operator not in self.SUPPORTED_OPERATORS:
                raise ValueError(
                    f"Unsupported operator: {operator}. Supported: {self.SUPPORTED_OPERATORS}"
                )

            value = filter_value.get("value")
            if value is None:
                raise ValueError(f"Filter value cannot be None for field: {field_name}")

            # Security: Validate filter value
            try:
                value = SecurityValidator.validate_sql_value(value)
            except Exception as e:
                logger.warning(
                    f"Suspicious filter value detected for field {field_name}: {str(e)[:100]}"
                )
                raise ValueError(f"Invalid filter value for field: {field_name}")

            # Get model field (safe as field_name is validated)
            field = getattr(self.model, field_name, None)
            if field is None:
                raise ValueError(f"Field not found on model: {field_name}")

            # Apply filter using operator mapping with additional safety
            operator_map = {
                "exact": lambda f, v: f == v,
                "ne": lambda f, v: f != v,
                "gt": lambda f, v: f > v,
                "gte": lambda f, v: f >= v,
                "lt": lambda f, v: f < v,
                "lte": lambda f, v: f <= v,
                "in": lambda f, v: f.in_(v.split(",") if isinstance(v, str) else v),
                "like": lambda f, v: f.like(f"%{v}%"),  # Automatically add wildcards for safety
                "ilike": lambda f, v: f.ilike(f"%{v}%"),  # Automatically add wildcards for safety
            }

            if operator in operator_map:
                # Additional validation for LIKE operators to prevent pattern injection
                if operator in ["like", "ilike"] and isinstance(value, str):
                    # Escape special SQL wildcard characters
                    value = value.replace("%", "\\%").replace("_", "\\_")

                query = query.where(operator_map[operator](field, value))

        return query

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
            async with self.session_factory() as session:
                query = select(self.model)

                # Apply filters (using extracted method)
                query = self._apply_filters(query, filters)

                # Apply sorting
                for field_name, direction in sorts.items():
                    field = getattr(self.model, field_name, None)
                    if field is None:
                        continue

                    if direction == "desc":
                        query = query.order_by(field.desc())
                    else:
                        query = query.order_by(field.asc())

                # Apply pagination
                skip = pagination.get("skip", 0)
                limit = pagination.get("limit", 10)
                query = query.offset(skip).limit(limit)

                result = await session.execute(query)
                return result.scalars().all()
        except ValueError as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                message=f"Database error (validation): {str(e)}",
            )
        except SQLAlchemyError as e:
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
        async with self.session_factory() as session:
            try:
                pk_field = getattr(self.model, self.pk_field)
                query = select(self.model).where(pk_field == id)
                result = await session.execute(query)
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                raise AppError(
                    code=ErrorCode.INTERNAL_ERROR,
                    status_code=500,
                    message=f"Database error: {str(e)}",
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
        async with self.session_factory() as session:
            try:
                item = self.model(**data)
                session.add(item)
                await session.commit()
                await session.refresh(item)
                return item
            except IntegrityError as e:
                await session.rollback()
                raise ConflictError(f"Item already exists: {str(e)}")
            except SQLAlchemyError as e:
                await session.rollback()
                raise AppError(
                    code=ErrorCode.INTERNAL_ERROR,
                    status_code=500,
                    message=f"Database error: {str(e)}",
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
        async with self.session_factory() as session:
            try:
                pk_field = getattr(self.model, self.pk_field)
                query = select(self.model).where(pk_field == id)
                result = await session.execute(query)
                item = result.scalar_one_or_none()

                if item is None:
                    return None

                for key, value in data.items():
                    setattr(item, key, value)

                await session.commit()
                await session.refresh(item)
                return item
            except IntegrityError as e:
                await session.rollback()
                raise ConflictError(f"Update conflict: {str(e)}")
            except SQLAlchemyError as e:
                await session.rollback()
                raise AppError(
                    code=ErrorCode.INTERNAL_ERROR,
                    status_code=500,
                    message=f"Database error: {str(e)}",
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
        async with self.session_factory() as session:
            try:
                pk_field = getattr(self.model, self.pk_field)
                query = select(self.model).where(pk_field == id)
                result = await session.execute(query)
                item = result.scalar_one_or_none()

                if item is None:
                    return None

                await session.delete(item)
                await session.commit()
                return item
            except SQLAlchemyError as e:
                await session.rollback()
                raise AppError(
                    code=ErrorCode.INTERNAL_ERROR,
                    status_code=500,
                    message=f"Database error: {str(e)}",
                )

    async def delete_all(self) -> List[Any]:
        """Delete all items

        Returns:
            List of deleted items

        Raises:
            AppError: For database errors
        """
        async with self.session_factory() as session:
            try:
                # Get all items first
                query = select(self.model)
                result = await session.execute(query)
                items = result.scalars().all()

                # Delete all
                delete_query = delete(self.model)
                await session.execute(delete_query)
                await session.commit()

                return items
            except SQLAlchemyError as e:
                await session.rollback()
                raise AppError(
                    code=ErrorCode.INTERNAL_ERROR,
                    status_code=500,
                    message=f"Database error: {str(e)}",
                )

    async def count(self, filters: Dict[str, Any]) -> int:
        """Count items

        Args:
            filters: Filter conditions

        Returns:
            Total count
        """
        try:
            async with self.session_factory() as session:
                query = select(func.count()).select_from(self.model)

                # Apply filters (using extracted method - DRY!)
                query = self._apply_filters(query, filters)

                result = await session.execute(query)
                return result.scalar()
        except ValueError as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {str(e)}"
            )
        except SQLAlchemyError as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR, status_code=500, message=f"Database error: {str(e)}"
            )
