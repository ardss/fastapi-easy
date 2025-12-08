"""
核心模块统一接口定义

定义清晰的服务接口，实现模块间的松耦合。
遵循依赖倒置原则，高层模块不依赖低层模块的具体实现。
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union, AsyncIterator
from dataclasses import dataclass
from enum import Enum
import asyncio

from .exceptions import BaseException

T = TypeVar('T')
ID = TypeVar('ID')


class QueryOperator(Enum):
    """查询操作符"""
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
    """排序方向"""
    ASC = "asc"
    DESC = "desc"


@dataclass
class QueryFilter:
    """查询过滤器"""
    field: str
    operator: QueryOperator
    value: Any

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value
        }


@dataclass
class QuerySort:
    """查询排序"""
    field: str
    direction: SortDirection = SortDirection.ASC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "direction": self.direction.value
        }


@dataclass
class QueryPagination:
    """查询分页"""
    skip: int = 0
    limit: int = 10

    def __post_init__(self):
        if self.skip < 0:
            raise ValueError("Skip must be non-negative")
        if self.limit <= 0:
            raise ValueError("Limit must be positive")

    @property
    def page(self) -> int:
        """页码（从1开始）"""
        return (self.skip // self.limit) + 1

    @property
    def total_pages(self, total: int) -> int:
        """总页数"""
        return (total + self.limit - 1) // self.limit


@dataclass
class QueryOptions:
    """查询选项"""
    filters: List[QueryFilter] = None
    sorts: List[QuerySort] = None
    pagination: Optional[QueryPagination] = None
    fields: Optional[List[str]] = None  # 字段投影
    include_total: bool = False

    def __post_init__(self):
        if self.filters is None:
            self.filters = []
        if self.sorts is None:
            self.sorts = []


@dataclass
class QueryResult:
    """查询结果"""
    items: List[T]
    total: Optional[int] = None
    has_more: bool = False
    page: Optional[int] = None
    total_pages: Optional[int] = None

    @property
    def count(self) -> int:
        """项目数量"""
        return len(self.items)


# 基础服务接口
class IRepository(ABC, Type[T]):
    """仓储接口

    提供数据访问的抽象层，隐藏具体的数据访问细节。
    """

    @abstractmethod
    async def get_by_id(self, id: ID) -> Optional[T]:
        """根据ID获取实体"""
        pass

    @abstractmethod
    async def get_one(self, options: QueryOptions) -> Optional[T]:
        """获取单个实体"""
        pass

    @abstractmethod
    async def get_many(self, options: QueryOptions) -> QueryResult[T]:
        """获取多个实体"""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建实体"""
        pass

    @abstractmethod
    async def create_many(self, entities: List[T]) -> List[T]:
        """批量创建实体"""
        pass

    @abstractmethod
    async def update(self, id: ID, updates: Dict[str, Any]) -> Optional[T]:
        """更新实体"""
        pass

    @abstractmethod
    async def update_many(
        self,
        updates: Dict[str, Any],
        options: Optional[QueryOptions] = None
    ) -> int:
        """批量更新实体"""
        pass

    @abstractmethod
    async def delete(self, id: ID) -> bool:
        """删除实体"""
        pass

    @abstractmethod
    async def delete_many(self, options: QueryOptions) -> int:
        """批量删除实体"""
        pass

    @abstractmethod
    async def count(self, options: QueryOptions) -> int:
        """统计实体数量"""
        pass

    @abstractmethod
    async def exists(self, options: QueryOptions) -> bool:
        """检查实体是否存在"""
        pass


class ICacheService(ABC):
    """缓存服务接口"""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> int:
        """清空缓存"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass


class IEventBus(ABC):
    """事件总线接口"""

    @abstractmethod
    async def publish(self, event_name: str, data: Any, **kwargs) -> None:
        """发布事件"""
        pass

    @abstractmethod
    async def subscribe(
        self,
        event_name: str,
        handler: callable,
        **kwargs
    ) -> str:
        """订阅事件"""
        pass

    @abstractmethod
    async def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅"""
        pass


class ILogger(ABC):
    """日志接口"""

    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """调试日志"""
        pass

    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """信息日志"""
        pass

    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """警告日志"""
        pass

    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """错误日志"""
        pass

    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
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
    def map_collection(
        self,
        sources: List[Any],
        target_type: Type[T]
    ) -> List[T]:
        """映射对象集合"""
        pass


class IHook(ABC):
    """钩子接口"""

    @abstractmethod
    async def before_execute(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """执行前钩子"""
        pass

    @abstractmethod
    async def after_execute(
        self,
        context: Dict[str, Any],
        result: Any
    ) -> Any:
        """执行后钩子"""
        pass

    @abstractmethod
    async def on_error(
        self,
        context: Dict[str, Any],
        error: Exception
    ) -> Optional[Exception]:
        """错误处理钩子"""
        pass


class IHookRegistry(ABC):
    """钩子注册表接口"""

    @abstractmethod
    def register_hook(
        self,
        event_name: str,
        hook: IHook,
        priority: int = 0
    ) -> None:
        """注册钩子"""
        pass

    @abstractmethod
    def unregister_hook(self, event_name: str, hook_id: str) -> bool:
        """取消注册钩子"""
        pass

    @abstractmethod
    async def execute_hooks(
        self,
        event_name: str,
        context: Dict[str, Any]
    ) -> Any:
        """执行钩子"""
        pass


class IUnitOfWork(ABC):
    """工作单元接口"""

    @abstractmethod
    async def __aenter__(self) -> 'IUnitOfWork':
        """进入工作单元"""
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
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


class ICommandHandler(ABC, Type[T]):
    """命令处理器接口"""

    @abstractmethod
    async def handle(self, command: Any) -> Any:
        """处理命令"""
        pass


class IQueryHandler(ABC, Type[T]):
    """查询处理器接口"""

    @abstractmethod
    async def handle(self, query: Any) -> Any:
        """处理查询"""
        pass


class IMiddleware(ABC):
    """中间件接口"""

    @abstractmethod
    async def process(
        self,
        request: Any,
        next_handler: callable
    ) -> Any:
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