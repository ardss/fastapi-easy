# 权限控制指南

## 概述

FastAPI-Easy 提供了灵活的权限控制系统，支持：

- 角色权限检查 (RBAC)
- 细粒度权限控制
- 多种权限检查方式
- 完整的错误处理

## 快速开始

### 1. 定义角色和权限

```python
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    USER = "user"

class Permission(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
```

### 2. 创建带权限检查的端点

```python
from fastapi import Depends
from fastapi_easy.security import require_role, require_permission

# 要求至少一个角色
@app.post("/items")
async def create_item(
    item: Item,
    current_user: dict = Depends(require_role("editor", "admin")),
):
    """创建项目 - 需要 editor 或 admin 角色"""
    return {"item": item, "created_by": current_user["user_id"]}

# 要求所有角色
@app.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    current_user: dict = Depends(require_all_roles("admin", "moderator")),
):
    """删除项目 - 需要 admin 和 moderator 角色"""
    return {"message": "Item deleted"}

# 要求特定权限
@app.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item: Item,
    current_user: dict = Depends(require_permission("update")),
):
    """更新项目 - 需要 update 权限"""
    return {"item": item, "updated_by": current_user["user_id"]}
```

## 权限检查装饰器

### require_role(*roles)

要求用户至少拥有一个指定的角色。

```python
@app.get("/admin-panel")
async def admin_panel(
    current_user: dict = Depends(require_role("admin")),
):
    """管理员面板 - 只有 admin 角色可访问"""
    return {"message": "Welcome admin"}
```

### require_all_roles(*roles)

要求用户拥有所有指定的角色。

```python
@app.get("/super-admin")
async def super_admin(
    current_user: dict = Depends(require_all_roles("admin", "moderator")),
):
    """超级管理员 - 需要 admin 和 moderator 角色"""
    return {"message": "Welcome super admin"}
```

### require_permission(*permissions)

要求用户至少拥有一个指定的权限。

```python
@app.post("/publish")
async def publish(
    content: str,
    current_user: dict = Depends(require_permission("publish", "admin")),
):
    """发布内容 - 需要 publish 或 admin 权限"""
    return {"content": content, "published_by": current_user["user_id"]}
```

### require_all_permissions(*permissions)

要求用户拥有所有指定的权限。

```python
@app.post("/sensitive-operation")
async def sensitive_operation(
    current_user: dict = Depends(require_all_permissions("read", "write", "delete")),
):
    """敏感操作 - 需要 read、write 和 delete 权限"""
    return {"message": "Operation completed"}
```

## 在 JWT Token 中包含权限

```python
from fastapi_easy.security import init_jwt_auth

jwt_auth = init_jwt_auth()

@app.post("/auth/login")
async def login(username: str, password: str):
    """登录并返回包含权限的 Token"""
    # 验证用户
    user = authenticate_user(username, password)
    
    # 获取用户角色和权限
    roles = get_user_roles(user.id)
    permissions = get_user_permissions(user.id)
    
    # 创建 Token
    access_token = jwt_auth.create_access_token(
        subject=str(user.id),
        roles=roles,
        permissions=permissions,
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
```

## 自定义权限检查

如果需要更复杂的权限检查逻辑，可以创建自定义装饰器：

```python
from fastapi import Depends, HTTPException

def require_resource_owner(resource_id: int):
    """要求用户是资源的所有者"""
    async def check_owner(current_user: dict = Depends(get_current_user)):
        resource = get_resource(resource_id)
        if resource.owner_id != int(current_user["user_id"]):
            raise HTTPException(
                status_code=403,
                detail="You are not the owner of this resource",
            )
        return current_user
    
    return Depends(check_owner)

@app.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    current_user: dict = Depends(require_resource_owner(item_id)),
):
    """删除项目 - 只有所有者可删除"""
    delete_resource(item_id)
    return {"message": "Item deleted"}
```

## 权限检查流程

```
请求到达
    ↓
检查 Authorization Header
    ↓
验证 JWT Token
    ↓
检查 Token 是否过期
    ↓
提取用户信息 (ID、角色、权限)
    ↓
检查权限要求
    ↓
✓ 通过 → 执行业务逻辑
✗ 失败 → 返回 403 Forbidden
```

## 错误处理

```python
from fastapi_easy.security import (
    AuthorizationError,
    InsufficientPermissionError,
)

@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request, exc):
    return {
        "error": "Authorization Failed",
        "detail": exc.message,
        "status_code": 403,
    }

@app.exception_handler(InsufficientPermissionError)
async def insufficient_permission_handler(request, exc):
    return {
        "error": "Insufficient Permission",
        "detail": exc.message,
        "status_code": 403,
    }
```

## 最佳实践

### 1. 最小权限原则

只授予用户完成工作所需的最小权限。

```python
# ❌ 不好：给所有用户 admin 权限
user.roles = ["admin"]

# ✅ 好：只给需要的权限
user.roles = ["editor"]
user.permissions = ["read", "create", "update"]
```

### 2. 定期审计权限

定期检查用户权限，移除不需要的权限。

```python
# 审计用户权限
audit_logs = audit_logger.get_user_activity(user_id=user_id)
for log in audit_logs:
    if log["event_type"] == "permission_denied":
        # 分析被拒绝的权限
        pass
```

### 3. 使用角色而不是直接权限

使用角色来管理权限更容易维护。

```python
# ❌ 不好：直接分配权限
user.permissions = ["read", "create", "update", "delete", "publish"]

# ✅ 好：使用角色
user.roles = ["editor"]  # editor 角色包含所有这些权限
```

### 4. 记录权限拒绝

记录所有权限拒绝以便审计。

```python
from fastapi_easy.security import AuditEventType

@app.get("/sensitive-data")
async def get_sensitive_data(
    current_user: dict = Depends(require_permission("admin")),
):
    # 权限检查失败时自动记录
    # audit_logger.log(
    #     event_type=AuditEventType.PERMISSION_DENIED,
    #     user_id=current_user["user_id"],
    #     resource="sensitive-data",
    # )
    return {"data": "sensitive"}
```

## 完整示例

参考 `examples/06_with_permissions.py` 获取完整的工作示例。
