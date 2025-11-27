"""Main CRUD Router class for FastAPI-Easy"""

from typing import Type, Optional, List, Any, Dict
from fastapi import APIRouter, Query, Path, Body, Request
from pydantic import BaseModel

from .config import CRUDConfig
from .adapters import ORMAdapter
from .hooks import HookRegistry, ExecutionContext


class CRUDRouter(APIRouter):
    """CRUD Router for automatic API generation
    
    Generates CRUD routes automatically with support for filtering,
    sorting, pagination, and more.
    """
    
    def __init__(
        self,
        schema: Type[BaseModel],
        adapter: Optional[ORMAdapter] = None,
        config: Optional[CRUDConfig] = None,
        prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
        id_type: Type = int,
        create_schema: Optional[Type[BaseModel]] = None,
        update_schema: Optional[Type[BaseModel]] = None,
        **kwargs: Any,
    ):
        """Initialize CRUD Router
        
        Args:
            schema: Pydantic schema for the resource (used for reading)
            adapter: ORM adapter instance
            config: CRUD configuration
            prefix: API prefix (default: lowercase schema name)
            tags: OpenAPI tags
            id_type: Type of the ID field (default: int)
            create_schema: Schema for creation (default: same as schema)
            update_schema: Schema for updates (default: same as schema)
            **kwargs: Additional arguments passed to APIRouter
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
                stacklevel=2
            )
        
        # Initialize registries
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
    
    def _add_get_all_route(self) -> None:
        """Add GET all items route"""
        async def get_all(
            request: Request,
            skip: int = Query(0, ge=0, description="Number of items to skip"),
            limit: int = Query(
                self.config.default_limit,
                ge=1,
                le=self.config.max_limit,
                description="Number of items to return"
            ),
        ) -> List[self.schema]:
            """Get all items"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                filters={},
                sorts={},
                pagination={"skip": skip, "limit": limit},
            )
            
            # Trigger hooks
            await self.hooks.trigger("before_get_all", context)
            
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
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in get_all: {str(e)}", exc_info=True)
                    raise
            
            # Trigger hooks
            context.result = result
            await self.hooks.trigger("after_get_all", context)
            
            return result
        
        self.add_api_route(
            "/",
            get_all,
            methods=["GET"],
            response_model=List[self.schema],
            summary=f"Get all {self.schema.__name__} items",
            description=f"Retrieve a list of {self.schema.__name__} items with pagination",
        )
    
    def _add_get_one_route(self) -> None:
        """Add GET single item route"""
        from fastapi import HTTPException
        
        async def get_one(
            request: Request,
            id: self.id_type = Path(..., description="Item ID"),
        ) -> self.schema:
            """Get single item by ID"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                metadata={"id": id},
            )
            
            # Trigger hooks
            await self.hooks.trigger("before_get_one", context)
            
            # Execute adapter method
            result = None
            if self.adapter:
                try:
                    result = await self.adapter.get_one(id)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in get_one: {str(e)}", exc_info=True)
                    raise
            
            # Return 404 if not found
            if result is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"{self.schema.__name__} with id {id} not found"
                )
            
            # Trigger hooks
            context.result = result
            await self.hooks.trigger("after_get_one", context)
            
            return result
        
        self.add_api_route(
            "/{id}",
            get_one,
            methods=["GET"],
            response_model=self.schema,
            summary=f"Get {self.schema.__name__} by ID",
            description=f"Retrieve a single {self.schema.__name__} item by its ID",
        )
    
    def _add_create_route(self) -> None:
        """Add POST create item route"""
        async def create(
            request: Request,
            data: self.create_schema = Body(..., description="Item data"),
        ) -> self.schema:
            """Create new item"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                data=data.model_dump() if hasattr(data, 'model_dump') else data.dict(),
            )
            
            # Trigger hooks
            await self.hooks.trigger("before_create", context)
            
            # Execute adapter method
            if self.adapter:
                result = await self.adapter.create(context.data)
            else:
                result = None
            
            # Trigger hooks
            context.result = result
            await self.hooks.trigger("after_create", context)
            
            return result
        
        self.add_api_route(
            "/",
            create,
            methods=["POST"],
            response_model=self.schema,
            status_code=201,
            summary=f"Create {self.schema.__name__}",
            description=f"Create a new {self.schema.__name__} item",
        )
    
    def _add_update_route(self) -> None:
        """Add PUT update item route"""
        async def update(
            request: Request,
            id: self.id_type = Path(..., description="Item ID"),
            data: self.update_schema = Body(..., description="Updated item data"),
        ) -> self.schema:
            """Update item"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                data=data.model_dump() if hasattr(data, 'model_dump') else data.dict(),
                metadata={"id": id},
            )
            
            # Trigger hooks
            await self.hooks.trigger("before_update", context)
            
            # Execute adapter method
            if self.adapter:
                result = await self.adapter.update(id, context.data)
            else:
                result = None
            
            # Trigger hooks
            context.result = result
            await self.hooks.trigger("after_update", context)
            
            return result
        
        self.add_api_route(
            "/{id}",
            update,
            methods=["PUT"],
            response_model=self.schema,
            summary=f"Update {self.schema.__name__}",
            description=f"Update an existing {self.schema.__name__} item",
        )
    
    def _add_delete_one_route(self) -> None:
        """Add DELETE single item route"""
        async def delete_one(
            request: Request,
            id: self.id_type = Path(..., description="Item ID"),
        ) -> self.schema:
            """Delete single item"""
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
                metadata={"id": id},
            )
            
            # Trigger hooks
            await self.hooks.trigger("before_delete", context)
            
            # Execute adapter method
            if self.adapter:
                result = await self.adapter.delete_one(id)
            else:
                result = None
            
            # Trigger hooks
            context.result = result
            await self.hooks.trigger("after_delete", context)
            
            return result
        
        self.add_api_route(
            "/{id}",
            delete_one,
            methods=["DELETE"],
            response_model=self.schema,
            summary=f"Delete {self.schema.__name__}",
            description=f"Delete a {self.schema.__name__} item by ID",
        )
    
    def _add_delete_all_route(self) -> None:
        """Add DELETE all items route"""
        from fastapi import HTTPException
        
        async def delete_all(
            request: Request,
        ) -> List[self.schema]:
            """Delete all items"""
            # Check if delete_all is enabled
            if not self.config.enable_delete_all:
                raise HTTPException(
                    status_code=403,
                    detail="Delete all operation is disabled for safety. Enable it in config if needed."
                )
            
            context = ExecutionContext(
                schema=self.schema,
                adapter=self.adapter,
                request=request,
            )
            
            # Trigger hooks
            await self.hooks.trigger("before_delete", context)
            
            # Execute adapter method
            result = []
            if self.adapter:
                try:
                    result = await self.adapter.delete_all()
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in delete_all: {str(e)}", exc_info=True)
                    raise
            
            # Trigger hooks
            context.result = result
            await self.hooks.trigger("after_delete", context)
            
            return result
        
        self.add_api_route(
            "/",
            delete_all,
            methods=["DELETE"],
            response_model=List[self.schema],
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
