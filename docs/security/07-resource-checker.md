# 资源检查器指南

资源检查器用于检查用户是否拥有或有权限访问特定资源。

---

## 概述

### 什么是资源检查器？

资源检查器是一个接口，用于检查用户对资源的访问权限，包括所有权检查和权限检查。

### 为什么需要资源检查器？

- **细粒度控制**: 支持资源级别的权限控制
- **所有权检查**: 验证用户是否拥有资源
- **灵活性**: 支持多种资源类型
- **可扩展性**: 易于添加新的资源类型

### 何时使用资源检查器？

- 用户只能访问自己的资源
- 需要资源级别的权限控制
- 需要支持共享资源
- 需要细粒度的访问控制

---

## 基础使用

### 静态资源检查器

从静态配置检查资源权限：

```python
from fastapi_easy.security import StaticResourceChecker

# 定义资源映射
resources_map = {
    "post_1": {
        "owner_id": "user1",
        "permissions": {
            "user2": ["read"],
            "user3": ["read", "comment"]
        }
    },
    "post_2": {
        "owner_id": "user2",
        "permissions": {
            "user1": ["read"]
        }
    }
}

# 创建检查器
checker = StaticResourceChecker(resources_map)

# 检查所有权
is_owner = await checker.check_owner("user1", "post_1")
# 返回: True

# 检查权限
has_permission = await checker.check_permission("user2", "post_1", "read")
# 返回: True
```

### 数据库资源检查器

从数据库检查资源权限（占位符实现）：

```python
from fastapi_easy.security import DatabaseResourceChecker

# 创建检查器
checker = DatabaseResourceChecker(db_session=session)

# 检查所有权
is_owner = await checker.check_owner("user1", "post_1")

# 检查权限
has_permission = await checker.check_permission("user1", "post_1", "read")
```

### 缓存资源检查器

添加缓存层以提高性能：

```python
from fastapi_easy.security import (
    StaticResourceChecker,
    CachedResourceChecker
)

# 创建基础检查器
base_checker = StaticResourceChecker(resources_map)

# 添加缓存
cached_checker = CachedResourceChecker(
    base_checker,
    cache_ttl=300  # 5 分钟缓存
)

# 使用
is_owner = await cached_checker.check_owner("user1", "post_1")
```

---

## 高级用法

### 自定义资源检查器

实现自己的资源检查器：

```python
class CustomResourceChecker:
    """自定义资源检查器"""
    
    async def check_owner(self, user_id: str, resource_id: str) -> bool:
        """检查用户是否拥有资源"""
        # 自定义实现
        resource = await get_resource(resource_id)
        return resource.owner_id == user_id
    
    async def check_permission(
        self,
        user_id: str,
        resource_id: str,
        permission: str
    ) -> bool:
        """检查用户是否有资源权限"""
        # 首先检查所有权
        if await self.check_owner(user_id, resource_id):
            return True
        
        # 然后检查显式权限
        resource = await get_resource(resource_id)
        return permission in resource.get_user_permissions(user_id)

# 使用
checker = CustomResourceChecker()
is_owner = await checker.check_owner("user1", "post_1")
```

### 资源缓存管理

清理缓存：

```python
# 清理特定用户的缓存
cached_checker.clear_cache("user1")

# 清理特定资源的缓存
cached_checker.clear_cache("post_1")

# 清理所有缓存
cached_checker.clear_cache()
```

### 权限检查引擎集成

与权限检查引擎集成：

```python
from fastapi_easy.security import PermissionEngine

# 创建引擎
engine = PermissionEngine(
    permission_loader=permission_loader,
    resource_checker=cached_checker,
    enable_cache=True
)

# 检查资源权限
has_permission = await engine.check_permission(
    "user1",
    "read",
    resource_id="post_1"
)
```

---

## 常见问题

### Q: 所有权检查和权限检查的区别？

A: 所有权检查验证用户是否拥有资源，权限检查验证用户是否有特定权限。

```python
# 所有权检查：用户是否拥有资源
is_owner = await checker.check_owner("user1", "post_1")

# 权限检查：用户是否有权限
has_permission = await checker.check_permission("user1", "post_1", "read")
```

### Q: 缓存何时失效？

A: 缓存在 TTL 时间后自动失效。

```python
# 设置自定义 TTL
cached_checker = CachedResourceChecker(
    base_checker,
    cache_ttl=600  # 10 分钟
)
```

### Q: 如何处理权限更新？

A: 清理缓存后重新检查：

```python
# 清理缓存
cached_checker.clear_cache("user1")

# 重新检查
has_permission = await cached_checker.check_permission("user1", "post_1", "read")
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
    StaticResourceChecker,
    CachedResourceChecker,
    PermissionEngine,
    require_permission
)

app = FastAPI()

# 1. 定义资源
resources_map = {
    "post_1": {
        "owner_id": "user1",
        "permissions": {
            "user2": ["read"],
            "user3": ["read", "comment"]
        }
    }
}

# 2. 创建资源检查器
checker = StaticResourceChecker(resources_map)
cached_checker = CachedResourceChecker(checker, cache_ttl=300)

# 3. 创建权限引擎
engine = PermissionEngine(
    permission_loader=permission_loader,
    resource_checker=cached_checker,
    enable_cache=True
)

# 4. 使用资源权限检查
@app.get("/posts/{post_id}")
async def get_post(
    post_id: str,
    current_user: dict = Depends(require_permission("read"))
):
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
async def update_post(
    post_id: str,
    current_user: dict = Depends(require_permission("write"))
):
    # 检查所有权
    is_owner = await cached_checker.check_owner(
        current_user["user_id"],
        post_id
    )
    
    if not is_owner:
        raise HTTPException(status_code=403, detail="Not owner")
    
    return {"post_id": post_id, "status": "updated"}

@app.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_user: dict = Depends(require_permission("delete"))
):
    # 检查所有权
    is_owner = await cached_checker.check_owner(
        current_user["user_id"],
        post_id
    )
    
    if not is_owner:
        raise HTTPException(status_code=403, detail="Not owner")
    
    return {"post_id": post_id, "status": "deleted"}
```

---

**资源检查器指南完成** ✅
