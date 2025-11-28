# JWT 认证指南

## 概述

FastAPI-Easy 提供了完整的 JWT (JSON Web Token) 认证系统，支持：

- JWT Token 生成和验证
- Token 刷新机制
- 自定义密钥和算法
- 完整的错误处理

## 快速开始

### 1. 初始化 JWT 认证

```python
from fastapi import FastAPI
from fastapi_easy.security import init_jwt_auth

app = FastAPI()

# 初始化 JWT 认证
jwt_auth = init_jwt_auth(
    secret_key="your-secret-key-change-in-production",
    algorithm="HS256",
    access_token_expire_minutes=15,
    refresh_token_expire_days=7,
)
```

### 2. 创建登录端点

```python
from fastapi import HTTPException
from fastapi_easy.security import TokenResponse, TokenRequest

@app.post("/auth/login", response_model=TokenResponse)
async def login(request: TokenRequest):
    """用户登录端点"""
    # 验证用户凭证 (这里使用模拟数据)
    if request.username != "admin" or request.password != "password":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 生成 Token
    access_token = jwt_auth.create_access_token(
        subject="user123",
        roles=["admin"],
    )
    refresh_token = jwt_auth.create_refresh_token(subject="user123")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60,  # 15 分钟
    )
```

### 3. 保护端点

```python
from fastapi import Depends
from fastapi_easy.security import get_current_user

@app.get("/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """获取当前用户资料"""
    return {
        "user_id": current_user["user_id"],
        "roles": current_user["roles"],
    }
```

### 4. 刷新 Token

```python
from fastapi_easy.security import RefreshTokenRequest

@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh(request: RefreshTokenRequest):
    """刷新访问令牌"""
    try:
        access_token = jwt_auth.refresh_access_token(
            refresh_token=request.refresh_token,
        )
        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,
            expires_in=15 * 60,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
```

## 环境变量配置

你可以使用环境变量来配置 JWT 密钥：

```bash
# .env
JWT_SECRET_KEY=your-super-secret-key-here
```

然后在代码中：

```python
from fastapi_easy.security import init_jwt_auth

# 自动从环境变量读取 JWT_SECRET_KEY
jwt_auth = init_jwt_auth()
```

## Token 格式

JWT Token 包含以下信息：

```json
{
  "sub": "user123",           // 用户 ID
  "roles": ["admin", "user"], // 用户角色
  "permissions": ["read"],    // 用户权限
  "iat": 1234567890,          // 签发时间
  "exp": 1234568790,          // 过期时间
  "type": "access"            // Token 类型 (access/refresh)
}
```

## 最佳实践

### 1. 使用强密钥

```python
import secrets

# 生成强密钥
secret_key = secrets.token_urlsafe(32)
```

### 2. 设置合理的过期时间

```python
# 访问令牌：15 分钟
# 刷新令牌：7 天
jwt_auth = init_jwt_auth(
    access_token_expire_minutes=15,
    refresh_token_expire_days=7,
)
```

### 3. 始终使用 HTTPS

在生产环境中，始终使用 HTTPS 来传输 Token。

### 4. 在客户端安全存储 Token

```javascript
// 不要在 localStorage 中存储 Token
// 使用 HttpOnly Cookie 或内存存储
localStorage.setItem('token', token);  // ❌ 不安全

// 更好的方式：使用 HttpOnly Cookie
document.cookie = `token=${token}; HttpOnly; Secure; SameSite=Strict`;
```

### 5. 定期轮换密钥

在生产环境中，定期轮换 JWT 密钥以提高安全性。

## 错误处理

```python
from fastapi_easy.security import (
    InvalidTokenError,
    TokenExpiredError,
    AuthenticationError,
)

@app.get("/protected")
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    """受保护的端点"""
    try:
        # 你的业务逻辑
        pass
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Token expired")
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Authentication failed")
```

## 完整示例

参考 `examples/06_with_permissions.py` 获取完整的工作示例。

```bash
# 运行示例
uvicorn examples.06_with_permissions:app --reload

# 测试登录
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password_123"}'

# 使用 Token 访问受保护的端点
curl -X GET http://localhost:8000/profile \
  -H "Authorization: Bearer <your_token_here>"
```
