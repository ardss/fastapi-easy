# 批量操作

批量操作允许在单个请求中对多个记录进行 CRUD 操作。本指南介绍如何使用批量操作功能。

---

## 什么是批量操作？

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
    backend=backend,
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

```python
{
    "success_count": 3,
    "failure_count": 0,
    "errors": [],
    "results": [
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

```python
{
    "success_count": 2,
    "failure_count": 0,
    "errors": [],
    "results": [
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

```python
{
    "success_count": 3,
    "failure_count": 0,
    "errors": [],
    "deleted_count": 3
}
```

---

## 高级用法

### 处理部分失败

```python
# 当某些操作失败时
{
    "success_count": 2,
    "failure_count": 1,
    "errors": [
        {
            "index": 2,
            "error": "Validation error",
            "details": "Price must be positive"
        }
    ],
    "results": [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item 2"}
    ]
}
```

### 事务模式

```python
# 原子模式：全部成功或全部失败
config = BulkOperationConfig(
    transaction_mode="atomic"
)

# 部分模式：继续处理其他记录
config = BulkOperationConfig(
    transaction_mode="partial"
)
```

### 获取批量操作结果

```python
from fastapi_easy.core.bulk_operations import BulkOperationAdapter

adapter = BulkOperationAdapter(Item, session)

# 执行批量创建
result = await adapter.bulk_create(
    items=[
        {"name": "Item 1"},
        {"name": "Item 2"}
    ]
)

print(f"成功: {result.success_count}")
print(f"失败: {result.failure_count}")
print(f"错误: {result.errors}")
```

---

## 最佳实践

### 1. 检查批量大小

```python
# ✅ 推荐：检查大小
if len(items) > max_batch_size:
    raise ValueError(f"批量大小超过限制: {max_batch_size}")

# 执行批量操作
result = await adapter.bulk_create(items)
```

### 2. 处理错误

```python
# ✅ 推荐：处理错误
result = await adapter.bulk_create(items)

if result.failure_count > 0:
    for error in result.errors:
        logger.error(f"批量操作错误: {error}")
```

### 3. 使用事务

```python
# ✅ 推荐：使用事务
config = BulkOperationConfig(
    transaction_mode="atomic"
)

# 确保全部成功或全部失败
result = await adapter.bulk_create(items)
```

### 4. 监控性能

```python
import time

start = time.time()
result = await adapter.bulk_create(items)
elapsed = time.time() - start

logger.info(f"批量创建耗时: {elapsed:.2f}s")
logger.info(f"成功: {result.success_count}, 失败: {result.failure_count}")
```

---

## 常见问题

**Q: 批量操作的最大大小是多少？**

A: 默认为 1000，可在 `BulkOperationConfig` 中配置。

**Q: 如果批量操作部分失败怎么办？**

A: 取决于事务模式。原子模式会回滚所有更改，部分模式会继续处理。

**Q: 批量操作支持哪些操作？**

A: 支持创建、更新、删除。

**Q: 如何提高批量操作的性能？**

A: 增加批量大小（在数据库限制范围内），使用原子事务模式。

---

## 总结

批量操作可以显著提高性能：

- ✅ 减少网络往返
- ✅ 提高数据库效率
- ✅ 简化客户端代码

使用批量操作时，记住：

1. 检查批量大小
2. 处理错误
3. 使用事务
4. 监控性能

---

**下一步**: [权限控制](11-permissions.md) →
