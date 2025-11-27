"""Operation system for FastAPI-Easy"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Callable, Optional
from .hooks import ExecutionContext


class Operation(ABC):
    """Base operation class
    
    All operations should inherit from this class and implement
    the abstract methods.
    """
    
    name: str
    method: str  # GET, POST, PUT, DELETE
    path: str
    
    @abstractmethod
    async def before_execute(self, context: ExecutionContext) -> None:
        """Hook before operation execution
        
        Args:
            context: Execution context
        """
        pass
    
    @abstractmethod
    async def execute(self, context: ExecutionContext) -> Any:
        """Execute the operation
        
        Args:
            context: Execution context
            
        Returns:
            Operation result
        """
        pass
    
    @abstractmethod
    async def after_execute(self, context: ExecutionContext) -> Any:
        """Hook after operation execution
        
        Args:
            context: Execution context
            
        Returns:
            Processed result
        """
        pass


class OperationRegistry:
    """Registry for managing operations
    
    Manages registration, retrieval, and execution of operations.
    """
    
    def __init__(self):
        """Initialize operation registry"""
        self.operations: Dict[str, Operation] = {}
    
    def register(self, operation: Operation) -> None:
        """Register an operation
        
        Args:
            operation: Operation instance
        """
        self.operations[operation.name] = operation
    
    def unregister(self, name: str) -> None:
        """Unregister an operation
        
        Args:
            name: Operation name
        """
        if name in self.operations:
            del self.operations[name]
    
    def get(self, name: str) -> Optional[Operation]:
        """Get operation by name
        
        Args:
            name: Operation name
            
        Returns:
            Operation or None if not found
        """
        return self.operations.get(name)
    
    def get_all(self) -> Dict[str, Operation]:
        """Get all operations
        
        Returns:
            Dictionary of all operations
        """
        return self.operations.copy()
    
    async def execute(
        self,
        name: str,
        context: ExecutionContext,
    ) -> Any:
        """Execute an operation
        
        Args:
            name: Operation name
            context: Execution context
            
        Returns:
            Operation result
            
        Raises:
            ValueError: If operation not found
        """
        operation = self.get(name)
        if not operation:
            raise ValueError(f"Operation '{name}' not found")
        
        # Execute operation with hooks
        await operation.before_execute(context)
        result = await operation.execute(context)
        context.result = result
        result = await operation.after_execute(context)
        
        return result
