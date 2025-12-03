# 安全最佳实践

## 概述

本指南提供了使用 FastAPI-Easy 安全模块的最佳实践。

## 1. 密钥管理

### ✅ 正确做法

```python
# 使用环境变量
import os
from fastapi_easy.security import init_jwt_auth

secret_key = os.getenv("JWT_SECRET_KEY")
if not secret_key:
    raise ValueError("JWT_SECRET_KEY environment variable is not set")

jwt_auth = init_jwt_auth(secret_key=secret_key)
```

### ❌ 错误做法

```python
# 不要硬编码密钥
jwt_auth = init_jwt_auth(secret_key="my-secret-key-123")

# 不要在代码中提交密钥
# git add .env  # ❌ 错误
```

### 密钥轮换

```python
# 定期轮换密钥
# 1. 生成新密钥
new_secret_key = secrets.token_urlsafe(32)

# 2. 创建新的 JWT 认证实例
new_jwt_auth = init_jwt_auth(secret_key=new_secret_key)

# 3. 允许旧密钥的 Token 继续工作（过渡期）
# 4. 更新环境变量
# 5. 重启应用
```

## 2. 密码安全

### ✅ 正确做法

```python
from fastapi_easy.security import PasswordManager
import re

password_manager = PasswordManager(rounds=12)

def validate_password_strength(password: str) -> bool:
    """验证密码强度"""
    # 至少 12 个字符
    if len(password) < 12:
        return False
    
    # 包含大写字母
    if not re.search(r'[A-Z]', password):
        return False
    
    # 包含小写字母
    if not re.search(r'[a-z]', password):
        return False
    
    # 包含数字
    if not re.search(r'\d', password):
        return False
    
    # 包含特殊字符
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    
    return True

@app.post("/auth/register")
async def register(username: str, password: str):
    if not validate_password_strength(password):
        raise HTTPException(
            status_code=400,
            detail="Password is too weak",
        )
    
    hashed = password_manager.hash_password(password)
    # 保存用户
```

### ❌ 错误做法

```python
# 不要存储明文密码
user.password = password  # ❌ 错误

# 不要使用简单的哈希
import hashlib
user.password = hashlib.md5(password.encode()).hexdigest()  # ❌ 错误

# 不要允许弱密码
if len(password) >= 4:  # ❌ 太弱
    user.password = password_manager.hash_password(password)
```

## 3. Token 安全

### ✅ 正确做法

```python
# 设置合理的过期时间
jwt_auth = init_jwt_auth(
    access_token_expire_minutes=15,    # 短期访问令牌
    refresh_token_expire_days=7,       # 长期刷新令牌
)

# 在客户端使用 HttpOnly Cookie
@app.post("/auth/login")
async def login(username: str, password: str):
    access_token = jwt_auth.create_access_token(subject=str(user.id))
    refresh_token = jwt_auth.create_refresh_token(subject=str(user.id))
    
    response = JSONResponse(
        content={"message": "Login successful"},
        status_code=200,
    )
    
    # 使用 HttpOnly Cookie 存储 Token
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,  # 仅 HTTPS
        samesite="strict",
        max_age=15 * 60,  # 15 分钟
    )
    
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7 天
    )
    
    return response
```

### ❌ 错误做法

```python
# 不要在 localStorage 中存储 Token
# localStorage.setItem('token', token)  # ❌ 易受 XSS 攻击

# 不要设置过长的过期时间
jwt_auth = init_jwt_auth(
    access_token_expire_minutes=10080,  # ❌ 7 天太长
)

# 不要在 URL 中传输 Token
# GET /api/data?token=xyz  # ❌ 错误
```

## 4. 登录安全

### ✅ 正确做法

```python
from fastapi_easy.security import LoginAttemptTracker

tracker = LoginAttemptTracker(
    max_attempts=5,
    lockout_duration_minutes=15,
)

@app.post("/auth/login")
async def login(username: str, password: str):
    # 检查是否被锁定
    if tracker.is_locked_out(username):
        remaining = tracker.get_lockout_remaining_seconds(username)
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Try again in {remaining} seconds",
        )
    
    # 验证用户
    user = authenticate_user(username, password)
    
    if not user:
        tracker.record_attempt(username, success=False)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 成功
    tracker.record_attempt(username, success=True)
    
    # 生成 Token
    access_token = jwt_auth.create_access_token(subject=str(user.id))
    return {"access_token": access_token}
```

### ❌ 错误做法

```python
# 不要透露用户是否存在
if user_exists(username):  # ❌ 信息泄露
    if not verify_password(password, user.password):
        raise HTTPException(detail="Invalid password")
else:
    raise HTTPException(detail="User not found")

# 正确做法：
raise HTTPException(detail="Invalid username or password")

# 不要允许无限制的登录尝试
# 没有登录限制  # ❌ 易受暴力破解
```

## 5. 权限检查

### ✅ 正确做法

