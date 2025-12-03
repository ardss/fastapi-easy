# 批量操作

批量操作允许在单个请求中对多个记录进行 CRUD 操作。本文档介绍如何使用批量操作功能。

---

## 什么是批量操作

批量操作可以：

- ✅ 一次创建多个记录
- ✅ 一次更新多个记录
- ✅ 一次删除多个记录
- ✅ 提高性能和效率

---

## 启用批量操作

```python
from fastapi_easy import CRUDRouter
from fastapi_easy.core.bulk_operations import BulkOperationConfig

config = BulkOperationConfig(
    enabled=True,
    max_batch_size=1000,           # 最大批量大小
    transaction_mode="atomic",      # 原子事务模式
)

router = CRUDRouter(
    schema=ItemSchema,
    adapter=adapter,
    bulk_operation_config=config,
)
```

---

## 批量创建

### 请求

```python
# POST /items/batch
# Content-Type: application/json

{
    "items": [
        {"name": "Item 1", "price": 10.0},
        {"name": "Item 2", "price": 20.0},
        {"name": "Item 3", "price": 30.0}
    ]
}
```

### 响应

```json
{
    "created": 3,
    "items": [
        {"id": 1, "name": "Item 1", "price": 10.0},
        {"id": 2, "name": "Item 2", "price": 20.0},
        {"id": 3, "name": "Item 3", "price": 30.0}
    ]
}
```

---

## 批量更新

### 请求

```python
# PUT /items/batch
# Content-Type: application/json

{
    "items": [
        {"id": 1, "name": "Updated Item 1", "price": 15.0},
        {"id": 2, "name": "Updated Item 2", "price": 25.0}
    ]
}
```

### 响应

```json
{
    "updated": 2,
    "items": [
        {"id": 1, "name": "Updated Item 1", "price": 15.0},
        {"id": 2, "name": "Updated Item 2", "price": 25.0}
    ]
}
```

---

## 批量删除

### 请求

```python
# DELETE /items/batch
# Content-Type: application/json

{
    "ids": [1, 2, 3]
}
```

### 响应

```json
{
    "deleted": 3
}
```

---

## 事务模式

### 原子模式（推荐）

所有操作成功或全部失败：

```python
transaction_mode="atomic"
```

### 部分模式

允许部分操作失败：

```python
transaction_mode="partial"
```

响应示例：

```json
{
    "created": 2,
    "failed": 1,
    "errors": [
        {
            "index": 2,
            "error": "Duplicate entry"
        }
    ]
}
```

---

## 性能优化

### 1. 合理设置批量大小

```python
# 不好：一次创建 10000 条
POST /items/batch with 10000 items

# 好：分批创建
POST /items/batch with 1000 items (10 次)
```

### 2. 使用批量操作而不是单个请求

```python
# 不好：10 个单独的 POST 请求
for item in items:
    POST /items

# 好：1 个批量请求
POST /items/batch with 10 items
```

### 3. 监控性能

```python
import time

start = time.time()
response = client.post("/items/batch", json={"items": items})
duration = time.time() - start

print(f"Created {response.json()['created']} items in {duration}s")
```

---

## 错误处理

### 处理批量操作错误

```python
from fastapi import HTTPException

try:
    response = client.post("/items/batch", json={"items": items})
    if response.status_code == 200:
        result = response.json()
        print(f"Created {result['created']} items")
    else:
        raise HTTPException(status_code=response.status_code)
except Exception as e:
    print(f"Error: {e}")
```

---

## 最佳实践

### 1. 验证数据

```python
# 在发送批量请求前验证数据
for item in items:
    if not item.get("name"):
        raise ValueError("Name is required")
```

### 2. 使用适当的批量大小

```python
# 根据数据库性能调整
max_batch_size = 1000  # 对大多数数据库足够
```

### 3. 监控和日志

```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"Creating {len(items)} items")
response = client.post("/items/batch", json={"items": items})
logger.info(f"Created {response.json()['created']} items")
```

---

## 常见问题

### Q: 批量操作的最大大小是多少？
A: 由 `max_batch_size` 配置决定，默认为 1000。

### Q: 如果批量操作中有错误会怎样？
A: 取决于 `transaction_mode`。原子模式会回滚所有操作。

### Q: 批量操作是否支持关联数据？
A: 支持，但需要在 Schema 中正确定义关系。
