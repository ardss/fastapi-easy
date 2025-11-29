# 架构设计和扩展

本文档介绍 fastapi-easy 的架构设计，以及如何进行扩展和定制。

---

## 核心架构

### 分离的职责

fastapi-easy 采用分离职责的设计，将路由生成和路由管理分开：

```
┌─────────────────────────────────────────┐
│         CRUDGenerator                   │
│  (负责生成路由和操作)                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         OperationRegistry               │
│  (管理所有操作：CRUD、搜索、排序等)     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         APIRouter                       │
│  (FastAPI 路由管理)                     │
└─────────────────────────────────────────┘
```

**优势**:
- ✅ 职责清晰
- ✅ 易于测试
- ✅ 易于扩展
- ✅ 易于维护

---

## 操作系统（Operation System）

### 基础操作接口

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any, Dict

T = TypeVar('T')

class Operation(ABC, Generic[T]):
    """所有操作的基类"""
    
    name: str
    method: str  # GET, POST, PUT, DELETE
    path: str
    
    @abstractmethod
    async def before_execute(self, context: 'ExecutionContext') -> None:
        """操作前的钩子"""
        pass
    
    @abstractmethod
    async def execute(self, context: 'ExecutionContext') -> T:
        """执行操作"""
        pass
    
    @abstractmethod
    async def after_execute(self, context: 'ExecutionContext') -> T:
        """操作后的钩子"""
        pass

class ExecutionContext:
    """执行上下文"""
    schema: Type[T]
    adapter: 'ORMAdapter'
    request: 'Request'
    filters: Dict[str, Any]
    sorts: Dict[str, Any]
    pagination: Dict[str, Any]
    user: Any  # 当前用户
    result: Any  # 操作结果
```

### 内置操作

```python
class GetAllOperation(Operation):
    """获取所有项目"""
    name = "get_all"
    method = "GET"
    path = ""
    
    async def before_execute(self, context):
        # 权限检查
        pass
    
    async def execute(self, context):
        return await context.adapter.get_all(
            filters=context.filters,
            sorts=context.sorts,
            pagination=context.pagination
        )
    
    async def after_execute(self, context):
        # 审计日志
        pass

class CreateOperation(Operation):
    """创建项目"""
    name = "create"
    method = "POST"
    path = ""
    
    async def before_execute(self, context):
        # 验证数据
        pass
    
    async def execute(self, context):
        return await context.adapter.create(context.data)
    
    async def after_execute(self, context):
        # 发送通知
        pass

# 其他操作：GetOne、Update、DeleteOne、DeleteAll、Search、Sort、Paginate、BulkCreate、BulkUpdate、BulkDelete
```

### 自定义操作

```python
class CustomSearchOperation(Operation):
    """自定义搜索操作"""
    name = "advanced_search"
    method = "POST"
    path = "/search"
    
    async def before_execute(self, context):
        # 验证搜索参数
        if not context.search_query:
            raise ValidationError("Search query is required")
    
    async def execute(self, context):
        # 调用搜索引擎（如 Elasticsearch）
        results = await elasticsearch.search(
            index="items",
            query=context.search_query
        )
        return results
    
    async def after_execute(self, context):
        # 记录搜索日志
        await log_search(context.user, context.search_query)

# 注册自定义操作
router = CRUDRouter(schema=Item, adapter=adapter)
router.register_operation(CustomSearchOperation())
```

---

## ORM 适配器（ORM Adapter）

### 统一的 ORM 接口

```python
from abc import ABC, abstractmethod
from typing import List, Any, Dict, Optional

class ORMAdapter(ABC):
    """ORM 适配器基类"""
    
    @abstractmethod
    async def get_all(
        self,
        filters: Dict[str, Any],
        sorts: Dict[str, Any],
        pagination: Dict[str, Any]
    ) -> List[Any]:
        """获取所有项目"""
        pass
    
    @abstractmethod
    async def get_one(self, id: Any) -> Optional[Any]:
        """获取单个项目"""
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Any:
        """创建项目"""
        pass
    
    @abstractmethod
    async def update(self, id: Any, data: Dict[str, Any]) -> Any:
        """更新项目"""
        pass
    
    @abstractmethod
    async def delete_one(self, id: Any) -> Any:
        """删除单个项目"""
        pass
    
    @abstractmethod
    async def delete_all(self) -> List[Any]:
        """删除所有项目"""
        pass
    
    @abstractmethod
    async def count(self, filters: Dict[str, Any]) -> int:
        """计数"""
        pass
