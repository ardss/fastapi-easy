"""DeleteAll operation"""

from typing import Any, List
from ..core.operations import Operation
from ..core.hooks import ExecutionContext


class DeleteAllOperation(Operation):
    """Delete all items operation
    
    Deletes all items (with optional filters).
    """
    
    name = "delete_all"
    method = "DELETE"
    path = ""
    
    async def before_execute(self, context: ExecutionContext) -> None:
        """Before delete all hook"""
        pass
    
    async def execute(self, context: ExecutionContext) -> List[Any]:
        """Execute delete all operation
        
        Args:
            context: Execution context
            
        Returns:
            List of deleted items
        """
        items = await context.adapter.delete_all()
        return items
    
    async def after_execute(self, context: ExecutionContext) -> List[Any]:
        """After delete all hook"""
        return context.result
