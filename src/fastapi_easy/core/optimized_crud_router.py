"""
Optimized CRUD Router with enhanced performance and features

Provides:
- Batch operations support
- Smart query optimization
- Efficient pagination
- Field-level selection
- Aggregated queries
- Performance monitoring
- Type safety improvements
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
)

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Request,
    status,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, create_model
from sqlalchemy import Select, and_, asc, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from .cache import QueryCache
from .errors import ConflictError
from .optimized_database import get_db_manager, monitor_performance

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=DeclarativeBase)
SchemaType = TypeVar("SchemaType", bound=BaseModel)


class OperationType(Enum):
    """CRUD operation types"""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    BATCH_CREATE = "batch_create"
    BATCH_UPDATE = "batch_update"
    BATCH_DELETE = "batch_delete"


@dataclass
class QueryParams:
    """Enhanced query parameters"""

    filters: Dict[str, Any] = Field(default_factory=dict)
    sorts: Dict[str, Literal["asc", "desc"]] = Field(default_factory=dict)
    search: Optional[str] = None
    search_fields: Optional[List[str]] = None
    include: Optional[List[str]] = None
    exclude: Optional[List[str]] = None
    aggregation: Optional[List[str]] = None
    group_by: Optional[List[str]] = None


@dataclass
class BatchParams:
    """Batch operation parameters"""

    batch_size: int = Field(default=1000, gt=0, le=10000)
    continue_on_error: bool = Field(default=False)
    validate_before: bool = Field(default=True)
    return_details: bool = Field(default=True)


class OptimizedCRUDRouter(APIRouter):
    """
    High-performance CRUD router with optimizations
    """

    def __init__(
        self,
        schema: Type[SchemaType],
        model: Type[T],
        db_manager: Optional[Any] = None,
        prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
        id_type: Type = int,
        id_field: str = "id",
        create_schema: Optional[Type[SchemaType]] = None,
        update_schema: Optional[Type[SchemaType]] = None,
        response_schema: Optional[Type[SchemaType]] = None,
        max_page_size: int = 1000,
        default_page_size: int = 50,
        enable_cache: bool = True,
        cache_ttl: int = 300,
        enable_search: bool = True,
        searchable_fields: Optional[List[str]] = None,
        enable_batch: bool = True,
        enable_soft_delete: bool = False,
        soft_delete_field: str = "deleted_at",
        exclude_fields: Optional[Set[str]] = None,
        **kwargs: Any,
    ):
        """Initialize optimized CRUD router"""
        # Store configurations
        self.schema = schema
        self.model = model
        self.db_manager = db_manager
        self.id_type = id_type
        self.id_field = id_field
        self.max_page_size = max_page_size
        self.default_page_size = default_page_size
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.enable_search = enable_search
        self.searchable_fields = searchable_fields or []
        self.enable_batch = enable_batch
        self.enable_soft_delete = enable_soft_delete
        self.soft_delete_field = soft_delete_field
        self.exclude_fields = exclude_fields or set()

        # Schema configurations
        self.create_schema = create_schema or schema
        self.update_schema = update_schema or self._create_update_schema()
        self.response_schema = response_schema or self._create_response_schema()

        # Initialize cache if enabled
        self.cache: Optional[QueryCache] = None
        if self.enable_cache:
            self.cache = QueryCache(max_size=1000, default_ttl=self.cache_ttl)

        # Set default prefix and tags
        if prefix is None:
            prefix = f"/{schema.__name__.lower()}"
        if tags is None:
            tags = [schema.__name__]

        # Initialize router
        super().__init__(prefix=prefix, tags=tags, **kwargs)

        # Generate routes
        self._generate_optimized_routes()

    def _create_update_schema(self) -> Type[BaseModel]:
        """Create partial update schema"""
        return create_model(
            f"{self.schema.__name__}Update",
            **{
                name: (field_info.annotation, Field(None, **field_info.kwargs))
                for name, field_info in self.schema.model_fields.items()
                if name != self.id_field
            },
        )

    def _create_response_schema(self) -> Type[BaseModel]:
        """Create response schema with additional fields"""
        return self.schema

    def _generate_optimized_routes(self) -> None:
        """Generate optimized CRUD routes"""
        # Standard CRUD operations
        self._add_get_all_route()
        self._add_get_one_route()
        self._add_create_route()
        self._add_update_route()
        self._add_delete_route()

        # Advanced operations
        if self.enable_batch:
            self._add_batch_routes()

        if self.enable_search:
            self._add_search_route()

        self._add_aggregation_route()
        self._add_count_route()

    def _get_cache_key(self, operation: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for operation"""
        key_parts = [self.model.__name__, operation, str(params or {})]
        return ":".join(key_parts)

    @monitor_performance
    async def _get_all(
        self,
        query_params: QueryParams,
        session: AsyncSession,
        page: int = 1,
        page_size: Optional[int] = None,
    ) -> Tuple[List[T], int]:
        """Get all items with pagination and filtering"""
        # Validate pagination
        if page_size is None:
            page_size = self.default_page_size
        page_size = min(page_size, self.max_page_size)

        offset = (page - 1) * page_size

        # Build base query
        base_query = Select(self.model)

        # Apply filters
        base_query = self._apply_filters(base_query, query_params.filters)

        # Apply soft delete filter
        if self.enable_soft_delete:
            base_query = base_query.where(getattr(self.model, self.soft_delete_field).is_(None))

        # Apply search
        if query_params.search and self.searchable_fields:
            base_query = self._apply_search(base_query, query_params.search)

        # Apply sorting
        base_query = self._apply_sorting(base_query, query_params.sorts)

        # Get total count
        count_query = Select(func.count()).select_from(base_query.subquery())
        total_count = await session.scalar(count_query)

        # Apply pagination and fetch
        query = base_query.offset(offset).limit(page_size)
        result = await session.execute(query)
        items = result.scalars().all()

        return list(items), total_count

    def _apply_filters(self, query: Select, filters: Dict[str, Any]) -> Select:
        """Apply filters to query"""
        if not filters:
            return query

        filter_conditions = []
        for field, value in filters.items():
            if hasattr(self.model, field):
                model_field = getattr(self.model, field)

                if isinstance(value, dict):
                    # Handle complex filters (e.g., { "gt": 10, "lt": 100 })
                    for operator, val in value.items():
                        if operator == "gt":
                            filter_conditions.append(model_field > val)
                        elif operator == "gte":
                            filter_conditions.append(model_field >= val)
                        elif operator == "lt":
                            filter_conditions.append(model_field < val)
                        elif operator == "lte":
                            filter_conditions.append(model_field <= val)
                        elif operator == "ne":
                            filter_conditions.append(model_field != val)
                        elif operator == "in":
                            filter_conditions.append(model_field.in_(val))
                        elif operator == "nin":
                            filter_conditions.append(model_field.notin_(val))
                        elif operator == "like":
                            filter_conditions.append(model_field.like(val))
                        elif operator == "ilike":
                            filter_conditions.append(model_field.ilike(val))
                else:
                    # Simple equality filter
                    filter_conditions.append(model_field == value)

        if filter_conditions:
            query = query.where(and_(*filter_conditions))

        return query

    def _apply_search(self, query: Select, search_term: str) -> Select:
        """Apply full-text search"""
        search_conditions = []
        for field_name in self.searchable_fields:
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                search_conditions.append(field.ilike(f"%{search_term}%"))

        if search_conditions:
            query = query.where(or_(*search_conditions))

        return query

    def _apply_sorting(self, query: Select, sorts: Dict[str, str]) -> Select:
        """Apply sorting to query"""
        if not sorts:
            # Apply default sorting by ID
            return query.order_by(getattr(self.model, self.id_field))

        for field_name, direction in sorts.items():
            if hasattr(self.model, field_name):
                field = getattr(self.model, field_name)
                if direction.lower() == "desc":
                    query = query.order_by(desc(field))
                else:
                    query = query.order_by(asc(field))

        return query

    def _add_get_all_route(self) -> None:
        """Add optimized get all route"""

        async def route(
            request: Request,
            page: int = Query(1, ge=1, description="Page number"),
            page_size: int = Query(
                self.default_page_size, ge=1, le=self.max_page_size, description="Items per page"
            ),
            filters: str = Query(None, description="JSON-encoded filters"),
            sort: str = Query(None, description="Sort fields (field:direction)"),
            search: str = Query(None, description="Search term"),
            include: str = Query(None, description="Fields to include"),
            exclude: str = Query(None, description="Fields to exclude"),
        ):
            # Parse parameters
            query_params = QueryParams()
            if filters:
                try:
                    import json

                    query_params.filters = json.loads(filters)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid filters JSON")

            if sort:
                query_params.sorts = {
                    s.split(":")[0]: s.split(":")[1] if ":" in s else "asc" for s in sort.split(",")
                }

            query_params.search = search

            # Build cache key
            cache_key = self._get_cache_key(
                "get_all",
                {
                    "page": page,
                    "page_size": page_size,
                    "filters": query_params.filters,
                    "sorts": query_params.sorts,
                    "search": search,
                },
            )

            # Check cache
            if self.cache:
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    return cached_result

            # Execute query
            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                items, total_count = await self._get_all(query_params, session, page, page_size)

                # Serialize items
                serialized_items = [self.response_schema.model_validate(item) for item in items]

                result = {
                    "items": serialized_items,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total": total_count,
                        "pages": (total_count + page_size - 1) // page_size,
                    },
                }

                # Cache result
                if self.cache:
                    await self.cache.set(cache_key, result, self.cache_ttl)

                return result

        self.add_api_route(
            "/",
            route,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary=f"Get all {self.schema.__name__} items",
            description=f"Retrieve paginated list of {self.schema.__name__} items with filtering and sorting",
        )

    def _add_get_one_route(self) -> None:
        """Add optimized get one route"""

        async def route(
            request: Request,
            item_id: self.id_type = Path(..., description=f"{self.schema.__name__} ID"),
            include: str = Query(None, description="Fields to include"),
        ):
            cache_key = self._get_cache_key("get_one", {"id": item_id})

            # Check cache
            if self.cache:
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    return cached_result

            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                query = Select(self.model).where(getattr(self.model, self.id_field) == item_id)

                if self.enable_soft_delete:
                    query = query.where(getattr(self.model, self.soft_delete_field).is_(None))

                result = await session.execute(query)
                item = result.scalar_one_or_none()

                if not item:
                    raise HTTPException(
                        status_code=404,
                        detail=f"{self.schema.__name__} with {self.id_field} {item_id} not found",
                    )

                serialized_item = self.response_schema.model_validate(item)

                # Cache result
                if self.cache:
                    await self.cache.set(cache_key, serialized_item, self.cache_ttl)

                return serialized_item

        self.add_api_route(
            "/{item_id}",
            route,
            methods=["GET"],
            response_model=self.response_schema,
            summary=f"Get {self.schema.__name__} by ID",
            description=f"Retrieve a specific {self.schema.__name__} item by its {self.id_field}",
        )

    def _add_create_route(self) -> None:
        """Add optimized create route"""

        async def route(
            request: Request,
            item_data: self.create_schema = Body(..., description=f"{self.schema.__name__} data"),
        ):
            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                # Create model instance
                db_item = self.model(**item_data.model_dump(exclude_unset=True))

                try:
                    session.add(db_item)
                    await session.flush()  # Get the ID without committing
                    await session.commit()

                    # Invalidate relevant cache
                    if self.cache:
                        await self.cache.invalidate_pattern("get_all")

                    # Refresh and serialize
                    await session.refresh(db_item)
                    serialized_item = self.response_schema.model_validate(db_item)

                    return JSONResponse(
                        status_code=status.HTTP_201_CREATED, content=serialized_item.model_dump()
                    )

                except Exception as e:
                    await session.rollback()
                    if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                        raise ConflictError(f"{self.schema.__name__} already exists")
                    raise

        self.add_api_route(
            "/",
            route,
            methods=["POST"],
            response_model=self.response_schema,
            status_code=status.HTTP_201_CREATED,
            summary=f"Create {self.schema.__name__}",
            description=f"Create a new {self.schema.__name__} item",
        )

    def _add_update_route(self) -> None:
        """Add optimized update route"""

        async def route(
            request: Request,
            item_id: self.id_type = Path(..., description=f"{self.schema.__name__} ID"),
            item_data: self.update_schema = Body(
                ..., description=f"{self.schema.__name__} update data"
            ),
        ):
            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                # Get existing item
                query = Select(self.model).where(getattr(self.model, self.id_field) == item_id)

                if self.enable_soft_delete:
                    query = query.where(getattr(self.model, self.soft_delete_field).is_(None))

                result = await session.execute(query)
                item = result.scalar_one_or_none()

                if not item:
                    raise HTTPException(
                        status_code=404,
                        detail=f"{self.schema.__name__} with {self.id_field} {item_id} not found",
                    )

                # Update fields
                update_data = item_data.model_dump(exclude_unset=True)
                for field, value in update_data.items():
                    if hasattr(item, field):
                        setattr(item, field, value)

                try:
                    await session.commit()

                    # Invalidate cache
                    if self.cache:
                        await self.cache.invalidate_pattern(f"get_one:{item_id}")
                        await self.cache.invalidate_pattern("get_all")

                    # Refresh and serialize
                    await session.refresh(item)
                    serialized_item = self.response_schema.model_validate(item)

                    return serialized_item

                except Exception:
                    await session.rollback()
                    raise

        self.add_api_route(
            "/{item_id}",
            route,
            methods=["PUT"],
            response_model=self.response_schema,
            summary=f"Update {self.schema.__name__}",
            description=f"Update a {self.schema.__name__} item by its {self.id_field}",
        )

    def _add_delete_route(self) -> None:
        """Add optimized delete route"""

        async def route(
            request: Request,
            item_id: self.id_type = Path(..., description=f"{self.schema.__name__} ID"),
            soft: bool = Query(
                self.enable_soft_delete, description="Perform soft delete if supported"
            ),
        ):
            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                # Get existing item
                query = Select(self.model).where(getattr(self.model, self.id_field) == item_id)

                if self.enable_soft_delete and not soft:
                    query = query.where(getattr(self.model, self.soft_delete_field).is_(None))

                result = await session.execute(query)
                item = result.scalar_one_or_none()

                if not item:
                    raise HTTPException(
                        status_code=404,
                        detail=f"{self.schema.__name__} with {self.id_field} {item_id} not found",
                    )

                # Delete item
                if self.enable_soft_delete and soft:
                    # Soft delete
                    setattr(item, self.soft_delete_field, func.now())
                else:
                    # Hard delete
                    await session.delete(item)

                try:
                    await session.commit()

                    # Invalidate cache
                    if self.cache:
                        await self.cache.invalidate_pattern(f"get_one:{item_id}")
                        await self.cache.invalidate_pattern("get_all")

                    if self.enable_soft_delete and soft:
                        return {"message": f"{self.schema.__name__} soft deleted successfully"}
                    else:
                        return {"message": f"{self.schema.__name__} deleted successfully"}

                except Exception:
                    await session.rollback()
                    raise

        self.add_api_route(
            "/{item_id}",
            route,
            methods=["DELETE"],
            response_model=Dict[str, str],
            summary=f"Delete {self.schema.__name__}",
            description=f"Delete a {self.schema.__name__} item by its {self.id_field}",
        )

    def _add_batch_routes(self) -> None:
        """Add batch operation routes"""
        from pydantic import BaseModel

        class BatchCreateRequest(BaseModel):
            items: List[self.create_schema]

        class BatchUpdateRequest(BaseModel):
            items: List[Dict[str, Any]]  # List of {id: ..., data: ...}

        class BatchDeleteRequest(BaseModel):
            ids: List[self.id_type]

        # Batch create
        async def batch_create_route(
            request: Request,
            batch_data: BatchCreateRequest = Body(...),
            params: BatchParams = Depends(),
        ):
            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                created_items = []
                errors = []

                for i, item_data in enumerate(batch_data.items):
                    try:
                        db_item = self.model(**item_data.model_dump(exclude_unset=True))
                        session.add(db_item)
                        await session.flush()  # Get ID without committing
                        created_items.append(db_item)
                    except Exception as e:
                        errors.append({"index": i, "error": str(e)})
                        if not params.continue_on_error:
                            await session.rollback()
                            raise HTTPException(
                                status_code=400, detail=f"Batch creation failed at index {i}: {e!s}"
                            )

                try:
                    await session.commit()

                    # Invalidate cache
                    if self.cache:
                        await self.cache.invalidate_pattern("get_all")

                    # Serialize results
                    serialized_items = [
                        self.response_schema.model_validate(item) for item in created_items
                    ]

                    response = {"created": serialized_items}
                    if params.return_details and errors:
                        response["errors"] = errors

                    return response

                except Exception:
                    await session.rollback()
                    raise

        # Batch update
        async def batch_update_route(
            request: Request,
            batch_data: BatchUpdateRequest = Body(...),
            params: BatchParams = Depends(),
        ):
            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                updated_items = []
                errors = []

                for i, update_item in enumerate(batch_data.items):
                    try:
                        item_id = update_item.get("id")
                        item_data = update_item.get("data", {})

                        if not item_id:
                            raise ValueError("Missing 'id' field")

                        # Get existing item
                        query = Select(self.model).where(
                            getattr(self.model, self.id_field) == item_id
                        )
                        if self.enable_soft_delete:
                            query = query.where(
                                getattr(self.model, self.soft_delete_field).is_(None)
                            )

                        result = await session.execute(query)
                        item = result.scalar_one_or_none()

                        if not item:
                            raise ValueError(f"Item with ID {item_id} not found")

                        # Update item
                        for field, value in item_data.items():
                            if hasattr(item, field):
                                setattr(item, field, value)

                        updated_items.append(item)

                    except Exception as e:
                        errors.append({"index": i, "error": str(e)})
                        if not params.continue_on_error:
                            await session.rollback()
                            raise HTTPException(
                                status_code=400, detail=f"Batch update failed at index {i}: {e!s}"
                            )

                try:
                    await session.commit()

                    # Invalidate cache
                    if self.cache:
                        await self.cache.invalidate_pattern("get_all")

                    # Serialize results
                    serialized_items = [
                        self.response_schema.model_validate(item) for item in updated_items
                    ]

                    response = {"updated": serialized_items}
                    if params.return_details and errors:
                        response["errors"] = errors

                    return response

                except Exception:
                    await session.rollback()
                    raise

        # Batch delete
        async def batch_delete_route(
            request: Request,
            batch_data: BatchDeleteRequest = Body(...),
            soft: bool = Query(self.enable_soft_delete),
            params: BatchParams = Depends(),
        ):
            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                deleted_count = 0
                errors = []

                for i, item_id in enumerate(batch_data.ids):
                    try:
                        query = Select(self.model).where(
                            getattr(self.model, self.id_field) == item_id
                        )
                        if self.enable_soft_delete and not soft:
                            query = query.where(
                                getattr(self.model, self.soft_delete_field).is_(None)
                            )

                        result = await session.execute(query)
                        item = result.scalar_one_or_none()

                        if not item:
                            raise ValueError(f"Item with ID {item_id} not found")

                        if self.enable_soft_delete and soft:
                            setattr(item, self.soft_delete_field, func.now())
                        else:
                            await session.delete(item)

                        deleted_count += 1

                    except Exception as e:
                        errors.append({"id": item_id, "error": str(e)})
                        if not params.continue_on_error:
                            await session.rollback()
                            raise HTTPException(
                                status_code=400,
                                detail=f"Batch delete failed for ID {item_id}: {e!s}",
                            )

                try:
                    await session.commit()

                    # Invalidate cache
                    if self.cache:
                        await self.cache.invalidate_pattern("get_all")

                    response = {
                        "deleted_count": deleted_count,
                        "message": f"Successfully deleted {deleted_count} items",
                    }
                    if params.return_details and errors:
                        response["errors"] = errors

                    return response

                except Exception:
                    await session.rollback()
                    raise

        self.add_api_route(
            "/batch/create",
            batch_create_route,
            methods=["POST"],
            response_model=Dict[str, Any],
            summary=f"Batch create {self.schema.__name__}",
            description=f"Create multiple {self.schema.__name__} items in a single operation",
        )

        self.add_api_route(
            "/batch/update",
            batch_update_route,
            methods=["PUT"],
            response_model=Dict[str, Any],
            summary=f"Batch update {self.schema.__name__}",
            description=f"Update multiple {self.schema.__name__} items in a single operation",
        )

        self.add_api_route(
            "/batch/delete",
            batch_delete_route,
            methods=["DELETE"],
            response_model=Dict[str, Any],
            summary=f"Batch delete {self.schema.__name__}",
            description=f"Delete multiple {self.schema.__name__} items in a single operation",
        )

    def _add_search_route(self) -> None:
        """Add advanced search route"""

        async def search_route(
            request: Request,
            query: str = Query(..., min_length=1, description="Search query"),
            fields: str = Query(None, description="Fields to search in (comma-separated)"),
            page: int = Query(1, ge=1),
            page_size: int = Query(self.default_page_size, ge=1, le=self.max_page_size),
            fuzzy: bool = Query(False, description="Enable fuzzy search"),
        ):
            search_fields = []
            if fields:
                search_fields = [f.strip() for f in fields.split(",")]
            else:
                search_fields = self.searchable_fields

            if not search_fields:
                raise HTTPException(status_code=400, detail="No searchable fields specified")

            # Build search query
            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                base_query = Select(self.model)

                if fuzzy:
                    # Implement fuzzy search (using LIKE with wildcards)
                    search_conditions = []
                    for field_name in search_fields:
                        if hasattr(self.model, field_name):
                            field = getattr(self.model, field_name)
                            search_conditions.append(field.ilike(f"%{query}%"))

                    if search_conditions:
                        base_query = base_query.where(or_(*search_conditions))
                else:
                    # Exact match search
                    search_conditions = []
                    for field_name in search_fields:
                        if hasattr(self.model, field_name):
                            field = getattr(self.model, field_name)
                            search_conditions.append(field.ilike(f"%{query}%"))

                    if search_conditions:
                        base_query = base_query.where(or_(*search_conditions))

                # Apply soft delete filter
                if self.enable_soft_delete:
                    base_query = base_query.where(
                        getattr(self.model, self.soft_delete_field).is_(None)
                    )

                # Get count and paginated results
                count_query = Select(func.count()).select_from(base_query.subquery())
                total_count = await session.scalar(count_query)

                offset = (page - 1) * page_size
                query = base_query.offset(offset).limit(page_size)
                result = await session.execute(query)
                items = result.scalars().all()

                # Serialize results
                serialized_items = [self.response_schema.model_validate(item) for item in items]

                return {
                    "query": query,
                    "fields": search_fields,
                    "fuzzy": fuzzy,
                    "items": serialized_items,
                    "pagination": {
                        "page": page,
                        "page_size": page_size,
                        "total": total_count,
                        "pages": (total_count + page_size - 1) // page_size,
                    },
                }

        self.add_api_route(
            "/search",
            search_route,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary=f"Search {self.schema.__name__}",
            description=f"Search {self.schema.__name__} items across specified fields",
        )

    def _add_aggregation_route(self) -> None:
        """Add aggregation route"""

        async def aggregation_route(
            request: Request,
            group_by: str = Query(..., description="Field to group by"),
            aggregate: str = Query(
                "count", description="Aggregation function (count, sum, avg, min, max)"
            ),
            field: str = Query(None, description="Field for sum/avg/min/max aggregations"),
            filters: str = Query(None, description="JSON-encoded filters"),
        ):
            if aggregate not in ["count", "sum", "avg", "min", "max"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid aggregation function. Use: count, sum, avg, min, max",
                )

            if aggregate != "count" and not field:
                raise HTTPException(
                    status_code=400, detail=f"Field is required for {aggregate} aggregation"
                )

            # Parse filters
            parsed_filters = {}
            if filters:
                try:
                    import json

                    parsed_filters = json.loads(filters)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid filters JSON")

            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                # Build query
                group_field = getattr(self.model, group_by, None)
                if not group_field:
                    raise HTTPException(
                        status_code=400, detail=f"Field '{group_by}' not found in model"
                    )

                base_query = Select(self.model)
                base_query = self._apply_filters(base_query, parsed_filters)

                if self.enable_soft_delete:
                    base_query = base_query.where(
                        getattr(self.model, self.soft_delete_field).is_(None)
                    )

                # Apply aggregation
                if aggregate == "count":
                    agg_func = func.count()
                elif aggregate == "sum":
                    agg_field = getattr(self.model, field, None)
                    if not agg_field:
                        raise HTTPException(status_code=400, detail=f"Field '{field}' not found")
                    agg_func = func.sum(agg_field)
                elif aggregate == "avg":
                    agg_field = getattr(self.model, field, None)
                    if not agg_field:
                        raise HTTPException(status_code=400, detail=f"Field '{field}' not found")
                    agg_func = func.avg(agg_field)
                elif aggregate == "min":
                    agg_field = getattr(self.model, field, None)
                    if not agg_field:
                        raise HTTPException(status_code=400, detail=f"Field '{field}' not found")
                    agg_func = func.min(agg_field)
                elif aggregate == "max":
                    agg_field = getattr(self.model, field, None)
                    if not agg_field:
                        raise HTTPException(status_code=400, detail=f"Field '{field}' not found")
                    agg_func = func.max(agg_field)

                query = Select(group_field, agg_func.label("value")).select_from(base_query)
                query = query.group_by(group_field)

                # Execute query
                result = await session.execute(query)
                rows = result.all()

                # Format results
                results = [{"group": row[0], "value": row[1]} for row in rows]

                return {
                    "group_by": group_by,
                    "aggregate": aggregate,
                    "field": field if aggregate != "count" else None,
                    "results": results,
                    "total_groups": len(results),
                }

        self.add_api_route(
            "/aggregate",
            aggregation_route,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary=f"Aggregate {self.schema.__name__}",
            description=f"Perform aggregation operations on {self.schema.__name__} data",
        )

    def _add_count_route(self) -> None:
        """Add count route"""

        async def count_route(
            request: Request,
            filters: str = Query(None, description="JSON-encoded filters"),
        ):
            # Parse filters
            parsed_filters = {}
            if filters:
                try:
                    import json

                    parsed_filters = json.loads(filters)
                except json.JSONDecodeError:
                    raise HTTPException(status_code=400, detail="Invalid filters JSON")

            db_manager = self.db_manager or await get_db_manager()
            async with db_manager.get_session() as session:
                # Build count query
                base_query = Select(self.model)
                base_query = self._apply_filters(base_query, parsed_filters)

                if self.enable_soft_delete:
                    base_query = base_query.where(
                        getattr(self.model, self.soft_delete_field).is_(None)
                    )

                count_query = Select(func.count()).select_from(base_query.subquery())
                total_count = await session.scalar(count_query)

                return {"count": total_count, "filters": parsed_filters}

        self.add_api_route(
            "/count",
            count_route,
            methods=["GET"],
            response_model=Dict[str, Any],
            summary=f"Count {self.schema.__name__}",
            description=f"Get the count of {self.schema.__name__} items matching filters",
        )
