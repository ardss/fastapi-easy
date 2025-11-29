# 权限加载器指南

权限加载器用于动态加载用户权限，支持从多种数据源加载权限数据。

---

## 概述

### 什么是权限加载器？

权限加载器是一个接口，用于从各种数据源（如数据库、缓存、静态配置等）加载用户权限。

### 为什么需要权限加载器？

- **灵活性**: 支持从多种数据源加载权限
- **可扩展性**: 易于添加新的数据源
- **性能**: 支持缓存优化
- **解耦**: 权限加载逻辑与业务逻辑分离

### 何时使用权限加载器？

- 权限存储在数据库中
- 权限需要动态更新
- 需要支持多种权限源
- 需要性能优化

---

## 基础使用

### 静态权限加载器

从静态配置加载权限：

```python
from fastapi_easy.security import StaticPermissionLoader

# 定义权限映射
permissions_map = {
    "user1": ["read", "write"],
    "user2": ["read"],
    "admin": ["read", "write", "delete", "admin"]
}

# 创建加载器
loader = StaticPermissionLoader(permissions_map)

# 加载权限
permissions = await loader.load_permissions("user1")
# 返回: ["read", "write"]
```

### 数据库权限加载器

从数据库加载权限（占位符实现）：

```python
from fastapi_easy.security import DatabasePermissionLoader

# 创建加载器
loader = DatabasePermissionLoader(db_session=session)

# 加载权限
permissions = await loader.load_permissions("user1")
```

### 缓存权限加载器

添加缓存层以提高性能：

```python
from fastapi_easy.security import (
    StaticPermissionLoader,
    CachedPermissionLoader
)

# 创建基础加载器
base_loader = StaticPermissionLoader(permissions_map)

# 添加缓存
cached_loader = CachedPermissionLoader(
    base_loader,
    cache_ttl=300  # 5 分钟缓存
)

# 使用
permissions = await cached_loader.load_permissions("user1")
```

---

## 高级用法

### 自定义权限加载器

实现自己的权限加载器：

```python
from typing import List

class CustomPermissionLoader:
    """自定义权限加载器"""
    
    async def load_permissions(self, user_id: str) -> List[str]:
        """从自定义源加载权限"""
        # 自定义实现
        if user_id == "admin":
            return ["read", "write", "delete", "admin"]
        else:
            return ["read"]

# 使用
loader = CustomPermissionLoader()
permissions = await loader.load_permissions("user1")
```

### 权限缓存管理

清理缓存：

```python
# 清理特定用户的缓存
cached_loader.clear_cache("user1")

# 清理所有缓存
cached_loader.clear_cache()
```

### 权限检查引擎集成

与权限检查引擎集成：

```python
from fastapi_easy.security import PermissionEngine

# 创建引擎
engine = PermissionEngine(
    permission_loader=cached_loader,
    enable_cache=True
)

# 检查权限
has_permission = await engine.check_permission("user1", "read")
```

---

## 常见问题

### Q: 缓存何时失效？

A: 缓存在 TTL 时间后自动失效。默认 TTL 为 300 秒（5 分钟）。

```python
# 设置自定义 TTL
cached_loader = CachedPermissionLoader(
    base_loader,
    cache_ttl=600  # 10 分钟
)
```

### Q: 如何更新权限？

A: 清理缓存后重新加载：

```python
# 清理缓存
cached_loader.clear_cache("user1")

# 重新加载权限
permissions = await cached_loader.load_permissions("user1")
```

### Q: 性能如何优化？

A: 使用缓存和合理的 TTL 时间：

```python
# 高频访问场景：使用较长的 TTL
cached_loader = CachedPermissionLoader(base_loader, cache_ttl=600)

# 实时更新场景：使用较短的 TTL
cached_loader = CachedPermissionLoader(base_loader, cache_ttl=60)
```

---

## 最佳实践

1. **使用缓存**: 在生产环境中始终使用缓存
2. **合理的 TTL**: 根据业务需求设置合适的缓存时间
3. **错误处理**: 处理加载失败的情况
4. **日志记录**: 记录权限加载操作
5. **性能监控**: 监控缓存命中率

---

## 完整示例

```python
from fastapi import FastAPI, Depends
from fastapi_easy.security import (
    StaticPermissionLoader,
    CachedPermissionLoader,
    PermissionEngine,
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

# 2. 添加缓存
cached_loader = CachedPermissionLoader(loader, cache_ttl=300)

# 3. 创建权限引擎
engine = PermissionEngine(
    permission_loader=cached_loader,
    enable_cache=True
)

# 4. 创建安全配置
jwt_auth = JWTAuth(secret_key="your-secret-key")
config = SecurityConfig(
    jwt_auth=jwt_auth,
    permission_loader=cached_loader
)

# 5. 使用权限检查
@app.get("/data")
async def get_data(current_user: dict = Depends(require_permission("read"))):
    return {"data": "sensitive data"}

@app.post("/data")
async def create_data(current_user: dict = Depends(require_permission("write"))):
    return {"status": "created"}

@app.delete("/data")
async def delete_data(current_user: dict = Depends(require_permission("delete"))):
    return {"status": "deleted"}
```

---

**权限加载器指南完成** ✅
