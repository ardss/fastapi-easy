# 最佳实践指南

本文档提供使用 fastapi-easy 的最佳实践建议。

---

## 项目结构

### 推荐的项目结构

```
my_api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 应用入口
│   ├── config.py               # 配置
│   ├── models/
│   │   ├── __init__.py
│   │   ├── item.py             # SQLAlchemy 模型
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── item.py             # Pydantic 数据模型
│   │   └── user.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── items.py            # 项目路由
│   │   └── users.py            # 用户路由
│   ├── dependencies/
│   │   ├── __init__.py
│   │   ├── auth.py             # 认证依赖
│   │   └── db.py               # 数据库依赖
│   └── utils/
│       ├── __init__.py
│       └── helpers.py           # 工具函数
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_items.py
│   └── test_users.py
├── requirements.txt
├── .env
└── README.md
```

---

## 代码组织

### 1. 分离关注点

```python
# ✅ 推荐：分离模型、数据模型和路由

# models/item.py
from sqlalchemy import Column, Integer, String

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)

# schemas/item.py
from pydantic import BaseModel

class ItemSchema(BaseModel):
    id: int
    name: str

# routers/items.py
from fastapi_easy import CRUDRouter

router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
)
```

### 2. 使用依赖注入

```python
# ✅ 推荐：使用依赖注入

from fastapi import Depends

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    return await get_user_from_token(token)

@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

### 3. 配置管理

```python
# ✅ 推荐：集中管理配置

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    log_level: str = "INFO"
    cache_ttl: int = 3600
    
    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 数据库操作

### 1. 使用事务

```python
# ✅ 推荐：使用事务

async with session.begin():
    item = await adapter.create({"name": "Item"})
    await audit_logger.log("Item", item.id, "create")
    # 如果出错，自动回滚
```

### 2. 处理并发

```python
# ✅ 推荐：使用乐观锁

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    version = Column(Integer, default=1)  # 版本号

# 更新时检查版本
item = await adapter.get_one(1)
if item.version != expected_version:
    raise ConflictError("Item has been modified")
```

### 3. 批量操作优化

```python
# ✅ 推荐：使用批量操作

# 不推荐：逐个创建
for item_data in items:
    await adapter.create(item_data)

# 推荐：批量创建
result = await adapter.bulk_create(items)
```

---

## 性能优化

### 1. 使用缓存

```python
# ✅ 推荐：缓存频繁访问的数据

from fastapi_easy.core.cache import CachedOperation

@CachedOperation(cache, ttl=3600)
async def get_popular_items():
    return await adapter.get_all(filters={"popular": True})
```

### 2. 使用索引

```python
# ✅ 推荐：在常用查询字段上创建索引

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)  # 创建索引
    category = Column(String, index=True)
```

### 3. 分页

```python
# ✅ 推荐：使用分页而不是获取所有数据

# 不推荐
items = await adapter.get_all()

# 推荐
items = await adapter.get_all(
    pagination={"skip": 0, "limit": 20}
)
```

---

## 安全性

### 1. 输入验证

```python
# ✅ 推荐：验证所有输入

from pydantic import BaseModel, Field

class ItemSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
```

### 2. 权限检查

```python
# ✅ 推荐：检查权限

async def before_delete(context):
    if not rbac.has_permission(context.user_role, "delete"):
        raise PermissionDeniedError()

router.hooks.register("before_delete", before_delete)
```

### 3. SQL 注入防护

```python
# ✅ 推荐：使用参数化查询（fastapi-easy 自动处理）

# 不推荐（fastapi-easy 会阻止）
filters = {"name__like": "'; DROP TABLE items; --"}

# 推荐
filters = {"name__like": "item%"}
```

---

## 错误处理

### 1. 自定义错误

```python
# ✅ 推荐：定义自定义异常

from fastapi_easy.core.errors import AppError

class ItemNotFoundError(AppError):
    code = "ITEM_NOT_FOUND"
    message = "Item not found"
    status_code = 404
```

### 2. 错误日志

```python
# ✅ 推荐：记录错误

try:
    item = await adapter.get_one(1)
except ItemNotFoundError as e:
    logger.error(f"Item not found: {e}")
    raise
```

---

## 测试

### 1. 单元测试

```python
# ✅ 推荐：测试业务逻辑

import pytest

@pytest.mark.asyncio
async def test_create_item():
    adapter = MockAdapter()
    result = await adapter.create({"name": "Item"})
    assert result.name == "Item"
```

### 2. 集成测试

```python
# ✅ 推荐：测试完整流程

@pytest.mark.asyncio
async def test_create_item_api(client):
    response = await client.post("/items", json={"name": "Item"})
    assert response.status_code == 201
```

### 3. 测试覆盖

```bash
# 运行测试并生成覆盖报告
pytest --cov=app tests/

# 目标：>80% 覆盖率
```

---

## 监控和日志

### 1. 结构化日志

```python
# ✅ 推荐：使用结构化日志

logger.info(
    "Item created",
    extra_fields={
        "item_id": item.id,
        "user_id": user.id,
        "timestamp": datetime.utcnow()
    }
)
```

### 2. 性能监控

```python
# ✅ 推荐：监控关键操作

import time

start = time.time()
items = await adapter.get_all()
elapsed = time.time() - start

if elapsed > 1.0:
    logger.warning(f"Slow query: {elapsed:.2f}s")
```

### 3. 错误监控

```python
# ✅ 推荐：监控错误率

error_count = 0
total_count = 0

try:
    result = await operation.execute()
    total_count += 1
except Exception as e:
    error_count += 1
    logger.error(f"Error: {e}")

error_rate = error_count / total_count if total_count > 0 else 0
if error_rate > 0.05:  # 5% 错误率
    logger.alert("High error rate detected")
```

---

## 部署

### 1. 环境配置

```bash
# .env.production
DATABASE_URL=postgresql://...
LOG_LEVEL=WARNING
CACHE_BACKEND=redis
RATE_LIMIT_ENABLED=true
```

### 2. 健康检查

```python
# ✅ 推荐：添加健康检查端点

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": await check_database(),
        "cache": await check_cache()
    }
```

### 3. 优雅关闭

```python
# ✅ 推荐：优雅关闭

@app.on_event("shutdown")
async def shutdown():
    await db.close()
    await cache.close()
```

---

## 常见陷阱

### 1. 不使用软删除

```python
# ❌ 不推荐：直接删除数据
await adapter.delete_one(1)

# ✅ 推荐：使用软删除
await adapter.soft_delete(1)
```

### 2. 忽视性能

```python
# ❌ 不推荐：获取所有数据
items = await adapter.get_all()

# ✅ 推荐：使用分页和缓存
items = await adapter.get_all(
    pagination={"skip": 0, "limit": 20}
)
```

### 3. 缺少错误处理

```python
# ❌ 不推荐：忽视错误
result = await adapter.create(data)

# ✅ 推荐：处理错误
try:
    result = await adapter.create(data)
except ValidationError as e:
    logger.error(f"Validation error: {e}")
    raise
```

---

## 总结

使用 fastapi-easy 的最佳实践：

1. ✅ 分离关注点
2. ✅ 使用依赖注入
3. ✅ 集中管理配置
4. ✅ 使用事务
5. ✅ 优化性能
6. ✅ 检查安全性
7. ✅ 处理错误
8. ✅ 编写测试
9. ✅ 监控和日志
10. ✅ 优雅部署

---

**下一步**: [部署指南](23-deployment.md) →
