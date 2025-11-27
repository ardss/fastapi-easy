"""Base ORM adapter implementation"""

from typing import Any, Dict, List, Optional
from ..core.adapters import ORMAdapter


class BaseORMAdapter(ORMAdapter):
    """Base ORM adapter with default implementations
    
    Provides basic implementations that can be overridden by specific ORM adapters.
    """
    
    def __init__(self, model: Any, session_factory: Any):
        """Initialize base adapter
        
        Args:
            model: ORM model class
            session_factory: Session factory function
        """
        self.model = model
        self.session_factory = session_factory
    
    async def get_all(
        self,
        filters: Dict[str, Any],
        sorts: Dict[str, Any],
        pagination: Dict[str, Any],
    ) -> List[Any]:
        """Get all items - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_all()")
    
    async def get_one(self, id: Any) -> Optional[Any]:
        """Get single item - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_one()")
    
    async def create(self, data: Dict[str, Any]) -> Any:
        """Create new item - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement create()")
    
    async def update(self, id: Any, data: Dict[str, Any]) -> Any:
        """Update item - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement update()")
    
    async def delete_one(self, id: Any) -> Any:
        """Delete single item - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement delete_one()")
    
    async def delete_all(self) -> List[Any]:
        """Delete all items - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement delete_all()")
    
    async def count(self, filters: Dict[str, Any]) -> int:
        """Count items - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement count()")
