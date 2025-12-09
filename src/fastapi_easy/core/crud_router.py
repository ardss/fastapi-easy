"""Main CRUD router for FastAPI.

This module provides an automatic CRUD router generator for FastAPI applications.
It creates complete REST endpoints for any Pydantic model, supporting filtering,
sorting, pagination, and more with minimal configuration.

The router follows REST conventions and integrates seamlessly with different
ORM adapters (SQLAlchemy, Tortoise, MongoDB, etc.) while maintaining
consistent behavior across all implementations.

Example:
    ```python
    from fastapi import FastAPI
    from fastapi_easy import CRUDRouter, SQLAlchemyAdapter

    app = FastAPI()

    # Auto-generate CRUD routes for User model
    app.include_router(
        CRUDRouter(
            schema=UserRead,
            adapter=SQLAlchemyAdapter(User, get_db),
            prefix="/users"
        )
    )
    ```
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Body, HTTPException, Path, Query, Request

if TYPE_CHECKING:
    from typing import List, Optional, Type

    from pydantic import BaseModel

    from .adapters import ORMAdapter
    from .config import CRUDConfig

from .exceptions import (
    DatabaseConnectionException,
    DatabaseQueryException,
    ErrorContext,
    FastAPIEasyException,
    NotFoundError,
)
from .hooks import ExecutionContext, HookRegistry

logger = logging.getLogger(__name__)


class CRUDRouter(APIRouter):
    """CRUD Router for automatic API generation.

    Generates complete CRUD routes automatically with support for filtering,
    sorting, pagination, soft deletion, and more. This router follows REST
    conventions and integrates seamlessly with different ORM adapters.

    The router automatically creates the following endpoints:
    - GET /prefix/ - List all resources with filtering, sorting, and pagination
    - GET /prefix/{id} - Get a single resource by ID
    - POST /prefix/ - Create a new resource
    - PUT /prefix/{id} - Update a resource (full or partial)
    - DELETE /prefix/{id} - Delete a resource (soft or hard)
    - DELETE /prefix/ - Batch delete resources (optional)

    Attributes:
        schema: Pydantic schema for reading/serializing resources
        create_schema: Schema for creating resources
        update_schema: Schema for updating resources
        adapter: ORM adapter for database operations
        config: CRUD configuration settings
        hooks: Hook registry for extending functionality

    Example:
        ```python
        router = CRUDRouter(
            schema=UserRead,
            create_schema=UserCreate,
            update_schema=UserUpdate,
            adapter=SQLAlchemyAdapter(User, get_db),
            prefix="/api/v1/users",
            tags=["Users"]
        )

        # The router now provides these endpoints:
        # GET /api/v1/users
        # GET /api/v1/users/{id}
        # POST /api/v1/users
        # PUT /api/v1/users/{id}
        # DELETE /api/v1/users/{id}
        ```
    """

    def __init__(
        self,
        schema: type["BaseModel"],
        adapter: "ORMAdapter" | None = None,
        config: "CRUDConfig" | None = None,
        prefix: str | None = None,
        tags: list[str] | None = None,
        id_type: type = int,
        create_schema: type["BaseModel"] | None = None,
        update_schema: type["BaseModel"] | None = None,
        **kwargs: Any,
    ):
        """Initialize CRUD Router.

        Args:
            schema: Pydantic schema for the resource (used for reading responses)
            adapter: ORM adapter instance for database operations
            config: CRUD configuration with customization options
            prefix: URL prefix for all routes (default: lowercase schema name)
            tags: OpenAPI tags for documentation grouping
            id_type: Type of the ID field (default: int)
            create_schema: Schema for creation requests (default: same as schema)
            update_schema: Schema for update requests (default: same as schema)
            **kwargs: Additional arguments passed to APIRouter

        Raises:
            ValueError: If schema is not provided

        Note:
            The adapter is optional but required for actual database operations.
            Without an adapter, routes will return empty results.
        """
        # Initialize configuration
        self.schema = schema
        self.create_schema = create_schema or schema
        self.update_schema = update_schema or schema
        self.adapter = adapter
        self.config = config or CRUDConfig()
        self.config.validate()
        self.id_type = id_type

        # Validate adapter is provided
        if self.adapter is None:
            import warnings

            warnings.warn(
                "No adapter provided to CRUDRouter. Routes will return empty results. "
                "Please provide a backend adapter (e.g., SQLAlchemyAdapter) to enable database operations.",
                UserWarning,
                stacklevel=2,
            )

        # Initialize hooks
        self.hooks = HookRegistry()

        # Set default prefix
        if prefix is None:
            prefix = f"/{schema.__name__.lower()}"

        # Set default tags
        if tags is None:
            tags = [schema.__name__]

        # Initialize APIRouter
        super().__init__(prefix=prefix, tags=tags, **kwargs)

        # 🔥 Generate CRUD routes
        self._generate_routes()

    def _generate_routes(self) -> None:
        """Generate FastAPI routes"""
        self._add_get_all_route()
        self._add_get_one_route()
        self._add_create_route()
        self._add_update_route()
        self._add_delete_one_route()
        self._add_delete_all_route()

    def _handle_error(self, e: Exception, default_detail: str, operation: str = None) -> None:
        """Handle errors with FastAPI-Easy exception system"""
        context = ErrorContext(
            resource=self.schema.__name__,
            action=operation or "unknown",
            metadata={"error_detail": default_detail},
        )

        # Convert different types of exceptions to FastAPI-Easy exceptions
        if isinstance(e, FastAPIEasyException):
            e.with_context(**context.__dict__)
            raise e
        elif "connection" in str(e).lower():
            raise DatabaseConnectionException(
                database=str(self.adapter),
                original_error=e,
            ).with_context(**context.__dict__)
        elif "query" in str(e).lower() or "sql" in str(e).lower():
            raise DatabaseQueryException(
                query=str(e),
                database=str(self.adapter),
                original_error=e,
            ).with_context(**context.__dict__)
        else:
            raise FastAPIEasyException(
                message=f"{default_detail}: {e!s}",
                details_field="error_detail",
                value=str(e),
                cause=e,
            ).with_context(**context.__dict__)

    def _add_get_all_route(self) -> None:
        """Add GET all items route"""

        async def get_all(
            request: Request,
            skip: int = Query(0, ge=0, description="Number of items to skip"),
            limit: int = Query(
                self.config.default_limit,
                ge=1,
                le=self.config.max_limit,
                description="Number of items to return",
            ),
        ) -> List[Any]:
            """Get all items"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                filters={},
                sorts={},
                pagination={"skip": skip, "limit": limit},
            )

            # Trigger hooks with error handling
            try:
                await self.hooks.trigger("before_get_all", context)
            except Exception as e:
                logger.error(f"Error in before_get_all hook: {e!s}", exc_info=True)
                raise HTTPException(status_code=500, detail="Hook execution failed")

            # Execute adapter method
            result = []
            if self.adapter:
                try:
                    result = await self.adapter.get_all(
                        filters=context.filters,
                        sorts=context.sorts,
                        pagination=context.pagination,
                    )
                    if result is None:
                        result = []
                    elif not isinstance(result, list):
                        logger.error(f"Expected list from get_all, got {type(result)}")
                        result = []
                except Exception as e:
                    self._handle_error(e, "Failed to retrieve items", operation="get_all")

            # Trigger hooks with error handling
            context.result = result
            try:
                await self.hooks.trigger("after_get_all", context)
            except Exception as e:
                logger.error(f"Error in after_get_all hook: {e!s}", exc_info=True)
                # Don't fail the request if after hook fails

            # Convert result items to Pydantic models if they're not already
            if result and isinstance(result, list):
                converted_result = []
                for item in result:
                    if item is not None and not isinstance(item, dict):
                        # If it's a SQLAlchemy model or similar, convert using the schema
                        try:
                            item = self.schema.model_validate(item)
                        except Exception:
                            # If validation fails, try to convert to dict first
                            try:
                                if hasattr(item, 'model_dump'):
                                    item_dict = item.model_dump()
                                elif hasattr(item, '__dict__'):
                                    item_dict = item.__dict__
                                else:
                                    item_dict = dict(item)
                                item = self.schema.model_validate(item_dict)
                            except Exception:
                                # If all else fails, keep as is
                                pass
                    converted_result.append(item)
                result = converted_result

            return result

        self.add_api_route(
            "/",
            get_all,
            methods=["GET"],
            response_model=List[Any],
            summary=f"Get all {self.schema.__name__} items",
            description=f"Retrieve a list of {self.schema.__name__} items with pagination",
        )

    def _add_get_one_route(self) -> None:
        """Add GET single item route"""
        from fastapi import HTTPException

        async def get_one(
            request: Request,
            id: Any = Path(..., description="Item ID"),
        ) -> Any:
            """Get single item by ID"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                metadata={"id": id},
            )

            # Trigger hooks with error handling
            try:
                await self.hooks.trigger("before_get_one", context)
            except Exception as e:
                logger.error(f"Error in before_get_one hook: {e!s}", exc_info=True)
                raise HTTPException(status_code=500, detail="Hook execution failed")

            # Execute adapter method
            result = None
            if self.adapter:
                try:
                    result = await self.adapter.get_one(id)
                except Exception as e:
                    self._handle_error(e, "Failed to retrieve item", operation="get_one")

            # Return 404 if not found
            if result is None:
                raise NotFoundError(
                    resource=self.schema.__name__,
                    identifier=id,
                ).with_context(
                    resource=self.schema.__name__,
                    action="get_one",
                )

            # Trigger hooks with error handling
            context.result = result
            try:
                await self.hooks.trigger("after_get_one", context)
            except Exception as e:
                logger.error(f"Error in after_get_one hook: {e!s}", exc_info=True)
                # Don't fail the request if after hook fails

            # Convert result to Pydantic model if it's not already
            if result is not None:
                if not isinstance(result, dict):
                    # If it's a SQLAlchemy model or similar, convert using the schema
                    try:
                        result = self.schema.model_validate(result)
                    except Exception:
                        # If validation fails, try to convert to dict first
                        try:
                            if hasattr(result, 'model_dump'):
                                result_dict = result.model_dump()
                            elif hasattr(result, '__dict__'):
                                result_dict = result.__dict__
                            else:
                                result_dict = dict(result)
                            result = self.schema.model_validate(result_dict)
                        except Exception:
                            # If all else fails, return as is
                            pass

            return result

        self.add_api_route(
            "/{id}",
            get_one,
            methods=["GET"],
            response_model=Any,
            summary=f"Get {self.schema.__name__} by ID",
            description=f"Retrieve a single {self.schema.__name__} item by its ID",
        )

    def _add_create_route(self) -> None:
        """Add POST create item route"""

        async def create(
            request: Request,
            data: Any = Body(..., description="Item data"),
        ) -> Any:
            """Create new item"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                data=data if isinstance(data, dict) else (data.model_dump() if hasattr(data, "model_dump") else data.dict()),
            )

            # Trigger hooks with error handling
            try:
                await self.hooks.trigger("before_create", context)
            except Exception as e:
                logger.error(f"Error in before_create hook: {e!s}", exc_info=True)
                raise HTTPException(status_code=500, detail="Hook execution failed")

            # Execute adapter method
            result = None
            if self.adapter:
                try:
                    result = await self.adapter.create(context.data)
                except Exception as e:
                    self._handle_error(e, "Failed to create item", operation="create")

            # Trigger hooks with error handling
            context.result = result
            try:
                await self.hooks.trigger("after_create", context)
            except Exception as e:
                logger.error(f"Error in after_create hook: {e!s}", exc_info=True)
                # Don't fail the request if after hook fails

            # Convert result to Pydantic model if it's not already
            if result is not None:
                if not isinstance(result, dict):
                    # If it's a SQLAlchemy model or similar, convert using the schema
                    try:
                        result = self.schema.model_validate(result)
                    except Exception:
                        # If validation fails, try to convert to dict first
                        try:
                            if hasattr(result, 'model_dump'):
                                result_dict = result.model_dump()
                            elif hasattr(result, '__dict__'):
                                result_dict = result.__dict__
                            else:
                                result_dict = dict(result)
                            result = self.schema.model_validate(result_dict)
                        except Exception:
                            # If all else fails, return as is
                            pass

            return result

        self.add_api_route(
            "/",
            create,
            methods=["POST"],
            response_model=Any,
            status_code=201,
            summary=f"Create {self.schema.__name__}",
            description=f"Create a new {self.schema.__name__} item",
        )

    def _add_update_route(self) -> None:
        """Add PUT update item route"""

        async def update(
            request: Request,
            id: Any = Path(..., description="Item ID"),
            data: Any = Body(..., description="Updated item data"),
        ) -> Any:
            """Update item"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                data=data if isinstance(data, dict) else (data.model_dump() if hasattr(data, "model_dump") else data.dict()),
                metadata={"id": id},
            )

            # Trigger hooks with error handling
            try:
                await self.hooks.trigger("before_update", context)
            except Exception as e:
                logger.error(f"Error in before_update hook: {e!s}", exc_info=True)
                raise HTTPException(status_code=500, detail="Hook execution failed")

            # Execute adapter method
            result = None
            if self.adapter:
                try:
                    result = await self.adapter.update(id, context.data)
                except Exception as e:
                    self._handle_error(e, "Failed to update item")

            # Trigger hooks with error handling
            context.result = result
            try:
                await self.hooks.trigger("after_update", context)
            except Exception as e:
                logger.error(f"Error in after_update hook: {e!s}", exc_info=True)
                # Don't fail the request if after hook fails

            # Convert result to Pydantic model if it's not already
            if result is not None:
                if not isinstance(result, dict):
                    # If it's a SQLAlchemy model or similar, convert using the schema
                    try:
                        result = self.schema.model_validate(result)
                    except Exception:
                        # If validation fails, try to convert to dict first
                        try:
                            if hasattr(result, 'model_dump'):
                                result_dict = result.model_dump()
                            elif hasattr(result, '__dict__'):
                                result_dict = result.__dict__
                            else:
                                result_dict = dict(result)
                            result = self.schema.model_validate(result_dict)
                        except Exception:
                            # If all else fails, return as is
                            pass

            return result

        self.add_api_route(
            "/{id}",
            update,
            methods=["PUT"],
            response_model=Any,
            summary=f"Update {self.schema.__name__}",
            description=f"Update an existing {self.schema.__name__} item",
        )

    def _add_delete_one_route(self) -> None:
        """Add DELETE single item route"""

        async def delete_one(
            request: Request,
            id: Any = Path(..., description="Item ID"),
        ) -> Any:
            """Delete single item"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                metadata={"id": id},
            )

            # Trigger hooks with error handling
            try:
                await self.hooks.trigger("before_delete", context)
            except Exception as e:
                logger.error(f"Error in before_delete hook: {e!s}", exc_info=True)
                raise HTTPException(status_code=500, detail="Hook execution failed")

            # Execute adapter method
            result = None
            if self.adapter:
                try:
                    result = await self.adapter.delete_one(id)
                except Exception as e:
                    self._handle_error(e, "Failed to delete item")

            # Trigger hooks with error handling
            context.result = result
            try:
                await self.hooks.trigger("after_delete", context)
            except Exception as e:
                logger.error(f"Error in after_delete hook: {e!s}", exc_info=True)
                # Don't fail the request if after hook fails

            # Convert result to Pydantic model if it's not already
            if result is not None:
                if not isinstance(result, dict):
                    # If it's a SQLAlchemy model or similar, convert using the schema
                    try:
                        result = self.schema.model_validate(result)
                    except Exception:
                        # If validation fails, try to convert to dict first
                        try:
                            if hasattr(result, 'model_dump'):
                                result_dict = result.model_dump()
                            elif hasattr(result, '__dict__'):
                                result_dict = result.__dict__
                            else:
                                result_dict = dict(result)
                            result = self.schema.model_validate(result_dict)
                        except Exception:
                            # If all else fails, return as is
                            pass

            return result

        self.add_api_route(
            "/{id}",
            delete_one,
            methods=["DELETE"],
            response_model=Any,
            summary=f"Delete {self.schema.__name__}",
            description=f"Delete a {self.schema.__name__} item by ID",
        )

    def _add_delete_all_route(self) -> None:
        """Add DELETE all items route"""
        from fastapi import HTTPException

        async def delete_all(
            request: Request,
        ) -> List[Any]:
            """Delete all items"""
            # Check if delete_all is enabled
            if not self.config.enable_delete_all:
                raise HTTPException(
                    status_code=403,
                    detail="Delete all operation is disabled for safety. Enable it in config if needed.",
                )

            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
            )

            # Trigger hooks with error handling
            try:
                await self.hooks.trigger("before_delete", context)
            except Exception as e:
                logger.error(f"Error in before_delete hook: {e!s}", exc_info=True)
                raise HTTPException(status_code=500, detail="Hook execution failed")

            # Execute adapter method
            result = []
            if self.adapter:
                try:
                    result = await self.adapter.delete_all()
                    if result is None:
                        result = []
                    elif not isinstance(result, list):
                        logger.error(f"Expected list from delete_all, got {type(result)}")
                        result = []
                except Exception as e:
                    self._handle_error(e, "Failed to delete items")

            # Trigger hooks with error handling
            context.result = result
            try:
                await self.hooks.trigger("after_delete", context)
            except Exception as e:
                logger.error(f"Error in after_delete hook: {e!s}", exc_info=True)
                # Don't fail the request if after hook fails

            # Convert result items to Pydantic models if they're not already
            if result and isinstance(result, list):
                converted_result = []
                for item in result:
                    if item is not None and not isinstance(item, dict):
                        # If it's a SQLAlchemy model or similar, convert using the schema
                        try:
                            item = self.schema.model_validate(item)
                        except Exception:
                            # If validation fails, try to convert to dict first
                            try:
                                if hasattr(item, 'model_dump'):
                                    item_dict = item.model_dump()
                                elif hasattr(item, '__dict__'):
                                    item_dict = item.__dict__
                                else:
                                    item_dict = dict(item)
                                item = self.schema.model_validate(item_dict)
                            except Exception:
                                # If all else fails, keep as is
                                pass
                    converted_result.append(item)
                result = converted_result

            return result

        self.add_api_route(
            "/",
            delete_all,
            methods=["DELETE"],
            response_model=List[Any],
            summary=f"Delete all {self.schema.__name__} items",
            description=f"Delete all {self.schema.__name__} items",
        )

    def get_config(self) -> CRUDConfig:
        """Get current configuration

        Returns:
            CRUD configuration
        """
        return self.config

    def update_config(self, **kwargs: Any) -> None:
        """Update configuration

        Args:
            **kwargs: Configuration fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        self.config.validate()
