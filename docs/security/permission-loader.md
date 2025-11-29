# 权限加载器

权限加载器负责从数据库或其他数据源加载用户权限。本文档介绍如何使用权限加载器。

---

## 什么是权限加载器

权限加载器是一个可插拔的组件，用于：

- 从数据库加载用户权限
- 从缓存加载权限
- 支持自定义权限源
- 支持权限缓存

---

## 基础使用

```python
from fastapi_easy.security import PermissionLoader

class DatabasePermissionLoader(PermissionLoader):
    async def load_permissions(self, user_id: int) -> List[str]:
        # 从数据库加载权限
        permissions = await db.query(Permission).filter(
            Permission.user_id == user_id
        ).all()
        return [p.name for p in permissions]
```

---

## 配置权限加载器

```python
from fastapi_easy import CRUDRouter
from fastapi_easy.security import PermissionConfig

config = PermissionConfig(
    enabled=True,
    permission_loader=DatabasePermissionLoader()
)

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    permission_config=config
)
```

---

## 权限缓存

```python
from fastapi_easy.security import CachedPermissionLoader

class CachedDatabasePermissionLoader(CachedPermissionLoader):
    async def load_permissions(self, user_id: int) -> List[str]:
        # 先从缓存查询
        cached = await self.cache.get(f"user:{user_id}:permissions")
        if cached:
            return cached
        
        # 从数据库加载
        permissions = await db.query(Permission).filter(
            Permission.user_id == user_id
        ).all()
        
        # 缓存结果
        await self.cache.set(
            f"user:{user_id}:permissions",
            [p.name for p in permissions],
            ttl=3600
        )
        
        return [p.name for p in permissions]
```

---

## 最佳实践

### 1. 使用缓存

```python
# 启用权限缓存
config = PermissionConfig(
    enabled=True,
    permission_loader=CachedDatabasePermissionLoader(),
    cache_ttl=3600  # 1 小时缓存
)
```

### 2. 处理权限变更

```python
# 权限变更时清除缓存
async def update_user_permissions(user_id: int, permissions: List[str]):
    # 更新数据库
    await db.update_permissions(user_id, permissions)
    
    # 清除缓存
    await cache.delete(f"user:{user_id}:permissions")
```

### 3. 异步加载

```python
# 使用异步数据库查询
async def load_permissions(self, user_id: int) -> List[str]:
    async with get_db() as db:
        permissions = await db.query(Permission).filter(
            Permission.user_id == user_id
        ).all()
        return [p.name for p in permissions]
```

---

## 常见问题

### Q: 如何处理权限加载失败？
A: 返回空列表，用户将被拒绝访问。

### Q: 如何支持多个权限源？
A: 实现 CompositePermissionLoader，组合多个加载器。

### Q: 性能如何优化？
A: 使用缓存和批量加载权限。
