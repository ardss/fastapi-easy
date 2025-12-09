"""
Common Mixins for FastAPI-Easy

Reusable mixins to eliminate code duplication and promote DRY principles:
- Timestamp management
- Soft delete functionality
- Audit trail
- Validation mixins
- Serialization mixins
- Cache management
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field, validator
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)


class TimestampMixin:
    """Mixin to add timestamp fields to models"""

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        comment="Creation timestamp",
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        comment="Last update timestamp",
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """Auto-generate table name from class name"""
        return cls.__name__.lower()


class SoftDeleteMixin:
    """Mixin to add soft delete functionality"""

    deleted_at = Column(
        DateTime(timezone=True), nullable=True, comment="Deletion timestamp (null if not deleted)"
    )
    is_deleted = Column(
        Boolean, default=False, nullable=False, index=True, comment="Soft delete flag"
    )

    def soft_delete(self) -> None:
        """Mark record as deleted"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self) -> None:
        """Restore soft-deleted record"""
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin:
    """Mixin to add audit trail functionality"""

    created_by = Column(String(255), nullable=True, comment="User who created the record")
    updated_by = Column(String(255), nullable=True, comment="User who last updated the record")
    version = Column(
        Integer, default=1, nullable=False, comment="Version number for optimistic locking"
    )

    def increment_version(self) -> None:
        """Increment version number"""
        self.version += 1


class MetadataMixin:
    """Mixin to add metadata storage"""

    metadata = Column(JSON, nullable=True, default=dict, comment="Additional metadata as JSON")

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value"""
        if self.metadata is None:
            return default
        return self.metadata.get(key, default)

    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value"""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value

    def update_metadata(self, data: Dict[str, Any]) -> None:
        """Update multiple metadata values"""
        if self.metadata is None:
            self.metadata = {}
        self.metadata.update(data)


class UUIDMixin:
    """Mixin to add UUID primary key"""

    @declared_attr
    def id(cls) -> Column:
        return Column(
            String(36),
            primary_key=True,
            default=lambda: str(uuid.uuid4()),
            comment="UUID primary key",
        )


class SlugMixin:
    """Mixin to add slug field with auto-generation"""

    slug = Column(String(255), nullable=True, unique=True, index=True, comment="URL-friendly slug")

    def generate_slug(self, source_fields: List[str]) -> str:
        """Generate slug from specified fields"""
        import re
        from urllib.parse import quote

        # Get values from source fields
        values = []
        for field in source_fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if value:
                    values.append(str(value))

        # Join and clean
        text = " ".join(values).lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        text = text.strip("-_")

        return quote(text)

    def ensure_slug(self, source_fields: List[str]) -> None:
        """Ensure slug exists, generate if needed"""
        if not self.slug:
            self.slug = self.generate_slug(source_fields)


# Base model class with common mixins
class BaseModelMixin(TimestampMixin, SoftDeleteMixin, AuditMixin, MetadataMixin):
    """Base model with common mixins applied"""

    __abstract__ = True


# Validation mixins for Pydantic models
class ValidationMixin:
    """Common validation methods for Pydantic models"""

    @validator("*", pre=True)
    def empty_string_to_none(cls, v):
        """Convert empty strings to None"""
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @classmethod
    def get_optional_fields(cls) -> List[str]:
        """Get list of optional fields"""
        optional_fields = []
        for name, field in cls.model_fields.items():
            if not field.is_required():
                optional_fields.append(name)
        return optional_fields


class PaginationMixin(BaseModel):
    """Mixin for pagination parameters"""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(50, ge=1, le=1000, description="Items per page")

    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit (page_size)"""
        return self.page_size


class FilterMixin:
    """Mixin for filter handling"""

    @classmethod
    def parse_filters(cls, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate filters"""
        parsed = {}
        for key, value in filters.items():
            if value is not None:
                parsed[key] = value
        return parsed

    @classmethod
    def build_filter_expression(cls, model: Type[T], filters: Dict[str, Any]):
        """Build SQLAlchemy filter expression"""
        from sqlalchemy import and_

        conditions = []
        for field, value in filters.items():
            if hasattr(model, field):
                model_field = getattr(model, field)

                if isinstance(value, dict):
                    # Handle complex filters
                    for operator, val in value.items():
                        if operator == "gt":
                            conditions.append(model_field > val)
                        elif operator == "gte":
                            conditions.append(model_field >= val)
                        elif operator == "lt":
                            conditions.append(model_field < val)
                        elif operator == "lte":
                            conditions.append(model_field <= val)
                        elif operator == "ne":
                            conditions.append(model_field != val)
                        elif operator == "in":
                            conditions.append(model_field.in_(val))
                        elif operator == "nin":
                            conditions.append(model_field.notin_(val))
                        elif operator == "like":
                            conditions.append(model_field.like(val))
                        elif operator == "ilike":
                            conditions.append(model_field.ilike(val))
                else:
                    # Simple equality
                    conditions.append(model_field == value)

        return and_(*conditions) if conditions else None


