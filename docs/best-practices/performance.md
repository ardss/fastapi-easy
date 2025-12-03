# 性能优化

提升 FastAPI-Easy 应用性能的实用技巧和最佳实践。

---

## 🎯 优化目标

- ⚡ 降低响应延迟
- 📈 提高吞吐量
- 💾 减少内存占用
- 🔄 优化数据库查询

---

## 1. 数据库优化

### 1.1 使用连接池

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 配置连接池
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # 连接池大小
    max_overflow=10,       # 最大溢出连接数
    pool_pre_ping=True,    # 连接前检查
    pool_recycle=3600,     # 连接回收时间(秒)
)
```

### 1.2 避免 N+1 查询

```python
# ❌ 不好：N+1 查询
items = await session.execute(select(Item))
for item in items:
    # 每次循环都查询数据库
    owner = await session.get(User, item.owner_id)

# ✅ 好：使用 joinedload
from sqlalchemy.orm import joinedload

items = await session.execute(
    select(Item).options(joinedload(Item.owner))
)
```

### 1.3 使用索引

```python
from sqlalchemy import Column, Integer, String, Index

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)  # 单列索引
    category = Column(String)
    price = Column(Float)
    
    # 复合索引
    __table_args__ = (
        Index('idx_category_price', 'category', 'price'),
    )
```

### 1.4 查询投影

只查询需要的字段：

```python
# ❌ 不好：查询所有字段
items = await session.execute(select(Item))

# ✅ 好：只查询需要的字段
items = await session.execute(
    select(Item.id, Item.name, Item.price)
)
```

---

## 2. 缓存策略

### 2.1 启用 L1/L2 缓存

```python
from fastapi_easy import CRUDRouter
from fastapi_easy.cache import CacheConfig, RedisBackend

# 配置 Redis 缓存
cache_backend = RedisBackend(
    host="localhost",
    port=6379,
    db=0,
)

cache_config = CacheConfig(
    enabled=True,
    ttl=300,  # 5分钟
    backend=cache_backend,
)

router = CRUDRouter(
    schema=Item,
    cache_config=cache_config,
)
```

### 2.2 缓存策略选择

```python
# 读多写少 - 使用长缓存
cache_config = CacheConfig(
    enabled=True,
    ttl=3600,  # 1小时
)

# 读写频繁 - 使用短缓存
cache_config = CacheConfig(
    enabled=True,
    ttl=60,  # 1分钟
)

# 实时数据 - 禁用缓存
cache_config = CacheConfig(
    enabled=False,
)
```

### 2.3 缓存失效策略

```python
async def after_update(context):
    """更新后清除缓存"""
    await cache.delete(f"item:{context.item_id}")
    await cache.delete("items:list")

router.hooks.register("after_update", after_update)
```

---

## 3. 异步操作

### 3.1 使用异步数据库驱动

```python
# ✅ 推荐：异步驱动
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"

# ❌ 不推荐：同步驱动
DATABASE_URL = "postgresql://user:pass@localhost/db"
```

### 3.2 并发请求

```python
import asyncio

# ❌ 不好：串行执行
user = await get_user(user_id)
items = await get_items(user_id)
orders = await get_orders(user_id)

# ✅ 好：并发执行
user, items, orders = await asyncio.gather(
    get_user(user_id),
    get_items(user_id),
    get_orders(user_id),
)
```

---

## 4. 响应优化

### 4.1 启用 GZIP 压缩

```python
from fastapi import FastAPI
from fastapi.middleware.gzip import GZIPMiddleware

app = FastAPI()
app.add_middleware(GZIPMiddleware, minimum_size=1000)
```

### 4.2 分页

```python
# ✅ 始终使用分页
@app.get("/items")
async def get_items(skip: int = 0, limit: int = 10):
    items = await db.query(Item).offset(skip).limit(limit).all()
    return items
```

### 4.3 字段过滤

```python
from pydantic import BaseModel
from typing import Optional

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    # 可选字段
    description: Optional[str] = None
    
    class Config:
        # 排除 None 值
        exclude_none = True
```

---

## 5. 批量操作

### 5.1 批量插入

```python
# ❌ 不好：逐个插入
for item_data in items_data:
    item = Item(**item_data)
    session.add(item)
    await session.commit()

# ✅ 好：批量插入
items = [Item(**data) for data in items_data]
session.add_all(items)
await session.commit()
```

### 5.2 批量更新

```python
# ✅ 使用 bulk_update_mappings
await session.execute(
    update(Item).where(Item.category == "old"),
    [{"id": 1, "category": "new"}, {"id": 2, "category": "new"}]
)
```

---

## 6. 监控和分析

### 6.1 添加性能日志

```python
import time
import logging

logger = logging.getLogger(__name__)

async def log_performance(context):
    start_time = time.time()
    yield
    duration = time.time() - start_time
    logger.info(f"Request took {duration:.2f}s")

router.hooks.register("around_get_all", log_performance)
```

### 6.2 使用 APM 工具

```python
# 集成 New Relic
import newrelic.agent
newrelic.agent.initialize('newrelic.ini')

app = newrelic.agent.WSGIApplicationWrapper(app)
```

---

## 7. 性能基准

### 典型性能指标

| 操作 | 目标延迟 | 说明 |
|------|----------|------|
| GET /items | < 50ms | 列表查询 |
| GET /items/{id} | < 30ms | 单个查询 |
| POST /items | < 100ms | 创建 |
| PUT /items/{id} | < 100ms | 更新 |
| DELETE /items/{id} | < 50ms | 删除 |

### 性能测试

```python
# 使用 locust 进行负载测试
from locust import HttpUser, task, between

class APIUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_items(self):
        self.client.get("/items?skip=0&limit=10")
    
    @task(3)
    def get_item(self):
        self.client.get("/items/1")
```

---

## 8. 常见性能问题

### 问题 1: 响应慢

**症状**: API 响应时间 > 500ms

**排查**:
1. 检查数据库查询时间
2. 检查是否有 N+1 查询
3. 检查缓存命中率
4. 检查网络延迟

**解决**:
- 添加数据库索引
- 使用 joinedload
- 启用缓存
- 使用 CDN

### 问题 2: 内存占用高

**症状**: 内存持续增长

**排查**:
1. 检查是否有内存泄漏
2. 检查大对象缓存
3. 检查连接池配置

**解决**:
- 使用分页限制结果集
- 配置合理的缓存 TTL
- 调整连接池大小

### 问题 3: 数据库连接耗尽

**症状**: "too many connections" 错误

**排查**:
1. 检查连接池配置
2. 检查是否有连接泄漏
3. 检查并发请求数

**解决**:
- 增加连接池大小
- 确保正确关闭连接
- 使用连接池回收

---

## 9. 性能优化检查清单

- [ ] 配置数据库连接池
- [ ] 添加必要的数据库索引
- [ ] 避免 N+1 查询
- [ ] 启用缓存系统
- [ ] 使用异步操作
- [ ] 启用 GZIP 压缩
- [ ] 实现分页
- [ ] 使用批量操作
- [ ] 添加性能监控
- [ ] 进行负载测试

---

## 10. 相关资源

- [缓存系统](../tutorials/03-advanced/caching.md)
- [数据库集成](../tutorials/01-basics/database-integration.md)
- [批量操作](../tutorials/02-core-features/bulk-operations.md)

---

**下一步**: [测试策略 →](testing.md)
