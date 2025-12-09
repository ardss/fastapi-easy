"""Core module unified interface definitions.

Defines clear service interfaces to achieve loose coupling between modules.
Follows the Dependency Inversion Principle - high-level modules don't depend
on low-level module implementations.

This module provides the foundation for the FastAPI-Easy framework's
architecture, defining contracts for repositories, services, caches,
events, and more. Each interface is designed to be generic and extensible,
supporting multiple implementations while maintaining consistency.

Example:
    ```python
    class UserRepository(IRepository[User]):
        async def get_by_id(self, id: int) -> Optional[User]:
            # Implementation
            pass

    # Usage with dependency injection
    repo = UserRepository()
    user = await repo.get_by_id(1)
    ```
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class QueryOperator(Enum):
    """Query operators for filtering data.

    These operators define how values should be compared in filter conditions.
    They map directly to database query operations and are used throughout
    the framework for consistent filtering semantics.

    Attributes:
        EQ: Equality comparison (=)
        NE: Not equal comparison (!=)
        GT: Greater than (>)
        GTE: Greater than or equal (>=)
        LT: Less than (<)
        LTE: Less than or equal (<=)
        IN: Value in list (IN)
        NIN: Value not in list (NOT IN)
        LIKE: Pattern matching with wildcards (LIKE)
        ILIKE: Case-insensitive pattern matching (ILIKE)
        IS_NULL: Check if value is NULL
        IS_NOT_NULL: Check if value is not NULL
    """

    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    IN = "in"
    NIN = "nin"
    LIKE = "like"
    ILIKE = "ilike"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class SortDirection(Enum):
    """Sorting direction for query results.

    Defines the order in which records should be returned when sorting
    by a specific field.

    Attributes:
        ASC: Ascending order (A-Z, 0-9)
        DESC: Descending order (Z-A, 9-0)
    """

    ASC = "asc"
    DESC = "desc"


@dataclass
class QueryFilter:
    """Query filter for data filtering operations.

    Represents a single filter condition that can be applied to queries.
    Each filter combines a field name, an operator, and a value to compare
    against.

    Attributes:
        field: The field name to filter on
        operator: The comparison operator to use
        value: The value to compare against

    Example:
        ```python
        # Find users with name "John"
        filter1 = QueryFilter(field="name", operator=QueryOperator.EQ, value="John")

        # Find users older than 30
        filter2 = QueryFilter(field="age", operator=QueryOperator.GT, value=30)

        # Find users in specific cities
        filter3 = QueryFilter(field="city", operator=QueryOperator.IN,
                             value=["New York", "London"])
        ```
    """

    field: str
    operator: QueryOperator
    value: Any

    def to_dict(self) -> dict[str, Any]:
        """Convert filter to dictionary representation.

        Returns:
            Dictionary with field, operator, and value keys
        """
        return {"field": self.field, "operator": self.operator.value, "value": self.value}


@dataclass
class QuerySort:
    """Query sorting configuration.

    Defines how query results should be sorted by specifying a field
    and sorting direction.

    Attributes:
        field: Field name to sort by
        direction: Sort direction (ascending or descending)

    Example:
        ```python
        # Sort by name in ascending order
        sort1 = QuerySort(field="name")

        # Sort by age in descending order
        sort2 = QuerySort(field="age", direction=SortDirection.DESC)
        ```
    """

    field: str
    direction: SortDirection = SortDirection.ASC

    def to_dict(self) -> dict[str, Any]:
        """Convert sort to dictionary representation.

        Returns:
            Dictionary with field and direction keys
        """
        return {"field": self.field, "direction": self.direction.value}


@dataclass
class QueryPagination:
    """Query pagination configuration.

    Controls which subset of results to return by specifying skip and limit
    values. Provides helper properties for page-based navigation.

    Attributes:
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 10)

    Raises:
        ValueError: If skip is negative or limit is not positive

    Example:
        ```python
        # Get first page with 20 items
        page1 = QueryPagination(skip=0, limit=20)

        # Get second page with 20 items
        page2 = QueryPagination(skip=20, limit=20)

        # Calculate page number
        print(f"Current page: {page2.page}")  # Output: 2
        ```
    """

    skip: int = 0
    limit: int = 10

    def __post_init__(self) -> None:
        """Validate pagination parameters."""
        if self.skip < 0:
            raise ValueError("Skip must be non-negative")
        if self.limit <= 0:
            raise ValueError("Limit must be positive")

    @property
    def page(self) -> int:
        """Current page number (1-based index).

        Returns:
            The page number corresponding to the current skip/limit values
        """
        return (self.skip // self.limit) + 1

    @property
    def total_pages(self, total: int) -> int:
        """Calculate total pages needed for given total records.

        Args:
            total: Total number of records

        Returns:
            Total number of pages required
        """
        return (total + self.limit - 1) // self.limit


@dataclass
class QueryOptions:
    """Comprehensive query configuration options.

    Combines filtering, sorting, pagination, and field selection into
    a single configuration object for database queries.

    Attributes:
        filters: List of filter conditions (default: empty list)
        sorts: List of sort configurations (default: empty list)
        pagination: Pagination settings (optional)
        fields: List of fields to include in projection (optional)
        include_total: Whether to include total count in results

    Example:
        ```python
        # Complex query with filters, sorting, and pagination
        options = QueryOptions(
            filters=[
                QueryFilter(field="status", operator=QueryOperator.EQ, value="active"),
                QueryFilter(field="age", operator=QueryOperator.GT, value=18)
            ],
            sorts=[QuerySort(field="created_at", direction=SortDirection.DESC)],
            pagination=QueryPagination(skip=0, limit=10),
            fields=["id", "name", "email", "created_at"],
            include_total=True
        )
        ```
    """

    filters: list[QueryFilter] | None = None
    sorts: list[QuerySort] | None = None
    pagination: QueryPagination | None = None
    fields: list[str] | None = None  # Field projection
    include_total: bool = False

    def __post_init__(self) -> None:
        """Initialize default values for optional fields."""
        if self.filters is None:
            self.filters = []
        if self.sorts is None:
            self.sorts = []


@dataclass
class QueryResult(Generic[T]):
    """Container for query results with pagination metadata.

    Wraps query results with additional metadata about pagination,
    total counts, and whether more results are available.

    Attributes:
        items: List of query results
        total: Total number of records matching query (optional)
        has_more: Whether more records are available
        page: Current page number (optional)
        total_pages: Total number of pages (optional)

    Example:
        ```python
        # Create a paginated result
        result = QueryResult[User](
            items=[user1, user2, user3],
            total=100,
            has_more=True,
            page=1,
            total_pages=10
        )

        print(f"Showing {result.count} of {result.total} users")
        print(f"Page {result.page} of {result.total_pages}")
        ```
    """

    items: list[T]
    total: int | None = None
    has_more: bool = False
    page: int | None = None
    total_pages: int | None = None

    @property
    def count(self) -> int:
        """Number of items in the result.

        Returns:
            The count of items in the items list
        """
        return len(self.items)


# Repository interfaces
class IRepository(ABC, Generic[T]):
    """Generic repository interface for data access operations.

    Provides a standardized interface for CRUD (Create, Read, Update, Delete)
    operations and advanced querying capabilities. This interface abstracts
    the underlying data storage mechanism, allowing different implementations
    (SQL, NoSQL, in-memory, etc.) while maintaining consistent behavior.

    Type Parameters:
        T: The entity type this repository manages

    Example:
        ```python
        class UserRepository(IRepository[User]):
            async def get_by_id(self, id: int) -> Optional[User]:
                # SQL implementation
                return await self.db.query(User).filter(User.id == id).first()

        # Usage
        repo = UserRepository()
        user = await repo.get_by_id(1)
        ```
    """

    @abstractmethod
    async def get_by_id(self, id: ID) -> T | None:
        """Retrieve an entity by its unique identifier.

        Args:
            id: The unique identifier of the entity

        Returns:
            The entity if found, None otherwise

        Example:
            ```python
            user = await repository.get_by_id(123)
            if user:
                print(f"Found user: {user.name}")
            ```
        """
        pass

    @abstractmethod
    async def get_one(self, options: QueryOptions) -> T | None:
        """Retrieve a single entity based on query options.

        Args:
            options: Query configuration including filters, sorts, etc.

        Returns:
            The first matching entity if found, None otherwise

        Example:
            ```python
            options = QueryOptions(
                filters=[QueryFilter(field="email", operator=QueryOperator.EQ,
                                   value="user@example.com")]
            )
            user = await repository.get_one(options)
            ```
        """
        pass

    @abstractmethod
    async def get_many(self, options: QueryOptions) -> QueryResult[T]:
        """Retrieve multiple entities based on query options.

        Args:
            options: Query configuration including filters, sorts, pagination

        Returns:
            QueryResult containing matching entities and metadata

        Example:
            ```python
            options = QueryOptions(
                filters=[QueryFilter(field="status", operator=QueryOperator.EQ,
                                   value="active")],
                pagination=QueryPagination(skip=0, limit=10),
                include_total=True
            )
            result = await repository.get_many(options)
            print(f"Found {result.total} active users")
            ```
        """
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: The entity to create

        Returns:
            The created entity (possibly with generated fields like ID)

        Example:
            ```python
            user = User(name="John", email="john@example.com")
            created_user = await repository.create(user)
            print(f"Created user with ID: {created_user.id}")
            ```
        """
        pass

    @abstractmethod
    async def create_many(self, entities: list[T]) -> list[T]:
        """Create multiple entities in a single operation.

        Args:
            entities: List of entities to create

        Returns:
            List of created entities (possibly with generated fields)

        Example:
            ```python
            users = [
                User(name="John", email="john@example.com"),
                User(name="Jane", email="jane@example.com"),
            ]
            created_users = await repository.create_many(users)
            ```
        """
        pass

    @abstractmethod
    async def update(self, id: ID, updates: dict[str, Any]) -> T | None:
        """Update an entity by ID.

        Args:
            id: The unique identifier of the entity to update
            updates: Dictionary of fields to update and their new values

        Returns:
            The updated entity if found and updated, None otherwise

        Example:
            ```python
            updates = {"name": "John Doe", "status": "active"}
            updated_user = await repository.update(123, updates)
            ```
        """
        pass

    @abstractmethod
    async def update_many(
        self, updates: dict[str, Any], options: QueryOptions | None = None
    ) -> int:
        """Update multiple entities based on filter criteria.

        Args:
            updates: Dictionary of fields to update and their new values
            options: Query options to filter which entities to update

        Returns:
            Number of entities that were updated

        Example:
            ```python
            updates = {"status": "inactive"}
            options = QueryOptions(
                filters=[QueryFilter(field="last_login", operator=QueryOperator.LT,
                                   value=datetime.now() - timedelta(days=30))]
            )
            count = await repository.update_many(updates, options)
            print(f"Deactivated {count} inactive users")
            ```
        """
        pass

    @abstractmethod
    async def delete(self, id: ID) -> bool:
        """Delete an entity by ID.

        Args:
            id: The unique identifier of the entity to delete

        Returns:
            True if the entity was deleted, False if not found

        Example:
            ```python
            deleted = await repository.delete(123)
            if deleted:
                print("User deleted successfully")
            else:
                print("User not found")
            ```
        """
        pass

    @abstractmethod
    async def delete_many(self, options: QueryOptions) -> int:
        """Delete multiple entities based on filter criteria.

        Args:
            options: Query options to filter which entities to delete

        Returns:
            Number of entities that were deleted

        Example:
            ```python
            options = QueryOptions(
                filters=[QueryFilter(field="status", operator=QueryOperator.EQ,
                                   value="deleted")]
            )
            count = await repository.delete_many(options)
            print(f"Permanently deleted {count} records")
            ```
        """
        pass

    @abstractmethod
    async def count(self, options: QueryOptions) -> int:
        """Count entities matching the given criteria.

        Args:
            options: Query options to filter which entities to count

        Returns:
            The number of matching entities

        Example:
            ```python
            options = QueryOptions(
                filters=[QueryFilter(field="status", operator=QueryOperator.EQ,
                                   value="active")]
            )
            active_count = await repository.count(options)
            print(f"Active users: {active_count}")
            ```
        """
        pass

    @abstractmethod
    async def exists(self, options: QueryOptions) -> bool:
        """Check if any entities match the given criteria.

        More efficient than count() when you only need to know existence.

        Args:
            options: Query options to filter entities

        Returns:
            True if at least one matching entity exists, False otherwise

        Example:
            ```python
            options = QueryOptions(
                filters=[QueryFilter(field="email", operator=QueryOperator.EQ,
                                   value="admin@example.com")]
            )
            if await repository.exists(options):
                print("Admin user exists")
            ```
        """
        pass


