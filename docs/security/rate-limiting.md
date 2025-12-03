# 密码和登录限制指南

## 概述

FastAPI-Easy 提供了：

- 安全的密码哈希 (bcrypt)
- 登录尝试限制
- 账户锁定机制
- 暴力破解防护

## 密码管理

### 初始化密码管理器

```python
from fastapi_easy.security import PasswordManager

# 创建密码管理器
password_manager = PasswordManager(rounds=12)
```

### 哈希密码

```python
# 在用户注册时哈希密码
password = "user_password_123"
hashed_password = password_manager.hash_password(password)

# 保存到数据库
user.password_hash = hashed_password
db.add(user)
db.commit()
```

### 验证密码

```python
# 在用户登录时验证密码
@app.post("/auth/login")
async def login(username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 验证密码
    if not password_manager.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 生成 Token
    access_token = jwt_auth.create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}
```

### 检查是否需要重新哈希

```python
# 定期检查密码是否需要重新哈希
# 例如：当 bcrypt rounds 增加时
new_password_manager = PasswordManager(rounds=14)

if new_password_manager.needs_rehash(user.password_hash):
    # 在用户下次登录时重新哈希
    new_hash = new_password_manager.hash_password(original_password)
    user.password_hash = new_hash
    db.commit()
```

## 登录限制

### 初始化登录尝试跟踪器

```python
from fastapi_easy.security import LoginAttemptTracker

# 创建跟踪器
# 最多 5 次尝试，锁定 15 分钟，60 分钟后重置
tracker = LoginAttemptTracker(
    max_attempts=5,
    lockout_duration_minutes=15,
    reset_duration_minutes=60,
)
```

### 记录登录尝试

```python
@app.post("/auth/login")
async def login(username: str, password: str):
    # 检查是否被锁定
    if tracker.is_locked_out(username):
        remaining = tracker.get_lockout_remaining_seconds(username)
        raise HTTPException(
            status_code=429,
            detail=f"Account locked. Try again in {remaining} seconds",
        )
    
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not password_manager.verify_password(password, user.password_hash):
        # 记录失败的尝试
        tracker.record_attempt(username, success=False)
        
        attempt_count = tracker.get_attempt_count(username)
        raise HTTPException(
            status_code=401,
            detail=f"Invalid credentials ({attempt_count} attempts)",
        )
    
    # 记录成功的尝试（清除计数）
    tracker.record_attempt(username, success=True)
    
    # 生成 Token
    access_token = jwt_auth.create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}
```

### 获取锁定信息

```python
@app.get("/auth/lockout-status/{username}")
async def get_lockout_status(username: str):
    """获取账户锁定状态"""
    if tracker.is_locked_out(username):
        remaining = tracker.get_lockout_remaining_seconds(username)
        return {
            "locked": True,
            "remaining_seconds": remaining,
        }
    else:
        attempt_count = tracker.get_attempt_count(username)
        return {
            "locked": False,
            "attempts": attempt_count,
            "max_attempts": 5,
        }
```

### 重置用户

```python
@app.post("/admin/reset-lockout/{username}")
async def reset_lockout(
    username: str,
    current_user: dict = Depends(require_role("admin")),
):
    """管理员重置用户锁定状态"""
    tracker.reset_user(username)
    return {"message": f"Lockout reset for {username}"}
```

## 完整的登录流程

```python
from fastapi_easy.security import (
    PasswordManager,
    LoginAttemptTracker,
    AuditLogger,
    AuditEventType,
)

# 初始化
password_manager = PasswordManager()
tracker = LoginAttemptTracker()
audit_logger = AuditLogger()

@app.post("/auth/login")
async def login(username: str, password: str):
    """完整的登录流程"""
    
    # 1. 检查是否被锁定
    if tracker.is_locked_out(username):
        remaining = tracker.get_lockout_remaining_seconds(username)
        audit_logger.log(
            event_type=AuditEventType.LOGIN_LOCKED,
            username=username,
            status="failure",
        )
        raise HTTPException(status_code=429, detail="Account locked")
    
    # 2. 查找用户
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        tracker.record_attempt(username, success=False)
        audit_logger.log(
            event_type=AuditEventType.LOGIN_FAILURE,
            username=username,
            status="failure",
            details={"reason": "user_not_found"},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 3. 验证密码
    if not password_manager.verify_password(password, user.password_hash):
        tracker.record_attempt(username, success=False)
        audit_logger.log(
            event_type=AuditEventType.LOGIN_FAILURE,
            username=username,
            user_id=str(user.id),
            status="failure",
            details={"reason": "invalid_password"},
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 4. 记录成功的尝试
    tracker.record_attempt(username, success=True)
    
    # 5. 生成 Token
    access_token = jwt_auth.create_access_token(subject=str(user.id))
    refresh_token = jwt_auth.create_refresh_token(subject=str(user.id))
    
    # 6. 记录审计日志
    audit_logger.log(
        event_type=AuditEventType.LOGIN_SUCCESS,
        username=username,
        user_id=str(user.id),
        status="success",
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }
```

## 最佳实践

### 1. 使用强密码要求

```python
import re

def validate_password(password: str) -> bool:
    """验证密码强度"""
    # 至少 8 个字符
    if len(password) < 8:
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
    if not validate_password(password):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters and contain uppercase, lowercase, digit, and special character",
        )
    
    # 继续注册流程
```

### 2. 定期更新 bcrypt rounds

```python
# 每年或根据安全建议更新 rounds
# 当计算能力增加时，增加 rounds 以保持安全性
password_manager = PasswordManager(rounds=14)  # 从 12 增加到 14
```

### 3. 监控登录失败

```python
# 定期检查登录失败
failed_logins = audit_logger.get_failed_logins(username="admin", limit=10)

for login in failed_logins:
    print(f"Failed login attempt: {login['timestamp']}")
```

### 4. 实现密码重置

```python
@app.post("/auth/forgot-password")
async def forgot_password(email: str):
    """密码重置请求"""
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # 不要透露用户是否存在
        return {"message": "If user exists, reset link will be sent"}
    
    # 生成重置令牌
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    # 发送重置链接
    send_reset_email(user.email, reset_token)
    
    return {"message": "Reset link sent to email"}

@app.post("/auth/reset-password")
async def reset_password(token: str, new_password: str):
    """重置密码"""
    user = db.query(User).filter(User.reset_token == token).first()
    
    if not user or user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    # 哈希新密码
    user.password_hash = password_manager.hash_password(new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    
    return {"message": "Password reset successfully"}
```

## 完整示例

参考 `examples/06_with_permissions.py` 获取完整的工作示例。
