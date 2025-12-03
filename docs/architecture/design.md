# 架构设计

本文档介绍 FastAPI-Easy 的整体架构设计。

---

## 核心架构

FastAPI-Easy 采用分层架构设计：

```
┌─────────────────────────────────────┐
│         FastAPI 应用                 │
├─────────────────────────────────────┤
│         CRUDRouter 层                │
│  (自动生成 CRUD 路由)                 │
├─────────────────────────────────────┤
│         中间件层                      │
│  (认证、权限、速率限制等)             │
├─────────────────────────────────────┤
│         业务逻辑层                    │
│  (Hook、过滤、排序、分页等)           │
├─────────────────────────────────────┤
│         适配器层                      │
│  (ORM 适配器接口)                     │
├─────────────────────────────────────┤
│         数据库层                      │
│  (SQLAlchemy、Tortoise、MongoDB等)   │
└─────────────────────────────────────┘
```

---

## 组件设计

### 1. CRUDRouter

主要职责：
- 自动生成 CRUD 路由
- 管理路由配置
- 集成中间件和 Hook

```python
class CRUDRouter:
    def __init__(self, schema, adapter, **config):
        self.schema = schema
        self.adapter = adapter
        self.config = config
        self._setup_routes()
```

### 2. ORMAdapter

抽象基类，定义 ORM 操作接口：

```python
class ORMAdapter(ABC):
    @abstractmethod
    async def get_all(self, **filters) -> List:
        pass
    
    @abstractmethod
    async def get_one(self, id) -> Optional:
        pass
    
    @abstractmethod
    async def create(self, data) -> Any:
        pass
    
    @abstractmethod
    async def update(self, id, data) -> Any:
        pass
    
    @abstractmethod
    async def delete(self, id) -> bool:
        pass
```

### 3. Hook 系统

支持 10 种 Hook 事件：

```python
class HookRegistry:
    def register(self, event: str, callback: Callable):
        pass
    
    async def trigger(self, event: str, *args, **kwargs):
        pass
```

Hook 事件：
- before_get_all / after_get_all
- before_get_one / after_get_one
- before_create / after_create
- before_update / after_update
- before_delete / after_delete

### 4. 配置系统

```python
@dataclass
class CRUDConfig:
    enable_filters: bool = True
    enable_sorters: bool = True
    enable_pagination: bool = True
    enable_soft_delete: bool = False
    enable_audit: bool = False
    enable_bulk_operations: bool = False
    filter_fields: List[str] = None
    sort_fields: List[str] = None
    default_limit: int = 10
    max_limit: int = 100
```

---

## 数据流

### 请求处理流程

```
1. 客户端发送 HTTP 请求
   ↓
2. FastAPI 路由匹配
   ↓
3. 中间件处理（认证、权限等）
   ↓
4. CRUDRouter 处理
   ↓
5. 触发 before_* Hook
   ↓
6. 业务逻辑处理（过滤、排序、分页）
   ↓
7. 调用 ORM 适配器
   ↓
8. 数据库查询
   ↓
9. 触发 after_* Hook
   ↓
10. 返回响应
```

### 数据转换流程

```
HTTP Request
    ↓
Pydantic Schema 验证
    ↓
业务逻辑处理
    ↓
ORM 模型转换
    ↓
数据库操作
    ↓
ORM 模型转换
    ↓
Pydantic Schema 序列化
    ↓
HTTP Response
```

---

## 设计模式

### 1. 适配器模式

使用 ORMAdapter 抽象不同 ORM 的差异：

```python
# SQLAlchemy 适配器
class SQLAlchemyAdapter(ORMAdapter):
    async def get_all(self, **filters):
        query = self.session.query(self.model)
        for key, value in filters.items():
            query = query.filter(getattr(self.model, key) == value)
        return await query.all()

# MongoDB 适配器
class MongoAdapter(ORMAdapter):
    async def get_all(self, **filters):
        return await self.collection.find(filters).to_list(None)
```

### 2. Hook 模式

支持在关键点插入自定义逻辑：

```python
@migration_hook("before_create")
async def validate_before_create(data):
    # 自定义验证逻辑
    pass

@migration_hook("after_create", priority=10)
async def log_after_create(data):
    # 自定义日志逻辑
    pass
```

### 3. 中间件模式

使用中间件处理横切关注点：

```python
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(PermissionMiddleware)
app.add_middleware(RateLimitMiddleware)
```

---

## 扩展点

### 1. 自定义适配器

```python
class CustomAdapter(ORMAdapter):
    async def get_all(self, **filters):
        # 自定义实现
        pass
```

### 2. 自定义 Hook

```python
@migration_hook("before_create")
async def custom_hook(data):
    # 自定义逻辑
    pass
```

### 3. 自定义中间件

```python
class CustomMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 自定义逻辑
        response = await call_next(request)
        return response
```

---

## 性能考虑

### 1. 缓存

- 查询结果缓存
- 权限缓存
- Schema 缓存

### 2. 异步

- 所有数据库操作都是异步的
- 支持并发请求

### 3. 批量操作

- 支持批量创建、更新、删除
- 减少数据库往返次数

---

## 安全考虑

### 1. 输入验证

- Pydantic Schema 自动验证
- 自定义验证器支持

### 2. 权限控制

- 端点级权限
- 字段级权限

### 3. 审计日志

- 自动记录所有操作
- 支持追踪数据变更
