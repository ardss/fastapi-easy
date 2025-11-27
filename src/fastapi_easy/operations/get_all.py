"""GetAll operation"""

from typing import Any, Dict, List
from ..core.operations import Operation
from ..core.hooks import ExecutionContext


class GetAllOperation(Operation):
    """Get all items operation
    
    Retrieves all items with optional filtering, sorting, and pagination.
    """
    
    name = "get_all"
    method = "GET"
    path = ""
    
    async def before_execute(self, context: ExecutionContext) -> None:
        """Before get all hook"""
        pass
    
    async def execute(self, context: ExecutionContext) -> List[Any]:
        """Execute get all operation
        
        Args:
            context: Execution context
            
        Returns:
            List of items
        """
        items = await context.adapter.get_all(
            filters=context.filters,
            sorts=context.sorts,
            pagination=context.pagination,
        )
        return items
    
    async def after_execute(self, context: ExecutionContext) -> List[Any]:
        """After get all hook"""
        return context.result
