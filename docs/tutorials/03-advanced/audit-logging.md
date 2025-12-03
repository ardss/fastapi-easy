# 审计日志

审计日志记录所有对数据的修改操作，用于合规性、安全性和故障排除。本指南介绍如何使用审计日志功能。

---

## 什么是审计日志？

审计日志记录：

- ✅ 谁进行了操作
- ✅ 什么时候进行的操作
- ✅ 操作了什么数据
- ✅ 数据如何改变

---

## 启用审计日志

### 1. 添加审计日志表

```python
from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    entity_type = Column(String, index=True)  # 实体类型
    entity_id = Column(Integer, index=True)   # 实体 ID
    action = Column(String)                   # 操作（create/update/delete）
    user_id = Column(Integer)                 # 用户 ID
    changes = Column(JSON)                    # 变更内容
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
```

### 2. 配置审计日志

```python
from fastapi_easy import CRUDRouter
from fastapi_easy.core.audit_log import AuditLogConfig

config = AuditLogConfig(
    enabled=True,
    track_changes=True,      # 记录变更内容
    track_user=True,         # 记录用户信息
    track_timestamp=True,    # 记录时间戳
)

router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    audit_log_config=config,
)
```

---

## 使用审计日志

### 自动记录

```python
# 创建记录时自动记录
# POST /items
# 自动创建审计日志：
# {
#   "entity_type": "Item",
#   "entity_id": 1,
#   "action": "create",
#   "user_id": 123,
#   "changes": {"name": "Item 1", "price": 10.0},
#   "timestamp": "2024-11-27T..."
# }
```

### 手动记录

```python
from fastapi_easy.core.audit_log import AuditLogger

logger = AuditLogger()

# 记录创建
logger.log(
    entity_type="Item",
    entity_id=1,
    action="create",
    user_id=user.id,
    changes={"name": "Item 1", "price": 10.0}
)

# 记录更新
logger.log(
    entity_type="Item",
    entity_id=1,
    action="update",
    user_id=user.id,
    changes={"price": 15.0}  # 只记录变更的字段
)

# 记录删除
logger.log(
    entity_type="Item",
    entity_id=1,
    action="delete",
    user_id=user.id,
)
```

---

## 查询审计日志

### 获取实体的所有操作

```python
# GET /audit-logs?entity_type=Item&entity_id=1

# 响应：
{
    "data": [
        {
            "id": 1,
            "entity_type": "Item",
            "entity_id": 1,
            "action": "create",
            "user_id": 123,
            "changes": {"name": "Item 1", "price": 10.0},
            "timestamp": "2024-11-27T10:00:00"
        },
        {
            "id": 2,
            "entity_type": "Item",
            "entity_id": 1,
            "action": "update",
            "user_id": 123,
            "changes": {"price": 15.0},
            "timestamp": "2024-11-27T11:00:00"
        }
    ]
}
```

### 获取用户的所有操作

```python
# GET /audit-logs?user_id=123

# 响应：该用户进行的所有操作
```

### 获取特定时间范围的操作

```python
# GET /audit-logs?start_date=2024-11-01&end_date=2024-11-30

# 响应：该时间范围内的所有操作
```

---

## 高级用法

### 追踪数据变化历史

```python
from fastapi_easy.core.audit_log import AuditLogAdapter

adapter = AuditLogAdapter(AuditLog, session)

# 获取实体的完整历史
history = await adapter.get_entity_history(
    entity_type="Item",
    entity_id=1
)

# 重建任意时间点的数据
data_at_time = await adapter.reconstruct_at_time(
    entity_type="Item",
    entity_id=1,
    timestamp="2024-11-27T10:00:00"
)
```

### 比较版本

```python
# 比较两个版本的差异
diff = await adapter.compare_versions(
    entity_type="Item",
    entity_id=1,
    version1_id=1,
    version2_id=2
)

# 响应：
{
    "added": {"price": 15.0},
    "removed": {"price": 10.0},
    "unchanged": {"name": "Item 1"}
}
```

### 导出审计日志

```python
# 导出为 CSV
await adapter.export_to_csv(
    filename="audit_logs.csv",
    filters={"start_date": "2024-11-01"}
)

# 导出为 JSON
await adapter.export_to_json(
    filename="audit_logs.json",
    filters={"user_id": 123}
)
```

---

## 最佳实践

### 1. 记录所有修改

```python
# ✅ 推荐：记录所有修改
logger.log(
    entity_type="Item",
    entity_id=1,
    action="update",
    user_id=user.id,
    changes={"price": 15.0}
)
```

### 2. 定期清理旧日志

```python
# 定期删除 1 年前的日志
from datetime import datetime, timedelta

cutoff_date = datetime.utcnow() - timedelta(days=365)

await adapter.delete_logs_before(cutoff_date)
```

### 3. 保护审计日志

```python
# ✅ 推荐：只有管理员可以查看审计日志
@router.get("/audit-logs")
async def get_audit_logs(current_user: User = Depends(get_current_user)):
    if "admin" not in current_user.roles:
        raise PermissionDeniedError("No permission to view audit logs")
    
    return await adapter.get_logs()
```

### 4. 监控异常活动

```python
# 监控异常删除
logs = await adapter.get_logs(
    filters={"action": "delete"},
    limit=100
)

for log in logs:
    if log.timestamp > datetime.utcnow() - timedelta(hours=1):
        logger.warning(f"Recent deletion: {log}")
```

---

## 常见问题

**Q: 审计日志会影响性能吗？**

A: 会有轻微影响。建议异步记录日志。

**Q: 如何保护审计日志不被篡改？**

A: 使用数据库级别的权限控制，限制对审计日志表的访问。

**Q: 审计日志需要保留多久？**

A: 取决于法规要求，通常 1-7 年。

**Q: 如何处理大量审计日志？**

A: 定期归档和清理，使用分区表。

---

## 总结

审计日志是重要的合规和安全工具：

- ✅ 记录所有修改
- ✅ 追踪数据变化
- ✅ 支持故障排除
- ✅ 满足法规要求

使用审计日志时，记住：

1. 记录所有修改
2. 定期清理旧日志
3. 保护审计日志
4. 监控异常活动

---

**下一步**: [配置参考](../../reference/configuration.md) →
