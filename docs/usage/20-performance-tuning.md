# 性能优化指南

本指南介绍如何优化使用 fastapi-easy 构建的应用的性能。

---

## 数据库优化

### 1. 创建索引

```python
class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    category = Column(String, index=True)
```

### 2. 使用连接池

```python
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
)
```

---

## 缓存优化

```python
from fastapi_easy.core.cache import CacheConfig

config = CacheConfig(
    enabled=True,
    backend="memory",
    ttl=3600,
    max_size=10000,
)
```

---

## 查询优化

### 1. 使用分页

```python
items = await adapter.get_all(
    pagination={"skip": 0, "limit": 20}
)
```

### 2. 选择字段

```python
items = await adapter.get_all(
    select_fields=["id", "name"]
)
```

---

## 监控性能

```python
import time

start = time.time()
items = await adapter.get_all()
elapsed = time.time() - start

logger.info(f"Query took {elapsed:.2f}s")
```

---

**下一步**: [最佳实践](21-best-practices.md) →
