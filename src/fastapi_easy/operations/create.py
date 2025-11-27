"""Create operation"""

from typing import Any
from ..core.operations import Operation
from ..core.hooks import ExecutionContext


class CreateOperation(Operation):
    """Create new item operation
    
    Creates a new item from request data.
    """
    
    name = "create"
    method = "POST"
    path = ""
    
    async def before_execute(self, context: ExecutionContext) -> None:
        """Before create hook"""
        pass
    
    async def execute(self, context: ExecutionContext) -> Any:
        """Execute create operation
        
        Args:
            context: Execution context
            
        Returns:
            Created item
        """
        item = await context.adapter.create(context.data)
        return item
    
    async def after_execute(self, context: ExecutionContext) -> Any:
        """After create hook"""
        return context.result