class SortMixin:
    """Mixin for sorting functionality"""

    @classmethod
    def parse_sorts(cls, sorts: Dict[str, str]) -> List[tuple]:
        """Parse sort parameters into list of (field, direction)"""
        parsed = []
        for field, direction in sorts.items():
            if direction.lower() in ["asc", "desc"]:
                parsed.append((field, direction.lower()))
        return parsed

    @classmethod
    def build_sort_expression(cls, model: Type[T], sorts: List[tuple]):
        """Build SQLAlchemy order by expression"""
        from sqlalchemy import asc, desc

        expressions = []
        for field, direction in sorts:
            if hasattr(model, field):
                model_field = getattr(model, field)
                if direction == "desc":
                    expressions.append(desc(model_field))
                else:
                    expressions.append(asc(model_field))

        return expressions


class ResponseMixin:
    """Mixin for standardized API responses"""

    @classmethod
    def success_response(
        cls, data: Any, message: str = "Operation successful", meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create standardized success response"""
        response = {"success": True, "message": message, "data": data}
        if meta:
            response["meta"] = meta
        return response

    @classmethod
    def error_response(
        cls, message: str, code: str = "ERROR", details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create standardized error response"""
        response = {"success": False, "message": message, "code": code}
        if details:
            response["details"] = details
        return response

    @classmethod
    def paginated_response(
        cls,
        items: List[Any],
        total: int,
        page: int,
        page_size: int,
        message: str = "Items retrieved successfully",
    ) -> Dict[str, Any]:
        """Create paginated response"""
        total_pages = (total + page_size - 1) // page_size

        return cls.success_response(
            data=items,
            message=message,
            meta={
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                }
            },
        )


