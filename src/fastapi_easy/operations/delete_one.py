"""DeleteOne operation"""

from typing import Any
from ..core.operations import Operation
from ..core.hooks import ExecutionContext
from ..core.errors import NotFoundError


class DeleteOneOperation(Operation):
    """Delete single item operation
    
    Deletes a single item by ID.
    """
    
    name = "delete_one"
    method = "DELETE"
    path = "/{id}"
    
    async def before_execute(self, context: ExecutionContext) -> None:
        """Before delete one hook"""
        pass
    
    async def execute(self, context: ExecutionContext) -> Any:
        """Execute delete one operation
        
        Args:
            context: Execution context
            
        Returns:
            Deleted item
            
        Raises:
            NotFoundError: If item not found
        """
        item_id = context.metadata.get("id")
        
        # Check if item exists
        existing = await context.adapter.get_one(item_id)
        if existing is None:
            raise NotFoundError(context.schema.__name__, item_id)
        
        # Delete item
        item = await context.adapter.delete_one(item_id)
        return item
    
    async def after_execute(self, context: ExecutionContext) -> Any:
        """After delete one hook"""
        return context.result
