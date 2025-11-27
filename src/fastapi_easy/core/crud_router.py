"""Main CRUD Router class for FastAPI-Easy"""

from typing import Type, Optional, List, Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

from .config import CRUDConfig
from .adapters import ORMAdapter
from .hooks import HookRegistry
from .operations import OperationRegistry


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
        **kwargs: Any,
    ):
        """Initialize CRUD Router
        
        Args:
            schema: Pydantic schema for the resource
            adapter: ORM adapter instance
            config: CRUD configuration
            prefix: API prefix (default: lowercase schema name)
            tags: OpenAPI tags
            **kwargs: Additional arguments passed to APIRouter
        """
        # Initialize configuration
        self.schema = schema
        self.adapter = adapter
        self.config = config or CRUDConfig()
        self.config.validate()
        
        # Initialize registries
        self.hooks = HookRegistry()
        self.operations = OperationRegistry()
        
        # Set default prefix
        if prefix is None:
            prefix = f"/{schema.__name__.lower()}"
        
        # Set default tags
        if tags is None:
            tags = [schema.__name__]
        
        # Initialize APIRouter
        super().__init__(prefix=prefix, tags=tags, **kwargs)
    
    def register_operation(self, operation: Any) -> None:
        """Register a custom operation
        
        Args:
            operation: Operation instance
        """
        self.operations.register(operation)
    
    def unregister_operation(self, name: str) -> None:
        """Unregister an operation
        
        Args:
            name: Operation name
        """
        self.operations.unregister(name)
    
    def get_operation(self, name: str) -> Optional[Any]:
        """Get operation by name
        
        Args:
            name: Operation name
            
        Returns:
            Operation or None
        """
        return self.operations.get(name)
    
    def get_all_operations(self) -> Dict[str, Any]:
        """Get all registered operations
        
        Returns:
            Dictionary of operations
        """
        return self.operations.get_all()
    
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
