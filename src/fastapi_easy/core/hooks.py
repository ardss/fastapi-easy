"""Hook system for FastAPI-Easy"""

from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ExecutionContext:
    """Execution context for operations
    
    Contains all information needed for operation execution.
    """
    
    schema: Any  # Pydantic schema
    adapter: Any  # ORM adapter
    request: Any  # FastAPI request
    user: Any = None  # Current user
    filters: Dict[str, Any] = field(default_factory=dict)
    sorts: Dict[str, Any] = field(default_factory=dict)
    pagination: Dict[str, Any] = field(default_factory=dict)
    data: Any = None  # Request data
    result: Any = None  # Operation result
    metadata: Dict[str, Any] = field(default_factory=dict)


class HookRegistry:
    """Hook registry for managing operation hooks
    
    Supports registering and triggering hooks for various events.
    """
    
    # Supported hook events
    HOOK_EVENTS = {
        "before_create": "Before create operation",
        "after_create": "After create operation",
        "before_update": "Before update operation",
        "after_update": "After update operation",
        "before_delete": "Before delete operation",
        "after_delete": "After delete operation",
        "before_get_all": "Before get all operation",
        "after_get_all": "After get all operation",
        "before_get_one": "Before get one operation",
        "after_get_one": "After get one operation",
    }
    
    def __init__(self):
        """Initialize hook registry"""
        self.hooks: Dict[str, List[Callable]] = {}
    
    def register(self, event: str, callback: Callable) -> None:
        """Register a hook callback
        
        Args:
            event: Hook event name
            callback: Callback function
            
        Raises:
            ValueError: If event is not supported
        """
        if event not in self.HOOK_EVENTS:
            raise ValueError(f"Unsupported hook event: {event}")
        
        if event not in self.hooks:
            self.hooks[event] = []
        
        self.hooks[event].append(callback)
    
    def unregister(self, event: str, callback: Callable) -> None:
        """Unregister a hook callback
        
        Args:
            event: Hook event name
            callback: Callback function
        """
        if event in self.hooks and callback in self.hooks[event]:
            self.hooks[event].remove(callback)
    
    async def trigger(self, event: str, context: ExecutionContext) -> None:
        """Trigger all hooks for an event
        
        Args:
            event: Hook event name
            context: Execution context
        """
        if event not in self.hooks:
            return
        
        for callback in self.hooks[event]:
            if callable(callback):
                # Support both async and sync callbacks
                if hasattr(callback, "__await__"):
                    await callback(context)
                else:
                    result = callback(context)
                    # If callback returns a coroutine, await it
                    if hasattr(result, "__await__"):
                        await result
    
    def get_hooks(self, event: str) -> List[Callable]:
        """Get all hooks for an event
        
        Args:
            event: Hook event name
            
        Returns:
            List of callbacks
        """
        return self.hooks.get(event, [])
    
    def get_all(self) -> Dict[str, List[Callable]]:
        """Get all hooks
        
        Returns:
            Dictionary of all hooks
        """
        return self.hooks.copy()
    
    def clear(self, event: Optional[str] = None) -> None:
        """Clear hooks
        
        Args:
            event: Specific event to clear, or None to clear all
        """
        if event is None:
            self.hooks.clear()
        elif event in self.hooks:
            self.hooks[event].clear()


# Type alias for hook callback
HookCallback = Callable[[ExecutionContext], Any]
