"""GetOne operation"""

from typing import Any
from ..core.operations import Operation
from ..core.hooks import ExecutionContext
from ..core.errors import NotFoundError


class GetOneOperation(Operation):
    """Get single item operation
    
    Retrieves a single item by ID.
    """
    
    name = "get_one"
    method = "GET"
    path = "/{id}"
    
    async def before_execute(self, context: ExecutionContext) -> None:
        """Before get one hook"""
        pass
    
    async def execute(self, context: ExecutionContext) -> Any:
        """Execute get one operation
        
        Args:
            context: Execution context
            
        Returns:
            Single item
            
        Raises:
            NotFoundError: If item not found
        """
        item_id = context.metadata.get("id")
        item = await context.adapter.get_one(item_id)
        
        if item is None:
            raise NotFoundError(context.schema.__name__, item_id)
        
        return item
    
    async def after_execute(self, context: ExecutionContext) -> Any:
        """After get one hook"""
        return context.result
