# 安全配置指南

安全配置用于统一管理所有安全相关的组件。

---

## 概述

### 什么是安全配置？

安全配置是一个中央配置类，用于管理 JWT 认证、权限加载、资源检查和审计日志等所有安全组件。

### 为什么需要安全配置？

- **集中管理**: 所有安全组件在一个地方
- **易于使用**: 简化安全组件的初始化
- **可维护性**: 便于修改和扩展
- **一致性**: 确保安全配置的一致性

### 何时使用安全配置？

- 需要管理多个安全组件
- 需要支持多环境配置
- 需要动态配置安全组件
- 需要集中管理安全策略

---

## 基础使用

### 创建配置

```python
from fastapi_easy.security import (
    SecurityConfig,
    JWTAuth,
    StaticPermissionLoader,
    StaticResourceChecker,
    AuditLogger
)

# 创建 JWT 认证
jwt_auth = JWTAuth(secret_key="your-secret-key")

# 创建权限加载器
permissions_map = {
    "user1": ["read", "write"],
    "user2": ["read"]
}
permission_loader = StaticPermissionLoader(permissions_map)

# 创建资源检查器
resources_map = {
    "post_1": {
        "owner_id": "user1",
        "permissions": {}
    }
}
resource_checker = StaticResourceChecker(resources_map)

# 创建审计日志
audit_logger = AuditLogger()

# 创建安全配置
config = SecurityConfig(
    jwt_auth=jwt_auth,
    permission_loader=permission_loader,
    resource_checker=resource_checker,
    audit_logger=audit_logger
)
```

### 从环境变量创建配置

```python
# 从环境变量创建配置
config = SecurityConfig.from_env()

# 环境变量：
# JWT_SECRET_KEY=your-secret-key
```

### 访问组件

```python
# 获取 JWT 认证
jwt_auth = config.get_jwt_auth()

# 获取权限加载器
permission_loader = config.get_permission_loader()

# 获取资源检查器
resource_checker = config.get_resource_checker()

# 获取审计日志
audit_logger = config.get_audit_logger()
```

---

## 高级用法

### 多环境配置

```python
import os

def get_security_config():
    """根据环境创建安全配置"""
    env = os.getenv("ENV", "development")
    
    if env == "production":
        # 生产环境配置
        jwt_auth = JWTAuth(secret_key=os.getenv("JWT_SECRET_KEY"))
        permission_loader = DatabasePermissionLoader(db_session=db_session)
        resource_checker = DatabaseResourceChecker(db_session=db_session)
    else:
        # 开发环境配置
        jwt_auth = JWTAuth(secret_key="dev-secret-key")
        permission_loader = StaticPermissionLoader(DEV_PERMISSIONS)
        resource_checker = StaticResourceChecker(DEV_RESOURCES)
    
    return SecurityConfig(
        jwt_auth=jwt_auth,
        permission_loader=permission_loader,
        resource_checker=resource_checker
    )

config = get_security_config()
```

### 配置验证

```python
# 验证配置
config.validate()

# 如果配置无效，会抛出异常
```

### 配置扩展

```python
# 创建基础配置
config = SecurityConfig(jwt_auth=jwt_auth)

# 添加权限加载器
config.permission_loader = permission_loader

# 添加资源检查器
config.resource_checker = resource_checker
```

---

## 常见问题

### Q: 如何处理配置错误？

A: 使用 try-except 捕获异常：

```python
try:
    config = SecurityConfig(jwt_auth=None)
except ValueError as e:
    logger.error(f"Configuration error: {e}")
```

### Q: 如何从环境变量读取配置？

A: 使用 `from_env()` 方法：

```python
# 设置环境变量
os.environ["JWT_SECRET_KEY"] = "your-secret-key"

# 创建配置
config = SecurityConfig.from_env()
```

### Q: 如何支持多个安全配置？

A: 创建多个配置实例：

```python
# 配置 1
config1 = SecurityConfig(jwt_auth=jwt_auth1)

# 配置 2
config2 = SecurityConfig(jwt_auth=jwt_auth2)
```

---

## 最佳实践

1. **集中管理**: 在一个地方创建和管理安全配置
2. **环境变量**: 使用环境变量存储敏感信息
3. **验证配置**: 在应用启动时验证配置
4. **错误处理**: 处理配置错误
5. **日志记录**: 记录配置操作

---

## 完整示例

```python
from fastapi import FastAPI
from fastapi_easy.security import (
    SecurityConfig,
    JWTAuth,
    StaticPermissionLoader,
    StaticResourceChecker,
    PermissionEngine,
    require_permission
)

app = FastAPI()

# 1. 创建安全配置
permissions_map = {
    "user1": ["read", "write"],
    "user2": ["read"],
    "admin": ["read", "write", "delete", "admin"]
}
permission_loader = StaticPermissionLoader(permissions_map)

resources_map = {
    "post_1": {
        "owner_id": "user1",
        "permissions": {}
    }
}
resource_checker = StaticResourceChecker(resources_map)

jwt_auth = JWTAuth(secret_key="your-secret-key")

config = SecurityConfig(
    jwt_auth=jwt_auth,
    permission_loader=permission_loader,
    resource_checker=resource_checker
)

# 2. 验证配置
config.validate()

# 3. 创建权限引擎
engine = PermissionEngine(
    permission_loader=config.get_permission_loader(),
    resource_checker=config.get_resource_checker(),
    enable_cache=True
)

# 4. 使用配置
@app.get("/data")
async def get_data(current_user: dict = Depends(require_permission("read"))):
    # 使用权限引擎检查权限
    has_permission = await engine.check_permission(
        current_user["user_id"],
        "read"
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail="No permission")
    
    # 记录审计日志
    config.get_audit_logger().log(
        event_type="data_access",
        user_id=current_user["user_id"],
        action="read",
        status="success"
    )
    
    return {"data": "sensitive data"}

@app.on_event("startup")
async def startup():
    """应用启动时验证配置"""
    try:
        config.validate()
        print("Security configuration is valid")
    except Exception as e:
        print(f"Configuration error: {e}")
        raise
```

---

**安全配置指南完成** ✅
