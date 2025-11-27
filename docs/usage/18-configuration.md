# 完整配置参考

本文档提供 fastapi-easy 的完整配置参考。

---

## CRUDRouter 配置

```python
from fastapi_easy import CRUDRouter

router = CRUDRouter(
    # 基础配置
    schema=ItemSchema,                    # Pydantic 数据模型
    backend=backend,                      # ORM 适配器
    prefix="/items",                      # 路由前缀
    tags=["items"],                       # OpenAPI 标签
    
    # 功能配置
    enable_filters=True,                  # 启用过滤
    enable_sorters=True,                  # 启用排序
    enable_pagination=True,               # 启用分页
    
    # 高级功能配置
    soft_delete_config=soft_delete_config,
    bulk_operation_config=bulk_config,
    permission_config=permission_config,
    audit_log_config=audit_config,
    cache_config=cache_config,
    rate_limit_config=rate_limit_config,
    
    # 响应配置
    response_formatter=formatter,
    
    # 钩子
    hooks=hooks,
)
```

---

## 软删除配置

```python
from fastapi_easy.core.soft_delete import SoftDeleteConfig

config = SoftDeleteConfig(
    enabled=True,                         # 启用软删除
    include_deleted_by_default=False,     # 默认不包含已删除的记录
    auto_restore_on_update=False,         # 更新时不自动恢复
    deleted_field="is_deleted",           # 已删除标记字段
    deleted_at_field="deleted_at",        # 删除时间字段
)
```

---

## 批量操作配置

```python
from fastapi_easy.core.bulk_operations import BulkOperationConfig

config = BulkOperationConfig(
    enabled=True,                         # 启用批量操作
    max_batch_size=1000,                  # 最大批量大小
    transaction_mode="atomic",            # 事务模式：atomic/partial
    timeout=30,                           # 超时时间（秒）
)
```

---

## 权限配置

```python
from fastapi_easy.core.permissions import PermissionConfig

config = PermissionConfig(
    enabled=True,                         # 启用权限控制
    default_role="user",                  # 默认角色
    require_authentication=True,          # 需要认证
    cache_permissions=True,               # 缓存权限
    cache_ttl=3600,                       # 缓存 TTL（秒）
)
```

---

## 审计日志配置

```python
from fastapi_easy.core.audit_log import AuditLogConfig

config = AuditLogConfig(
    enabled=True,                         # 启用审计日志
    track_changes=True,                   # 记录变更内容
    track_user=True,                      # 记录用户信息
    track_timestamp=True,                 # 记录时间戳
    async_logging=True,                   # 异步记录
    retention_days=365,                   # 保留天数
)
```

---

## 缓存配置

```python
from fastapi_easy.core.cache import CacheConfig

config = CacheConfig(
    enabled=True,                         # 启用缓存
    backend="memory",                     # 缓存后端：memory/redis
    ttl=3600,                             # 默认 TTL（秒）
    max_size=1000,                        # 最大缓存大小
)
```

---

## 速率限制配置

```python
from fastapi_easy.core.rate_limit import RateLimitConfig

config = RateLimitConfig(
    enabled=True,                         # 启用速率限制
    backend="memory",                     # 后端：memory/redis
    default_limit=100,                    # 默认请求限制
    default_window=60,                    # 默认时间窗口（秒）
)
```

---

## 日志配置

```python
from fastapi_easy.core.logger import LoggerConfig

config = LoggerConfig(
    enabled=True,                         # 启用日志
    level="INFO",                         # 日志级别
    format="json",                        # 日志格式：json/text
    output="stdout",                      # 输出：stdout/file
    file_path="/var/log/app.log",         # 日志文件路径
    max_size=10485760,                    # 最大文件大小（10MB）
    backup_count=5,                       # 备份文件数
)
```

---

## 中间件配置

```python
from fastapi_easy.middleware import MiddlewareChain

chain = MiddlewareChain()

# 添加错误处理中间件
chain.add(ErrorHandlingMiddleware())

# 添加日志中间件
chain.add(LoggingMiddleware(logger=logger))

# 添加监控中间件
chain.add(MonitoringMiddleware())
```

---

## GraphQL 配置

```python
from fastapi_easy.graphql import GraphQLConfig

config = GraphQLConfig(
    enabled=True,                         # 启用 GraphQL
    endpoint="/graphql",                  # GraphQL 端点
    playground=True,                      # 启用 GraphQL Playground
)
```

---

## WebSocket 配置

```python
from fastapi_easy.websocket import WebSocketConfig

config = WebSocketConfig(
    enabled=True,                         # 启用 WebSocket
    endpoint="/ws",                       # WebSocket 端点
    max_connections=1000,                 # 最大连接数
    message_queue_size=100,               # 消息队列大小
)
```

---

## 完整示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.core.soft_delete import SoftDeleteConfig
from fastapi_easy.core.bulk_operations import BulkOperationConfig
from fastapi_easy.core.permissions import PermissionConfig
from fastapi_easy.core.audit_log import AuditLogConfig
from fastapi_easy.core.cache import CacheConfig
from fastapi_easy.core.rate_limit import RateLimitConfig

app = FastAPI()

# 配置所有功能
router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    
    # 启用所有功能
    enable_filters=True,
    enable_sorters=True,
    enable_pagination=True,
    
    # 配置高级功能
    soft_delete_config=SoftDeleteConfig(enabled=True),
    bulk_operation_config=BulkOperationConfig(enabled=True),
    permission_config=PermissionConfig(enabled=True),
    audit_log_config=AuditLogConfig(enabled=True),
    cache_config=CacheConfig(enabled=True),
    rate_limit_config=RateLimitConfig(enabled=True),
)

app.include_router(router)
```

---

## 环境变量配置

```bash
# .env 文件

# 数据库
DATABASE_URL=postgresql://user:password@localhost/dbname

# 日志
LOG_LEVEL=INFO
LOG_FORMAT=json

# 缓存
CACHE_BACKEND=memory
CACHE_TTL=3600

# 速率限制
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT=100

# 权限
PERMISSION_ENABLED=true
REQUIRE_AUTHENTICATION=true

# 审计日志
AUDIT_LOG_ENABLED=true
AUDIT_LOG_RETENTION_DAYS=365
```

---

## 配置优先级

1. 环境变量（最高）
2. 配置对象
3. 默认值（最低）

---

## 常见配置组合

### 最小配置

```python
router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
)
```

### 标准配置

```python
router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    enable_filters=True,
    enable_sorters=True,
    enable_pagination=True,
)
```

### 企业配置

```python
router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    enable_filters=True,
    enable_sorters=True,
    enable_pagination=True,
    soft_delete_config=SoftDeleteConfig(enabled=True),
    permission_config=PermissionConfig(enabled=True),
    audit_log_config=AuditLogConfig(enabled=True),
    cache_config=CacheConfig(enabled=True),
    rate_limit_config=RateLimitConfig(enabled=True),
)
```

---

**下一步**: [最佳实践](21-best-practices.md) →