```

### SQLAlchemy 适配器实现

```python
class SQLAlchemyAdapter(ORMAdapter):
    """SQLAlchemy 异步适配器"""
    
    def __init__(self, model: Type[Base], session_factory):
        self.model = model
        self.session_factory = session_factory
    
    async def get_all(self, filters, sorts, pagination):
        async with self.session_factory() as session:
            query = select(self.model)
            
            # 应用过滤
            for field, value in filters.items():
                query = query.where(getattr(self.model, field) == value)
            
            # 应用排序
            for field, direction in sorts.items():
                col = getattr(self.model, field)
                query = query.order_by(col.desc() if direction == 'desc' else col)
            
            # 应用分页
            query = query.offset(pagination['skip']).limit(pagination['limit'])
            
            result = await session.execute(query)
            return result.scalars().all()
    
    async def get_one(self, id):
        async with self.session_factory() as session:
            return await session.get(self.model, id)
    
    # ... 其他方法
```

### Tortoise 适配器实现

```python
class TortoiseAdapter(ORMAdapter):
    """Tortoise ORM 适配器"""
    
    def __init__(self, model: Type[Model]):
        self.model = model
    
    async def get_all(self, filters, sorts, pagination):
        query = self.model.all()
        
        # 应用过滤
        for field, value in filters.items():
            query = query.filter(**{field: value})
        
        # 应用排序
        for field, direction in sorts.items():
            if direction == 'desc':
                query = query.order_by(f"-{field}")
            else:
                query = query.order_by(field)
        
        # 应用分页
        query = query.offset(pagination['skip']).limit(pagination['limit'])
        
        return await query
    
    # ... 其他方法
```

---

## 错误处理系统

### 结构化错误

```python
from enum import Enum

class ErrorCode(str, Enum):
    """错误代码"""
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"

class AppError(Exception):
    """应用错误基类"""
    
    code: ErrorCode
    status_code: int
    message: str
    details: Dict[str, Any]
    
    def __init__(
        self,
        code: ErrorCode,
        status_code: int,
        message: str,
        details: Dict[str, Any] = None
    ):
        self.code = code
        self.status_code = status_code
        self.message = message
        self.details = details or {}
    
    def to_dict(self):
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }

class NotFoundError(AppError):
    """资源不存在"""
    def __init__(self, resource: str, id: Any):
        super().__init__(
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            message=f"{resource} with id {id} not found",
            details={"resource": resource, "id": id}
        )

class ValidationError(AppError):
    """验证错误"""
    def __init__(self, field: str, message: str):
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            status_code=422,
            message=f"Validation error in field {field}",
            details={"field": field, "message": message}
        )

class PermissionDeniedError(AppError):
    """权限不足"""
    def __init__(self, action: str):
        super().__init__(
            code=ErrorCode.PERMISSION_DENIED,
            status_code=403,
            message=f"Permission denied for action {action}",
            details={"action": action}
        )
```

### 错误处理中间件

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "details": {}
        }
    )
```

---

## 钩子系统（Hook System）

### 全局钩子

```python
class HookRegistry:
    """钩子注册表"""
    
    def __init__(self):
        self.hooks = {}
    
    def register(self, event: str, callback):
        """注册钩子"""
        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(callback)
    
    async def trigger(self, event: str, context: ExecutionContext):
        """触发钩子"""
        if event in self.hooks:
            for callback in self.hooks[event]:
                await callback(context)

# 支持的钩子事件
HOOK_EVENTS = {
    "before_create": "创建前",
    "after_create": "创建后",
    "before_update": "更新前",
    "after_update": "更新后",
    "before_delete": "删除前",
    "after_delete": "删除后",
    "before_get": "获取前",
    "after_get": "获取后",
}
```

### 使用钩子

```python
async def send_email_on_create(context: ExecutionContext):
    """创建后发送邮件"""
    await send_email(
        to=context.result.email,
        subject="Welcome!",
        body="Thank you for signing up!"
    )

async def check_permission_before_delete(context: ExecutionContext):
    """删除前检查权限"""
    if not context.user.is_admin:
        raise PermissionDeniedError("delete")

# 注册钩子
router = CRUDRouter(schema=Item, adapter=adapter)
router.hooks.register("after_create", send_email_on_create)
router.hooks.register("before_delete", check_permission_before_delete)
```

---

## 响应格式系统

### 自定义响应格式