class CacheMixin:
    """Mixin for caching functionality"""

    def get_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key with prefix and parameters"""
        import hashlib

        key_data = f"{prefix}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    async def get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get value from cache (to be implemented)"""
        # Implementation depends on cache backend
        pass

    async def set_cache(self, cache_key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache (to be implemented)"""
        # Implementation depends on cache backend
        pass

    async def invalidate_cache_pattern(self, pattern: str) -> None:
        """Invalidate cache keys matching pattern (to be implemented)"""
        # Implementation depends on cache backend
        pass


class BatchOperationMixin:
    """Mixin for batch operations"""

    async def batch_create(
        self, items: List[Dict[str, Any]], batch_size: int = 1000, continue_on_error: bool = False
    ) -> Dict[str, Any]:
        """Create items in batches"""
        created = []
        errors = []

        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            try:
                # Process batch
                for item_data in batch:
                    try:
                        item = await self.create(item_data)
                        created.append(item)
                    except Exception as e:
                        error = {"index": i + len(created) + len(errors), "error": str(e)}
                        errors.append(error)

                        if not continue_on_error:
                            raise

            except Exception as e:
                if not continue_on_error:
                    errors.append({"batch": i // batch_size, "error": str(e)})
                    raise

        return {
            "created": created,
            "errors": errors,
            "total_created": len(created),
            "total_errors": len(errors),
        }

    async def batch_update(
        self, updates: List[Dict[str, Any]], batch_size: int = 1000, continue_on_error: bool = False
    ) -> Dict[str, Any]:
        """Update items in batches"""
        updated = []
        errors = []

        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]

            try:
                for update_data in batch:
                    try:
                        item_id = update_data.get("id")
                        if not item_id:
                            raise ValueError("Missing 'id' field")

                        data = update_data.get("data", {})
                        item = await self.update(item_id, data)
                        updated.append(item)

                    except Exception as e:
                        error = {"index": i + len(updated) + len(errors), "error": str(e)}
                        errors.append(error)

                        if not continue_on_error:
                            raise

            except Exception as e:
                if not continue_on_error:
                    errors.append({"batch": i // batch_size, "error": str(e)})
                    raise

        return {
            "updated": updated,
            "errors": errors,
            "total_updated": len(updated),
            "total_errors": len(errors),
        }


# Decorator mixins for common functionality
def cache_result(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = (
                f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            )

            # Try to get from cache
            cached_result = await wrapper._get_cache(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await wrapper._set_cache(cache_key, result, ttl)

            return result

        # Cache storage (to be set by class)
        wrapper._get_cache = lambda key: None
        wrapper._set_cache = lambda key, value, ttl: None

        return wrapper

    return decorator


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to retry function on failure"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(delay * (2**attempt))  # Exponential backoff
                    else:
                        raise

            raise last_exception

        return wrapper

    return decorator


def measure_performance():
    """Decorator to measure function performance"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                status = "success"
                error = None
            except Exception as e:
                result = None
                status = "error"
                error = str(e)
                raise
            finally:
                elapsed = time.perf_counter() - start_time

                logger.info(
                    f"Performance: {func.__name__} - " f"Time: {elapsed:.4f}s - Status: {status}"
                )

                if error:
                    logger.error(f"Error in {func.__name__}: {error}")

            return result

        return wrapper

    return decorator


def validate_input(schema: Type[BaseModel]):
    """Decorator to validate input with Pydantic schema"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the first argument that should be validated
            if args and hasattr(args[0], "__dict__"):
                # Skip self if this is a method
                validate_args = args[1:] if len(args) > 1 else args
            else:
                validate_args = args

            # Validate each argument against schema if applicable
            validated_args = []
            for arg in validate_args:
                if isinstance(arg, dict):
                    try:
                        validated_arg = schema(**arg)
                        validated_args.append(validated_arg)
                    except Exception as e:
                        raise ValueError(f"Validation error: {e}")
                else:
                    validated_args.append(arg)

            # Reconstruct args tuple
            if args and hasattr(args[0], "__dict__"):
                final_args = (args[0],) + tuple(validated_args)
            else:
                final_args = tuple(validated_args)

            return await func(*final_args, **kwargs)

        return wrapper

    return decorator


# Utility mixins for common operations
class FieldUtilsMixin:
    """Utility functions for field operations"""

    @classmethod
    def get_model_fields(cls, model: Type[T]) -> List[str]:
        """Get all field names from SQLAlchemy model"""
        from sqlalchemy import inspect

        mapper = inspect(model)
        return [column.name for column in mapper.columns]

    @classmethod
    def get_relationship_fields(cls, model: Type[T]) -> List[str]:
        """Get relationship field names from SQLAlchemy model"""
        from sqlalchemy import inspect

        mapper = inspect(model)
        return list(mapper.relationships.keys())

    @classmethod
    def exclude_fields(cls, data: Dict[str, Any], exclude: List[str]) -> Dict[str, Any]:
        """Exclude specified fields from data dict"""
        return {k: v for k, v in data.items() if k not in exclude}

    @classmethod
    def include_fields(cls, data: Dict[str, Any], include: List[str]) -> Dict[str, Any]:
        """Include only specified fields from data dict"""
        return {k: v for k, v in data.items() if k in include}

    @classmethod
    def snake_to_camel(cls, snake_str: str) -> str:
        """Convert snake_case to camelCase"""
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    @classmethod
    def camel_to_snake(cls, camel_str: str) -> str:
        """Convert camelCase to snake_case"""
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_str)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class SerializationMixin:
    """Mixin for serialization utilities"""

    def to_dict(
        self,
        exclude: Optional[List[str]] = None,
        include: Optional[List[str]] = None,
        relationships: bool = False,
    ) -> Dict[str, Any]:
        """Convert model to dictionary with options"""
        from sqlalchemy import inspect

        mapper = inspect(self)
        data = {}

        # Get columns
        for column in mapper.columns:
            field_name = column.name

            # Apply include/exclude filters
            if include and field_name not in include:
                continue
            if exclude and field_name in exclude:
                continue

            value = getattr(self, field_name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif hasattr(value, "to_dict"):
                value = value.to_dict()

            data[field_name] = value

        # Add relationships if requested
        if relationships:
            for rel in mapper.relationships:
                field_name = rel.key

                # Apply include/exclude filters
                if include and field_name not in include:
                    continue
                if exclude and field_name in exclude:
                    continue

                value = getattr(self, field_name)
                if value is not None:
                    if hasattr(value, "to_dict"):
                        data[field_name] = value.to_dict()
                    elif isinstance(value, list):
                        data[field_name] = [
                            item.to_dict() if hasattr(item, "to_dict") else item for item in value
                        ]
                    else:
                        data[field_name] = value

        return data

    def to_json(
        self,
        exclude: Optional[List[str]] = None,
        include: Optional[List[str]] = None,
        relationships: bool = False,
    ) -> str:
        """Convert model to JSON string"""
        import json

        data = self.to_dict(exclude=exclude, include=include, relationships=relationships)
        return json.dumps(data, default=str)