```python
from fastapi_easy.security import require_role, require_permission

# 使用装饰器检查权限
@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_role("admin")),
):
    """删除用户 - 仅管理员"""
    # 权限检查已自动进行
    return {"message": "User deleted"}

# 检查资源所有权
@app.put("/items/{item_id}")
async def update_item(
    item_id: int,
    item: Item,
    current_user: dict = Depends(get_current_user),
):
    """更新项目 - 仅所有者"""
    existing_item = get_item(item_id)
    
    if existing_item.owner_id != int(current_user["user_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # 更新项目
    return update_item_in_db(item_id, item)
```

### ❌ 错误做法

```python
# 不要在业务逻辑中检查权限
@app.delete("/users/{user_id}")
async def delete_user(user_id: int, current_user: dict):
    if current_user["role"] != "admin":  # ❌ 太晚了
        raise HTTPException(status_code=403)
    # 业务逻辑

# 不要信任客户端发送的权限
@app.post("/items")
async def create_item(item: Item, user_role: str):  # ❌ 不安全
    if user_role == "admin":
        # 给予特殊权限
        pass
```

## 6. 审计和监控

### ✅ 正确做法

```python
from fastapi_easy.security import AuditLogger, AuditEventType

audit_logger = AuditLogger()

@app.post("/auth/login")
async def login(username: str, password: str):
    # 记录所有登录尝试
    try:
        user = authenticate_user(username, password)
        
        audit_logger.log(
            event_type=AuditEventType.LOGIN_SUCCESS,
            user_id=str(user.id),
            username=username,
            status="success",
        )
        
        # 生成 Token
        access_token = jwt_auth.create_access_token(subject=str(user.id))
        return {"access_token": access_token}
    
    except Exception as e:
        audit_logger.log(
            event_type=AuditEventType.LOGIN_FAILURE,
            username=username,
            status="failure",
            details={"error": str(e)},
        )
        raise

# 定期检查审计日志
def check_suspicious_activity():
    """检查可疑活动"""
    failed_logins = audit_logger.get_failed_logins("admin", limit=10)
    
    if len(failed_logins) > 5:
        # 发送警告
        send_alert("Multiple failed login attempts for admin account")

import schedule
schedule.every(1).hour.do(check_suspicious_activity)
```

### ❌ 错误做法

```python
# 不要忽略审计日志
@app.post("/auth/login")
async def login(username: str, password: str):
    # 没有记录登录尝试  # ❌ 无法审计
    user = authenticate_user(username, password)
    access_token = jwt_auth.create_access_token(subject=str(user.id))
    return {"access_token": access_token}

# 不要只记录成功的事件
# 记录失败的事件同样重要
```

## 7. HTTPS 和传输安全

### ✅ 正确做法

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # 仅允许特定域名
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization"],
)

# 配置受信任的主机
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["yourdomain.com", "www.yourdomain.com"],
)

# 在生产环境中使用 HTTPS
# 使用 SSL 证书（Let's Encrypt）
# 配置 HSTS 头
```

### ❌ 错误做法

```python
# 不要在开发环境中使用 HTTP
# uvicorn app:app --host 0.0.0.0  # ❌ 不安全

# 不要允许所有 CORS 源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ 不安全
)

# 不要禁用 HTTPS
# 在生产环境中必须使用 HTTPS
```

## 8. 依赖和更新

### ✅ 正确做法

```python
# 定期更新依赖
# pip install --upgrade PyJWT bcrypt

# 使用 requirements.txt 固定版本
# PyJWT==2.8.0
# bcrypt==4.0.0

# 定期检查安全漏洞
# pip install safety
# safety check
```

### ❌ 错误做法

```python
# 不要使用过时的库
# PyJWT==1.0.0  # ❌ 太旧

# 不要忽视安全更新
# 不更新依赖  # ❌ 可能有漏洞
```

## 9. 错误处理

### ✅ 正确做法

```python
# 不要透露内部错误信息
@app.get("/data")
async def get_data(current_user: dict = Depends(get_current_user)):
    try:
        # 业务逻辑
        pass
    except Exception as e:
        # 记录详细错误
        logger.error(f"Error: {e}", exc_info=True)
        
        # 返回通用错误信息
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )
```

### ❌ 错误做法

```python
# 不要在错误信息中透露敏感信息
raise HTTPException(
    status_code=500,
    detail=f"Database error: {str(e)}",  # ❌ 泄露数据库信息
)

# 不要忽视错误
try:
    # 业务逻辑
    pass
except:
    pass  # ❌ 忽视错误
```

## 10. 部署检查清单

- [ ] 使用环境变量配置所有密钥
- [ ] 启用 HTTPS
- [ ] 配置 CORS
- [ ] 设置合理的 Token 过期时间
- [ ] 启用登录限制
- [ ] 启用审计日志
- [ ] 定期备份审计日志
- [ ] 监控可疑活动
- [ ] 定期更新依赖
- [ ] 进行安全审计
- [ ] 配置日志和监控
- [ ] 设置告警规则

## 参考资源

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [bcrypt Documentation](https://github.com/pyca/bcrypt)