```python
from typing import Generic, TypeVar, List

T = TypeVar('T')

class PaginatedResponse(Generic[T]):
    """分页响应"""
    data: List[T]
    total: int
    page: int
    pages: int
    limit: int
    skip: int

class CustomResponse(Generic[T]):
    """自定义响应"""
    items: List[T]
    meta: Dict[str, Any]
    links: Dict[str, str]

class ResponseFormatter(ABC):
    """响应格式化器"""
    
    @abstractmethod
    def format_list(self, items: List[T], total: int, pagination: Dict) -> Any:
        """格式化列表响应"""
        pass
    
    @abstractmethod
    def format_single(self, item: T) -> Any:
        """格式化单个项目响应"""
        pass
    
    @abstractmethod
    def format_error(self, error: AppError) -> Any:
        """格式化错误响应"""
        pass

class DefaultResponseFormatter(ResponseFormatter):
    """默认响应格式化器"""
    
    def format_list(self, items, total, pagination):
        return {
            "data": items,
            "total": total,
            "page": pagination['page'],
            "pages": pagination['pages'],
            "limit": pagination['limit'],
            "skip": pagination['skip']
        }
    
    def format_single(self, item):
        return {"data": item}
    
    def format_error(self, error):
        return error.to_dict()
```

### 使用自定义响应格式

```python
class CustomResponseFormatter(ResponseFormatter):
    def format_list(self, items, total, pagination):
        return {
            "items": items,
            "meta": {
                "total": total,
                "page": pagination['page'],
                "pages": pagination['pages']
            },
            "links": {
                "self": f"/items?page={pagination['page']}",
                "next": f"/items?page={pagination['page'] + 1}" if pagination['page'] < pagination['pages'] else None,
                "prev": f"/items?page={pagination['page'] - 1}" if pagination['page'] > 1 else None
            }
        }
    
    # ... 其他方法

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    response_formatter=CustomResponseFormatter()
)
```

---

## 配置系统

### 集中配置

```python
from dataclasses import dataclass
from typing import List, Type

@dataclass
class CRUDConfig:
    """CRUD 配置"""
    # 功能开关
    enable_filters: bool = True
    enable_sorters: bool = True
    enable_pagination: bool = True
    enable_soft_delete: bool = False
    enable_audit: bool = False
    enable_bulk_operations: bool = False
    
    # 过滤配置
    filter_fields: List[str] = None
    
    # 排序配置
    sort_fields: List[str] = None
    default_sort: str = None
    
    # 分页配置
    default_limit: int = 10
    max_limit: int = 100
    
    # 软删除配置
    deleted_at_field: str = "deleted_at"
    
    # 响应格式
    response_formatter: Type[ResponseFormatter] = DefaultResponseFormatter
    
    # 错误处理
    include_error_details: bool = True
    log_errors: bool = True

# 使用配置
config = CRUDConfig(
    enable_filters=True,
    filter_fields=["name", "price"],
    enable_sorters=True,
    sort_fields=["name", "created_at"],
    enable_soft_delete=True,
    enable_audit=True,
    default_limit=20,
    max_limit=100
)

router = CRUDRouter(schema=Item, adapter=adapter, config=config)
```

---

## 完整示例：扩展系统

```python
# 1. 定义自定义操作
class ExportOperation(Operation):
    name = "export"
    method = "GET"
    path = "/export"
    
    async def before_execute(self, context):
        if not context.user.is_admin:
            raise PermissionDeniedError("export")
    
    async def execute(self, context):
        items = await context.adapter.get_all(
            filters=context.filters,
            sorts=context.sorts,
            pagination={"skip": 0, "limit": None}
        )
        return self._to_csv(items)
    
    async def after_execute(self, context):
        await log_export(context.user, len(context.result))

# 2. 定义自定义适配器
class ElasticsearchAdapter(ORMAdapter):
    async def get_all(self, filters, sorts, pagination):
        # 使用 Elasticsearch 搜索
        pass

# 3. 定义自定义响应格式
class GraphQLResponseFormatter(ResponseFormatter):
    def format_list(self, items, total, pagination):
        return {
            "data": {
                "items": items,
                "pageInfo": {
                    "total": total,
                    "hasNextPage": pagination['skip'] + pagination['limit'] < total
                }
            }
        }

# 4. 创建路由
config = CRUDConfig(
    enable_filters=True,
    enable_sorters=True,
    response_formatter=GraphQLResponseFormatter
)

router = CRUDRouter(
    schema=Item,
    adapter=SQLAlchemyAdapter(ItemDB, get_db),
    config=config
)

# 5. 注册自定义操作
router.register_operation(ExportOperation())

# 6. 注册钩子
router.hooks.register("after_create", send_email_on_create)
router.hooks.register("before_delete", check_permission_before_delete)
```

---

## 下一步

- 学习[搜索和过滤](04-filters.md)
- 了解[排序功能](05-sorting.md)
- 查看[完整示例](06-complete-example.md)
