"""Type definitions and protocols for FastAPI-Easy"""

from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, Union
from typing_extensions import TypeAlias

# Generic type variables
T = TypeVar("T")
ModelT = TypeVar("ModelT")
SchemaT = TypeVar("SchemaT")

# Type aliases
FilterDict: TypeAlias = Dict[str, Any]
SortDict: TypeAlias = Dict[str, str]
PaginationDict: TypeAlias = Dict[str, int]
HookCallback: TypeAlias = Callable[..., Any]
OperationHandler: TypeAlias = Callable[..., Any]

# Response types
ResponseData: TypeAlias = Union[Dict[str, Any], List[Dict[str, Any]], Any]
ErrorResponse: TypeAlias = Dict[str, Union[str, int, Dict[str, Any]]]

# Database operation types
CreateData: TypeAlias = Dict[str, Any]
UpdateData: TypeAlias = Dict[str, Any]
DeleteResult: TypeAlias = Dict[str, Any]

# Filter and query types
FilterValue: TypeAlias = Union[str, int, float, bool, List[Any], None]
SortValue: TypeAlias = str  # "field" or "-field"
SkipLimit: TypeAlias = tuple[int, int]  # (skip, limit)


class ORM(Protocol):
    """Protocol for ORM models"""
    
    id: Any
    
    def __init__(self, **kwargs: Any) -> None:
        """Initialize ORM model"""
        ...


class Adapter(Protocol):
    """Protocol for ORM adapters"""
    
    async def create(self, data: CreateData) -> Any:
        """Create a new record"""
        ...
    
    async def get_one(self, pk: Any) -> Optional[Any]:
        """Get a single record by primary key"""
        ...
    
    async def get_all(
        self,
        filters: Optional[FilterDict] = None,
        sorts: Optional[SortDict] = None,
        pagination: Optional[PaginationDict] = None,
    ) -> List[Any]:
        """Get multiple records"""
        ...
    
    async def update(self, pk: Any, data: UpdateData) -> Optional[Any]:
        """Update a record"""
        ...
    
    async def delete_one(self, pk: Any) -> Optional[Any]:
        """Delete a single record"""
        ...
    
    async def delete_all(self, filters: Optional[FilterDict] = None) -> int:
        """Delete multiple records"""
        ...
    
    async def count(self, filters: Optional[FilterDict] = None) -> int:
        """Count records"""
        ...


class Operation(Protocol):
    """Protocol for CRUD operations"""
    
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the operation"""
        ...


class Hook(Protocol):
    """Protocol for hooks"""
    
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute the hook"""
        ...


class Validator(Protocol):
    """Protocol for validators"""
    
    def validate(self, value: Any) -> Any:
        """Validate a value"""
        ...


class Formatter(Protocol):
    """Protocol for response formatters"""
    
    def format(self, data: ResponseData) -> Any:
        """Format response data"""
        ...


class Cache(Protocol):
    """Protocol for cache backends"""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        ...
    
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        ...
    
    async def clear(self) -> None:
        """Clear all cache"""
        ...


class Logger(Protocol):
    """Protocol for loggers"""
    
    def debug(self, message: str, extra_fields: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message"""
        ...
    
    def info(self, message: str, extra_fields: Optional[Dict[str, Any]] = None) -> None:
        """Log info message"""
        ...
    
    def warning(self, message: str, extra_fields: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message"""
        ...
    
    def error(
        self,
        message: str,
        extra_fields: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        """Log error message"""
        ...


class PermissionChecker(Protocol):
    """Protocol for permission checkers"""
    
    def check_permission(self, context: Dict[str, Any], permission: str) -> None:
        """Check if permission is granted"""
        ...


class AuditLogger(Protocol):
    """Protocol for audit loggers"""
    
    def log(
        self,
        entity_type: str,
        entity_id: Any,
        action: str,
        user_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log an audit event"""
        ...