class ICacheService(ABC):
    """Generic cache service interface.

    Provides a standardized interface for caching operations with support
    for TTL (Time To Live), pattern-based clearing, and existence checks.
    This interface abstracts the underlying caching mechanism (Redis,
    Memcached, in-memory, etc.) while maintaining consistent behavior.

    Example:
        ```python
        class RedisCacheService(ICacheService):
            async def get(self, key: str) -> Optional[Any]:
                return await self.redis.get(key)

        # Usage
        cache = RedisCacheService()
        await cache.set("user:123", user_data, ttl=3600)
        user = await cache.get("user:123")
        ```
    """

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """Retrieve a value from cache.

        Args:
            key: The cache key

        Returns:
            The cached value if found, None otherwise

        Example:
            ```python
            user_data = await cache.get(f"user:{user_id}")
            if user_data:
                return User(**user_data)
            ```
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in cache.

        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live in seconds (optional)

        Example:
            ```python
            # Cache for 1 hour
            await cache.set("session:abc123", session_data, ttl=3600)

            # Cache indefinitely
            await cache.set("config:app", config_data)
            ```
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Remove a value from cache.

        Args:
            key: The cache key to delete

        Returns:
            True if the key was deleted, False if it didn't exist

        Example:
            ```python
            if await cache.delete(f"user:{user_id}"):
                print("User cache cleared")
            ```
        """
        pass

    @abstractmethod
    async def clear(self, pattern: str | None = None) -> int:
        """Clear cache entries.

        Args:
            pattern: Pattern to match keys (optional). If None, clears all.

        Returns:
            Number of keys that were cleared

        Example:
            ```python
            # Clear all user cache entries
            await cache.clear("user:*")

            # Clear all cache
            await cache.clear()
            ```
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists in cache.

        Args:
            key: The cache key to check

        Returns:
            True if the key exists, False otherwise

        Example:
            ```python
            if not await cache.exists(f"stats:{date}"):
                await generate_daily_stats(date)
            ```
        """
        pass


