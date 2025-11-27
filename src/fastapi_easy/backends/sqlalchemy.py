"""SQLAlchemy async ORM adapter"""

from typing import Any, Dict, List, Optional, Type
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .base import BaseORMAdapter
from ..core.errors import ConflictError, AppError, ErrorCode


class SQLAlchemyAdapter(BaseORMAdapter):
    """SQLAlchemy async ORM adapter
    
    Supports SQLAlchemy 2.0+ with async/await.
    """
    
    def __init__(
        self,
        model: Type[DeclarativeBase],
        session_factory,
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
        async with self.session_factory() as session:
            query = select(self.model)
            
            # Apply filters
            for filter_key, filter_value in filters.items():
                if isinstance(filter_value, dict):
                    field_name = filter_value.get("field")
                    operator = filter_value.get("operator", "exact")
                    value = filter_value.get("value")
                    
                    field = getattr(self.model, field_name, None)
                    if field is None:
                        continue
                    
                    if operator == "exact":
                        query = query.where(field == value)
                    elif operator == "ne":
                        query = query.where(field != value)
                    elif operator == "gt":
                        query = query.where(field > value)
                    elif operator == "gte":
                        query = query.where(field >= value)
                    elif operator == "lt":
                        query = query.where(field < value)
                    elif operator == "lte":
                        query = query.where(field <= value)
                    elif operator == "in":
                        values = value.split(",") if isinstance(value, str) else value
                        query = query.where(field.in_(values))
                    elif operator == "like":
                        query = query.where(field.like(value))
                    elif operator == "ilike":
                        query = query.where(field.ilike(value))
            
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
    
    async def get_one(self, id: Any) -> Optional[Any]:
        """Get single item by id
        
        Args:
            id: Item id
            
        Returns:
            Item or None
        """
        async with self.session_factory() as session:
            pk_field = getattr(self.model, self.pk_field)
            query = select(self.model).where(pk_field == id)
            result = await session.execute(query)
            return result.scalar_one_or_none()
    
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
                    message=f"Database error: {str(e)}"
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
                    message=f"Database error: {str(e)}"
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
                    message=f"Database error: {str(e)}"
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
                    message=f"Database error: {str(e)}"
                )
    
    async def count(self, filters: Dict[str, Any]) -> int:
        """Count items
        
        Args:
            filters: Filter conditions
            
        Returns:
            Total count
        """
        async with self.session_factory() as session:
            query = select(func.count()).select_from(self.model)
            
            # Apply filters
            for filter_key, filter_value in filters.items():
                if isinstance(filter_value, dict):
                    field_name = filter_value.get("field")
                    operator = filter_value.get("operator", "exact")
                    value = filter_value.get("value")
                    
                    field = getattr(self.model, field_name, None)
                    if field is None:
                        continue
                    
                    if operator == "exact":
                        query = query.where(field == value)
                    elif operator == "ne":
                        query = query.where(field != value)
                    elif operator == "gt":
                        query = query.where(field > value)
                    elif operator == "gte":
                        query = query.where(field >= value)
                    elif operator == "lt":
                        query = query.where(field < value)
                    elif operator == "lte":
                        query = query.where(field <= value)
                    elif operator == "in":
                        values = value.split(",") if isinstance(value, str) else value
                        query = query.where(field.in_(values))
                    elif operator == "like":
                        query = query.where(field.like(value))
                    elif operator == "ilike":
                        query = query.where(field.ilike(value))
            
            result = await session.execute(query)
            return result.scalar()
