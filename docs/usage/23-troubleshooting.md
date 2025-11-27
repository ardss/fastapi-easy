# 故障排除指南

本指南帮助解决使用 fastapi-easy 时遇到的常见问题。

---

## 常见问题

### 1. 数据库连接错误

**问题**: `sqlalchemy.exc.OperationalError: could not connect to server`

**解决方案**:
- 检查数据库 URL 是否正确
- 确保数据库服务正在运行
- 检查网络连接

```python
# 验证连接
async with engine.begin() as conn:
    await conn.execute(text("SELECT 1"))
```

### 2. 权限错误

**问题**: `PermissionDeniedError: No permission to ...`

**解决方案**:
- 检查用户角色和权限
- 验证权限配置
- 查看审计日志

```python
# 检查权限
if rbac.has_permission(user_role, permission):
    # 允许操作
    pass
```

### 3. 验证错误

**问题**: `ValidationError: Invalid input`

**解决方案**:
- 检查输入数据格式
- 验证必填字段
- 查看错误详情

```python
# 添加详细的验证错误信息
try:
    result = await adapter.create(data)
except ValidationError as e:
    logger.error(f"Validation error: {e.details}")
```

### 4. 性能问题

**问题**: 查询速度慢

**解决方案**:
- 添加数据库索引
- 启用缓存
- 使用分页
- 优化查询

```python
# 启用缓存
@CachedOperation(cache, ttl=3600)
async def get_items():
    return await adapter.get_all()
```

---

## 调试技巧

### 1. 启用详细日志

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
```

### 2. 使用 print 调试

```python
print(f"Debug: {variable}")
```

### 3. 使用 pdb 调试

```python
import pdb; pdb.set_trace()
```

---

## 获取帮助

1. 查看文档
2. 查看示例代码
3. 查看测试用例
4. 提交 Issue

---

**完成！** 🎉
