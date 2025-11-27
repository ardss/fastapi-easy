"""Update operation"""

from typing import Any
from ..core.operations import Operation
from ..core.hooks import ExecutionContext
from ..core.errors import NotFoundError


class UpdateOperation(Operation):
    """Update item operation
    
    Updates an existing item by ID.
    """
    
    name = "update"
    method = "PUT"
    path = "/{id}"
    
    async def before_execute(self, context: ExecutionContext) -> None:
        """Before update hook"""
        pass
    
    async def execute(self, context: ExecutionContext) -> Any:
        """Execute update operation
        
        Args:
            context: Execution context
            
        Returns:
            Updated item
            
        Raises:
            NotFoundError: If item not found
        """
        item_id = context.metadata.get("id")
        
        # Check if item exists
        existing = await context.adapter.get_one(item_id)
        if existing is None:
            raise NotFoundError(context.schema.__name__, item_id)
        
        # Update item
        item = await context.adapter.update(item_id, context.data)
        return item
    
    async def after_execute(self, context: ExecutionContext) -> Any:
        """After update hook"""
        return context.result
