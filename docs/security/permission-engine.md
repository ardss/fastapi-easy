# 权限检查引擎指南

权限检查引擎是一个统一的权限检查接口，支持多种权限检查方式。

---

## 概述

### 什么是权限检查引擎？

权限检查引擎是一个统一的接口，用于检查用户权限，支持单个权限检查、多权限检查（AND/OR）和资源级权限检查。

### 为什么需要权限检查引擎？

- **统一接口**: 提供统一的权限检查方式
- **灵活性**: 支持多种权限检查方式
- **性能**: 内置缓存支持
- **可扩展性**: 易于扩展新的检查方式

### 何时使用权限检查引擎？

- 需要统一的权限检查接口
- 需要支持复杂的权限逻辑
- 需要性能优化
- 需要资源级权限检查

---

## 基础使用

### 初始化引擎

```python
from fastapi_easy.security import (
    PermissionEngine,
    StaticPermissionLoader,
    CachedPermissionLoader
)

# 创建权限加载器
permissions_map = {
    "user1": ["read", "write"],
    "user2": ["read"],
    "admin": ["read", "write", "delete", "admin"]
}
loader = StaticPermissionLoader(permissions_map)

# 创建权限引擎
engine = PermissionEngine(
    permission_loader=loader,
    enable_cache=True,
    cache_ttl=300
)
```

### 单个权限检查

```python
# 检查用户是否有特定权限
has_permission = await engine.check_permission("user1", "read")
# 返回: True

has_permission = await engine.check_permission("user1", "delete")
# 返回: False
```

### 所有权限检查 (AND)

```python
# 检查用户是否有所有权限
has_all = await engine.check_all_permissions(
    "user1",
    ["read", "write"]
)
# 返回: True

has_all = await engine.check_all_permissions(
    "user1",
    ["read", "write", "delete"]
)
# 返回: False
```

### 任意权限检查 (OR)

```python
# 检查用户是否有任意权限
has_any = await engine.check_any_permission(
    "user1",
    ["delete", "admin"]
)
# 返回: False

has_any = await engine.check_any_permission(
    "user1",
    ["read", "delete"]
)
# 返回: True
```

---

## 高级用法

### 资源级权限检查

```python
from fastapi_easy.security import StaticResourceChecker, CachedResourceChecker

# 创建资源检查器
resources_map = {
    "post_1": {
        "owner_id": "user1",
        "permissions": {
            "user2": ["read"]
        }
    }
}
resource_checker = StaticResourceChecker(resources_map)
cached_checker = CachedResourceChecker(resource_checker)

# 创建引擎
engine = PermissionEngine(
    permission_loader=loader,
    resource_checker=cached_checker,
    enable_cache=True
)

# 检查资源权限
has_permission = await engine.check_permission(
    "user1",
    "read",
    resource_id="post_1"
)
# 返回: True（所有者）

has_permission = await engine.check_permission(
    "user2",
    "read",
    resource_id="post_1"
)
# 返回: True（有显式权限）
```

### 缓存管理

```python
# 清理特定用户的缓存
engine.clear_cache("user1")

# 清理所有缓存
engine.clear_cache()
```

### 禁用缓存

```python
# 创建不使用缓存的引擎
engine = PermissionEngine(
    permission_loader=loader,
    enable_cache=False
)
```

---

## 常见问题

### Q: 如何处理权限更新？

A: 清理缓存后重新检查：

```python
# 权限更新后清理缓存
engine.clear_cache("user1")

# 重新检查
has_permission = await engine.check_permission("user1", "read")
```

### Q: 缓存何时失效？

A: 缓存在 TTL 时间后自动失效。

```python
# 设置自定义 TTL
engine = PermissionEngine(
    permission_loader=loader,
    cache_ttl=600  # 10 分钟
)
```

### Q: 如何处理权限检查失败？

A: 捕获异常并处理：

```python
try:
    has_permission = await engine.check_permission("user1", "read")
except Exception as e:
    logger.error(f"Permission check failed: {e}")
    has_permission = False
```

---

## 最佳实践

1. **使用缓存**: 在生产环境中始终使用缓存
2. **合理的 TTL**: 根据业务需求设置合适的缓存时间
3. **错误处理**: 处理检查失败的情况
4. **日志记录**: 记录权限检查操作
5. **性能监控**: 监控缓存命中率

---

## 完整示例

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi_easy.security import (
    PermissionEngine,
    StaticPermissionLoader,
    StaticResourceChecker,
    CachedResourceChecker,
    SecurityConfig,
    JWTAuth,
    require_permission
)

app = FastAPI()

# 1. 创建权限加载器
permissions_map = {
    "user1": ["read", "write"],
    "user2": ["read"],
    "admin": ["read", "write", "delete", "admin"]
}
loader = StaticPermissionLoader(permissions_map)

# 2. 创建资源检查器
resources_map = {
    "post_1": {
        "owner_id": "user1",
        "permissions": {
            "user2": ["read"]
        }
    }
}
resource_checker = StaticResourceChecker(resources_map)
cached_checker = CachedResourceChecker(resource_checker)

# 3. 创建权限引擎
engine = PermissionEngine(
    permission_loader=loader,
    resource_checker=cached_checker,
    enable_cache=True,
    cache_ttl=300
)

# 4. 创建安全配置
jwt_auth = JWTAuth(secret_key="your-secret-key")
config = SecurityConfig(
    jwt_auth=jwt_auth,
    permission_loader=loader
)

# 5. 使用权限检查
@app.get("/data")
async def get_data(current_user: dict = Depends(require_permission("read"))):
    # 检查单个权限
    has_permission = await engine.check_permission(
        current_user["user_id"],
        "read"
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="No permission")
    
    return {"data": "sensitive data"}

@app.post("/data")
async def create_data(current_user: dict = Depends(require_permission("write"))):
    # 检查多个权限
    has_all = await engine.check_all_permissions(
        current_user["user_id"],
        ["read", "write"]
    )
    
    if not has_all:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return {"status": "created"}

@app.get("/posts/{post_id}")
async def get_post(post_id: str, current_user: dict = Depends(require_permission("read"))):
    # 检查资源权限
    has_permission = await engine.check_permission(
        current_user["user_id"],
        "read",
        resource_id=post_id
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="No permission")
    
    return {"post_id": post_id, "content": "..."}

@app.put("/posts/{post_id}")
async def update_post(post_id: str, current_user: dict = Depends(require_permission("write"))):
    # 检查所有权
    is_owner = await cached_checker.check_owner(
        current_user["user_id"],
        post_id
    )
    
    if not is_owner:
        raise HTTPException(status_code=403, detail="Not owner")
    
    return {"post_id": post_id, "status": "updated"}
```

---

**权限检查引擎指南完成** ✅
