# 软删除功能

软删除是一种常见的数据管理模式，将记录标记为已删除而不是永久删除。本指南介绍如何在 fastapi-easy 中使用软删除功能。

---

## 什么是软删除？

软删除不会从数据库中删除数据，而是标记为已删除。这样做的好处：

- ✅ 数据可恢复
- ✅ 保留审计日志
- ✅ 支持数据分析
- ✅ 符合法规要求

---

## 启用软删除

### 1. 添加软删除字段

```python
from sqlalchemy import Column, Boolean, DateTime
from datetime import datetime

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
```

### 2. 配置软删除

```python
from fastapi_easy import CRUDRouter
from fastapi_easy.core.soft_delete import SoftDeleteConfig

config = SoftDeleteConfig(
    enabled=True,
    include_deleted_by_default=False,  # 默认不包含已删除的记录
    auto_restore_on_update=False,      # 更新时不自动恢复
)

router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    soft_delete_config=config,
)
```

---

## 使用软删除

### 软删除记录

```python
# DELETE /items/1
# 响应：{"id": 1, "name": "Item 1", "is_deleted": true, "deleted_at": "2024-11-27T..."}
```

### 恢复已删除的记录

```python
from fastapi_easy.core.soft_delete import SoftDeleteAdapter

adapter = SoftDeleteAdapter(Item, session)

# 恢复单个记录
await adapter.restore(item_id=1)

# 恢复所有已删除的记录
await adapter.restore_all()
```

### 查询已删除的记录

```python
# 默认不包含已删除的记录
# GET /items
# 响应：只返回未删除的记录

# 包含已删除的记录
# GET /items?include_deleted=true
# 响应：返回所有记录（包括已删除的）
```

### 永久删除

```python
# 永久删除已删除的记录
await adapter.permanently_delete(item_id=1)

# 永久删除所有已删除的记录
await adapter.permanently_delete_all()
```

---

## 高级用法

### 自定义软删除字段

```python
from fastapi_easy.core.soft_delete import SoftDeleteMixin

class Item(Base, SoftDeleteMixin):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    # 自动添加 is_deleted 和 deleted_at 字段
```

### 检查记录是否已删除

```python
item = await adapter.get_one(1)

if adapter.is_soft_deleted(item):
    print("记录已删除")
else:
    print("记录未删除")
```

### 获取删除统计

```python
# 获取已删除的记录数
deleted_count = await adapter.count(filters={"is_deleted": True})

# 获取未删除的记录数
active_count = await adapter.count(filters={"is_deleted": False})
```

---

## 最佳实践

### 1. 总是使用软删除

```python
# ✅ 推荐：使用软删除
await adapter.soft_delete(item_id=1)

# ❌ 不推荐：直接删除
await adapter.delete_one(item_id=1)
```

### 2. 定期清理已删除的记录

```python
# 定期永久删除 30 天前删除的记录
from datetime import datetime, timedelta

cutoff_date = datetime.utcnow() - timedelta(days=30)

# 删除 deleted_at < cutoff_date 的记录
await adapter.permanently_delete_all(
    filters={"deleted_at__lt": cutoff_date}
)
```

### 3. 在查询中排除已删除的记录

```python
# 自动排除已删除的记录
router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    soft_delete_config=SoftDeleteConfig(
        include_deleted_by_default=False
    ),
)
```

### 4. 审计日志集成

```python
from fastapi_easy.core.audit_log import AuditLogger

audit_logger = AuditLogger()

# 记录软删除操作
await adapter.soft_delete(item_id=1)
audit_logger.log(
    entity_type="Item",
    entity_id=1,
    action="soft_delete",
    user_id=user.id,
)
```

---

## 常见问题

**Q: 软删除和硬删除有什么区别？**

A: 软删除标记记录为已删除但保留数据，硬删除永久删除数据。软删除更安全，支持恢复。

**Q: 如何查询包括已删除的记录？**

A: 在查询参数中添加 `include_deleted=true`。

**Q: 如何恢复已删除的记录？**

A: 使用 `SoftDeleteAdapter.restore()` 方法。

**Q: 软删除会影响性能吗？**

A: 会有轻微影响，因为需要检查 `is_deleted` 字段。建议在该字段上创建索引。

---

## 总结

软删除是一个强大的功能，可以：

- ✅ 保护数据安全
- ✅ 支持数据恢复
- ✅ 保留审计日志
- ✅ 符合法规要求

使用软删除时，记住：

1. 总是启用软删除
2. 定期清理已删除的记录
3. 在查询中排除已删除的记录
4. 与审计日志集成

---

**下一步**: [批量操作](bulk-operations.md) →
