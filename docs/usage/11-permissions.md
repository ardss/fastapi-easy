# 权限控制

权限控制是保护 API 的关键。fastapi-easy 支持基于角色的访问控制（RBAC）和基于属性的访问控制（ABAC）。

---

## 什么是权限控制？

权限控制可以：

- ✅ 限制用户访问
- ✅ 保护敏感数据
- ✅ 实现多租户
- ✅ 审计用户操作

---

## 基于角色的访问控制（RBAC）

### 定义角色和权限

```python
from fastapi_easy.core.permissions import Role, Permission, RoleBasedAccessControl

# 定义权限
class Permission(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ADMIN = "admin"

# 定义角色
class Role(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    USER = "user"

# 创建 RBAC 实例
rbac = RoleBasedAccessControl()

# 配置角色权限
rbac.add_permission(Role.ADMIN, Permission.ADMIN)
rbac.add_permission(Role.EDITOR, Permission.CREATE)
rbac.add_permission(Role.EDITOR, Permission.READ)
rbac.add_permission(Role.EDITOR, Permission.UPDATE)
rbac.add_permission(Role.VIEWER, Permission.READ)
rbac.add_permission(Role.USER, Permission.READ)
```

### 检查权限

```python
# 检查用户是否有权限
if rbac.has_permission(Role.EDITOR, Permission.UPDATE):
    # 允许更新
    pass
else:
    # 拒绝更新
    raise PermissionDeniedError("No permission to update")
```

---

## 基于属性的访问控制（ABAC）

### 定义策略

```python
from fastapi_easy.core.permissions import AttributeBasedAccessControl

abac = AttributeBasedAccessControl()

# 添加策略：只有所有者可以删除自己的项目
abac.add_policy(
    name="owner_delete",
    resource="item",
    action="delete",
    condition=lambda context: context.user_id == context.resource.owner_id
)

# 添加策略：只有管理员可以删除任何项目
abac.add_policy(
    name="admin_delete",
    resource="item",
    action="delete",
    condition=lambda context: "admin" in context.user_roles
)
```

### 评估策略

```python
from fastapi_easy.core.permissions import PermissionContext

# 创建权限上下文
context = PermissionContext(
    user_id=user.id,
    roles=user.roles,
    permissions=user.permissions,
    attributes={"resource": item}
)

# 检查是否允许删除
if abac.evaluate(context, "item", "delete"):
    # 允许删除
    pass
else:
    # 拒绝删除
    raise PermissionDeniedError("No permission to delete this item")
```

---

## 集成到 CRUDRouter

### 配置权限

```python
from fastapi_easy import CRUDRouter
from fastapi_easy.core.permissions import PermissionConfig

config = PermissionConfig(
    enabled=True,
    default_role=Role.USER,
    require_authentication=True,
)

router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    permission_config=config,
    rbac=rbac,
    abac=abac,
)
```

### 在钩子中检查权限

```python
async def before_create(context):
    # 检查创建权限
    if not rbac.has_permission(context.user_role, Permission.CREATE):
        raise PermissionDeniedError("No permission to create")

async def before_delete(context):
    # 检查删除权限
    if not abac.evaluate(context, "item", "delete"):
        raise PermissionDeniedError("No permission to delete this item")

router.hooks.register("before_create", before_create)
router.hooks.register("before_delete", before_delete)
```

---

## 高级用法

### 多租户支持

```python
# 添加策略：用户只能访问自己租户的数据
abac.add_policy(
    name="tenant_isolation",
    resource="item",
    action="read",
    condition=lambda context: context.tenant_id == context.resource.tenant_id
)
```

### 动态权限

```python
# 根据时间限制访问
abac.add_policy(
    name="time_based_access",
    resource="item",
    action="update",
    condition=lambda context: context.is_business_hours()
)

# 根据数据敏感性限制访问
abac.add_policy(
    name="data_sensitivity",
    resource="item",
    action="read",
    condition=lambda context: context.user_clearance_level >= context.resource.sensitivity_level
)
```

---

## 最佳实践

### 1. 使用最小权限原则

```python
# ✅ 推荐：最小权限
rbac.add_permission(Role.USER, Permission.READ)

# ❌ 不推荐：过度权限
rbac.add_permission(Role.USER, Permission.ADMIN)
```

### 2. 定期审计权限

```python
# 定期检查用户权限
for user in users:
    permissions = rbac.get_permissions(user.role)
    logger.info(f"User {user.id} permissions: {permissions}")
```

### 3. 使用权限缓存

```python
# 缓存权限检查结果
from functools import lru_cache

@lru_cache(maxsize=1000)
def check_permission(role: str, permission: str) -> bool:
    return rbac.has_permission(role, permission)
```

### 4. 记录权限拒绝

```python
# 记录所有权限拒绝
try:
    if not rbac.has_permission(user_role, permission):
        raise PermissionDeniedError()
except PermissionDeniedError:
    logger.warning(f"Permission denied: {user_id} -> {permission}")
    raise
```

---

## 常见问题

**Q: RBAC 和 ABAC 有什么区别？**

A: RBAC 基于用户角色，ABAC 基于属性和条件。ABAC 更灵活。

**Q: 如何实现多租户？**

A: 使用 ABAC 添加租户隔离策略。

**Q: 如何处理权限拒绝？**

A: 抛出 `PermissionDeniedError` 异常，由中间件处理。

**Q: 权限检查会影响性能吗？**

A: 会有轻微影响，建议使用缓存。

---

## 总结

权限控制是保护 API 的关键：

- ✅ 使用 RBAC 进行基本权限管理
- ✅ 使用 ABAC 进行复杂权限管理
- ✅ 遵循最小权限原则
- ✅ 定期审计权限

---

**下一步**: [审计日志](12-audit-logging.md) →
