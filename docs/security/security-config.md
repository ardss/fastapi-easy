# 安全配置

安全配置用于管理 FastAPI-Easy 的所有安全相关设置。本文档介绍如何配置安全选项。

---

## 基础配置

```python
from fastapi_easy.security import SecurityConfig

config = SecurityConfig(
    # 认证配置
    enable_auth=True,
    auth_scheme="bearer",
    
    # 权限配置
    enable_permissions=True,
    default_permission="read",
    
    # 速率限制
    enable_rate_limit=True,
    rate_limit_requests=100,
    rate_limit_period=3600,
    
    # 密码配置
    password_min_length=8,
    password_require_uppercase=True,
    password_require_numbers=True,
    password_require_special=True,
)
```

---

## 认证配置

```python
config = SecurityConfig(
    enable_auth=True,
    auth_scheme="bearer",
    jwt_secret="your-secret-key",
    jwt_algorithm="HS256",
    jwt_expiration=3600,
)
```

---

## 权限配置

```python
config = SecurityConfig(
    enable_permissions=True,
    default_permission="read",
    permission_loader=DatabasePermissionLoader(),
    cache_permissions=True,
    cache_ttl=3600,
)
```

---

## 速率限制配置

```python
config = SecurityConfig(
    enable_rate_limit=True,
    rate_limit_requests=100,
    rate_limit_period=3600,  # 1 小时
    rate_limit_storage="memory",  # 或 "redis"
)
```

---

## 密码策略

```python
config = SecurityConfig(
    password_min_length=12,
    password_require_uppercase=True,
    password_require_lowercase=True,
    password_require_numbers=True,
    password_require_special=True,
    password_special_chars="!@#$%^&*",
)
```

---

## 应用配置

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter

app = FastAPI()

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    security_config=config
)

app.include_router(router)
```

---

## 最佳实践

### 1. 使用环境变量

```python
import os
from fastapi_easy.security import SecurityConfig

config = SecurityConfig(
    jwt_secret=os.getenv("JWT_SECRET"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    jwt_expiration=int(os.getenv("JWT_EXPIRATION", "3600")),
)
```

### 2. 分环境配置

```python
from enum import Enum

class Environment(str, Enum):
    DEV = "dev"
    PROD = "prod"

def get_security_config(env: Environment) -> SecurityConfig:
    if env == Environment.PROD:
        return SecurityConfig(
            enable_auth=True,
            enable_permissions=True,
            enable_rate_limit=True,
            password_min_length=12,
        )
    else:
        return SecurityConfig(
            enable_auth=False,
            password_min_length=6,
        )
```

### 3. 定期更新密钥

```python
# 定期轮换 JWT 密钥
import asyncio

async def rotate_jwt_secret():
    while True:
        await asyncio.sleep(86400)  # 每天轮换一次
        new_secret = generate_new_secret()
        config.jwt_secret = new_secret
```

---

## 常见问题

### Q: 如何更改 JWT 密钥？
A: 更新 `config.jwt_secret` 并重启应用。

### Q: 如何禁用某个安全功能？
A: 在 SecurityConfig 中设置相应的 `enable_*` 为 False。

### Q: 如何自定义密码策略？
A: 继承 SecurityConfig 并覆盖 `validate_password` 方法。