class IEventBus(ABC):
    """Event bus interface for pub-sub communication.

    Provides a decoupled way for components to communicate through events.
    Components can publish events without knowing who subscribes to them,
    and subscribers can react to events without knowing the publisher.

    Example:
        ```python
        # Publisher
        await event_bus.publish("user.created", {"user_id": 123})

        # Subscriber
        async def handle_user_created(data):
            await send_welcome_email(data["user_id"])

        await event_bus.subscribe("user.created", handle_user_created)
        ```
    """

    @abstractmethod
    async def publish(self, event_name: str, data: Any, **kwargs) -> None:
        """Publish an event to all subscribers.

        Args:
            event_name: Name of the event
            data: Event payload data
            **kwargs: Additional event metadata

        Example:
            ```python
            await event_bus.publish(
                "order.placed",
                {"order_id": 123, "amount": 99.99},
                user_id=user.id,
                timestamp=datetime.now().isoformat()
            )
            ```
        """
        pass

    @abstractmethod
    async def subscribe(self, event_name: str, handler: Callable[..., Any], **kwargs) -> str:
        """Subscribe to an event with a handler function.

        Args:
            event_name: Name of the event to subscribe to
            handler: Function to handle the event
            **kwargs: Additional subscription options

        Returns:
            Subscription ID that can be used to unsubscribe

        Example:
            ```python
            async def handle_order_placed(data, user_id=None):
                print(f"Order {data['order_id']} placed by user {user_id}")

            sub_id = await event_bus.subscribe(
                "order.placed",
                handle_order_placed,
                priority="high"
            )
            ```
        """
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from an event.

        Args:
            subscription_id: The subscription ID returned by subscribe()

        Returns:
            True if unsubscribed successfully, False otherwise

        Example:
            ```python
            if await event_bus.unsubscribe(subscription_id):
                print("Successfully unsubscribed")
            ```
        """
        pass


class ILogger(ABC):
    """日志接口"""

    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        """调试日志"""
        pass

    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        """信息日志"""
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        """警告日志"""
        pass

    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        """错误日志"""
        pass

    @abstractmethod
    def critical(self, message: str, **kwargs: Any) -> None:
        """严重错误日志"""
        pass


class IValidator(ABC):
    """验证器接口"""

    @abstractmethod
    async def validate(self, value: Any, rules: Dict[str, Any]) -> bool:
        """验证值"""
        pass

    @abstractmethod
    async def validate_entity(self, entity: Any) -> List[str]:
        """验证实体"""
        pass


class IMapper(ABC):
    """对象映射接口"""

    @abstractmethod
    def map(self, source: Any, target_type: Type[T]) -> T:
        """映射对象"""
        pass

    @abstractmethod
    def map_collection(self, sources: List[Any], target_type: Type[T]) -> List[T]:
        """映射对象集合"""
        pass


class IHook(ABC):
    """钩子接口"""

    @abstractmethod
    async def before_execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """执行前钩子"""
        pass

    @abstractmethod
    async def after_execute(self, context: Dict[str, Any], result: Any) -> Any:
        """执行后钩子"""
        pass

    @abstractmethod
    async def on_error(self, context: Dict[str, Any], error: Exception) -> Optional[Exception]:
        """错误处理钩子"""
        pass


class IHookRegistry(ABC):
    """钩子注册表接口"""

    @abstractmethod
    def register_hook(self, event_name: str, hook: IHook, priority: int = 0) -> None:
        """注册钩子"""
        pass

    @abstractmethod
    def unregister_hook(self, event_name: str, hook_id: str) -> bool:
        """取消注册钩子"""
        pass

    @abstractmethod
    async def execute_hooks(self, event_name: str, context: Dict[str, Any]) -> Any:
        """执行钩子"""
        pass


class IUnitOfWork(ABC):
    """工作单元接口"""

    @abstractmethod
    async def __aenter__(self) -> IUnitOfWork:
        """进入工作单元"""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """退出工作单元"""
        pass

    @abstractmethod
    async def commit(self) -> None:
        """提交事务"""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """回滚事务"""
        pass

    @abstractmethod
    def get_repository(self, entity_type: Type[T]) -> IRepository[T]:
        """获取仓储"""
        pass


class IService(ABC):
    """服务接口"""

    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""
        pass

    @abstractmethod
    async def dispose(self) -> None:
        """释放服务资源"""
        pass

    @property
    @abstractmethod
    def is_healthy(self) -> bool:
        """检查服务健康状态"""
        pass


class ICommandHandler(ABC, Generic[T]):
    """命令处理器接口"""

    @abstractmethod
    async def handle(self, command: Any) -> Any:
        """处理命令"""
        pass


class IQueryHandler(ABC, Generic[T]):
    """查询处理器接口"""

    @abstractmethod
    async def handle(self, query: Any) -> Any:
        """处理查询"""
        pass


class IMiddleware(ABC):
    """中间件接口"""

    @abstractmethod
    async def process(self, request: Any, next_handler: Callable[..., Any]) -> Any:
        """处理请求"""
        pass


class IPlugin(ABC):
    """插件接口"""

    @abstractmethod
    def get_name(self) -> str:
        """获取插件名称"""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """获取插件版本"""
        pass

    @abstractmethod
    async def initialize(self, context: Dict[str, Any]) -> None:
        """初始化插件"""
        pass

    @abstractmethod
    async def dispose(self) -> None:
        """释放插件资源"""
        pass

    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """获取插件依赖"""
        pass


class IPluginManager(ABC):
    """插件管理器接口"""

    @abstractmethod
    async def load_plugin(self, plugin_path: str) -> bool:
        """加载插件"""
        pass

    @abstractmethod
    async def unload_plugin(self, plugin_name: str) -> bool:
        """卸载插件"""
        pass

    @abstractmethod
    def get_loaded_plugins(self) -> List[IPlugin]:
        """获取已加载的插件"""
        pass

    @abstractmethod
    def get_plugin(self, name: str) -> Optional[IPlugin]:
        """获取插件"""
        pass
