# 优先级修复方案

**状态**: 待执行  
**优先级**: 高 → 中 → 低

---

## 🔴 高优先级修复 (立即执行)

### 1. 添加线程安全 (LoginAttemptTracker)

**文件**: `src/fastapi_easy/security/rate_limit.py`

**修复方案**:
```python
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

class LoginAttemptTracker:
    """Track login attempts and enforce rate limiting"""

    def __init__(
        self,
        max_attempts: int = 5,
        lockout_duration_minutes: int = 15,
        reset_duration_minutes: int = 60,
    ):
        """Initialize login attempt tracker"""
        self.max_attempts = max_attempts
        self.lockout_duration = timedelta(minutes=lockout_duration_minutes)
        self.reset_duration = timedelta(minutes=reset_duration_minutes)
        
        # 添加线程锁
        self._lock = threading.RLock()
        
        self.attempts: Dict[str, list] = defaultdict(list)
        self.lockouts: Dict[str, datetime] = {}

    def record_attempt(self, username: str, success: bool = False) -> None:
        """Record a login attempt"""
        with self._lock:
            # 现有代码
            now = datetime.now(timezone.utc)
            
            if success:
                self.attempts[username] = []
                self.lockouts.pop(username, None)
                return
            
            self.attempts[username].append(now)
            self._cleanup_old_attempts(username)
            
            if len(self.attempts[username]) >= self.max_attempts:
                self.lockouts[username] = now

    def is_locked_out(self, username: str) -> bool:
        """Check if user is locked out"""
        with self._lock:
            # 现有代码
            if username not in self.lockouts:
                return False
            
            lockout_time = self.lockouts[username]
            now = datetime.now(timezone.utc)
            
            if now - lockout_time > self.lockout_duration:
                self.lockouts.pop(username, None)
                self.attempts[username] = []
                return False
            
            return True
```

**时间**: 30 分钟  
**测试**: 需要添加并发测试

---

### 2. 添加线程安全 (AuditLogger)

**文件**: `src/fastapi_easy/security/audit_log.py`

**修复方案**:
```python
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

class AuditLogger:
    """Audit logger for security events"""

    def __init__(self, max_logs: int = 10000):
        """Initialize audit logger"""
        self.max_logs = max_logs
        self._lock = threading.RLock()
        self.logs: List[AuditLog] = []

    def log(self, ...) -> AuditLog:
        """Log an audit event"""
        with self._lock:
            log_entry = AuditLog(...)
            self.logs.append(log_entry)
            
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs :]
            
            return log_entry

    def get_logs(self, ...) -> List[Dict[str, Any]]:
        """Get audit logs with optional filtering"""
        with self._lock:
            # 现有代码
            filtered_logs = self.logs
            # ...
            return [log.to_dict() for log in filtered_logs[-limit:]]
```

**时间**: 30 分钟  
**测试**: 需要添加并发测试

---

### 3. 完善 CRUDRouter 集成

**文件**: `src/fastapi_easy/security/crud_integration.py`

**修复方案**:
```python
import asyncio
from typing import Any, Awaitable, Callable, List, Optional

class ProtectedCRUDRouter:
    """Wrapper for CRUDRouter with security integration"""

    def add_security_to_routes(self) -> None:
        """Add security checks to all routes"""
        if not self.security_config.enable_auth:
            return

        for route in self.crud_router.routes:
            if hasattr(route, "endpoint"):
                original_endpoint = route.endpoint
                
                # 检查是否是异步函数
                if asyncio.iscoroutinefunction(original_endpoint):
                    route.endpoint = self._wrap_with_security_async(original_endpoint)
                else:
                    route.endpoint = self._wrap_with_security_sync(original_endpoint)

    def _wrap_with_security_async(
        self, endpoint: Callable[..., Awaitable[Any]]
    ) -> Callable[..., Awaitable[Any]]:
        """Wrap async endpoint with security checks"""
        async def secured_endpoint(*args: Any, **kwargs: Any) -> Any:
            current_user = await self._get_current_user(*args, **kwargs)
            
            if self.security_config.require_roles:
                user_roles = current_user.get("roles", [])
                if not any(role in user_roles for role in self.security_config.require_roles):
                    raise HTTPException(status_code=403, detail="Insufficient role")
            
            if self.security_config.require_permissions:
                user_permissions = current_user.get("permissions", [])
                if not any(perm in user_permissions for perm in self.security_config.require_permissions):
                    raise HTTPException(status_code=403, detail="Insufficient permission")
            
            return await endpoint(*args, **kwargs)
        
        return secured_endpoint

    def _wrap_with_security_sync(
        self, endpoint: Callable[..., Any]
    ) -> Callable[..., Any]:
        """Wrap sync endpoint with security checks"""
        def secured_endpoint(*args: Any, **kwargs: Any) -> Any:
            # 同步端点不支持异步 get_current_user
            # 需要使用不同的方法
            raise NotImplementedError("Sync endpoints not supported with async auth")
        
        return secured_endpoint

    async def _get_current_user(self, *args: Any, **kwargs: Any) -> dict:
        """Extract current user from kwargs"""
        current_user = kwargs.get("current_user")
        if current_user is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return current_user
```

**时间**: 1 小时  
**测试**: 需要添加异步端点测试

---

## 🟡 中优先级修复 (本月完成)

### 4. 改进内存管理

**文件**: `src/fastapi_easy/security/audit_log.py`

**修复方案**:
```python
from collections import deque

class AuditLogger:
    def __init__(self, max_logs: int = 10000):
        self.max_logs = max_logs
        self._lock = threading.RLock()
        # 使用 deque 自动丢弃旧日志
        self.logs: deque = deque(maxlen=max_logs)
    
    def log(self, ...) -> AuditLog:
        with self._lock:
            log_entry = AuditLog(...)
            self.logs.append(log_entry)  # 自动丢弃最旧的
            return log_entry
```

**时间**: 30 分钟

---

### 5. 性能优化 - 添加索引

**文件**: `src/fastapi_easy/security/audit_log.py`

**修复方案**:
```python
from collections import defaultdict

class AuditLogger:
    def __init__(self, max_logs: int = 10000):
        self.max_logs = max_logs
        self._lock = threading.RLock()
        self.logs: deque = deque(maxlen=max_logs)
        
        # 添加索引
        self.user_index: Dict[str, List[int]] = defaultdict(list)
        self.username_index: Dict[str, List[int]] = defaultdict(list)
    
    def log(self, ...) -> AuditLog:
        with self._lock:
            idx = len(self.logs)
            log_entry = AuditLog(...)
            self.logs.append(log_entry)
            
            # 更新索引
            if log_entry.user_id:
                self.user_index[log_entry.user_id].append(idx)
            if log_entry.username:
                self.username_index[log_entry.username].append(idx)
            
            return log_entry
    
    def get_logs(self, ...) -> List[Dict[str, Any]]:
        with self._lock:
            # 使用索引快速查询
            if user_id:
                indices = self.user_index.get(user_id, [])
                filtered_logs = [self.logs[i] for i in indices if i < len(self.logs)]
            elif username:
                indices = self.username_index.get(username, [])
                filtered_logs = [self.logs[i] for i in indices if i < len(self.logs)]
            else:
                filtered_logs = list(self.logs)
            
            return [log.to_dict() for log in filtered_logs[-limit:]]
```

**时间**: 1 小时

---

### 6. 增强安全性 - 时间恒定性

**文件**: `src/fastapi_easy/security/password.py`

**修复方案**:
```python
def verify_password(self, password: str, hashed_password: str) -> bool:
    """Verify password with constant time comparison"""
    try:
        if not password or not hashed_password:
            # 使用虚拟操作保持恒定时间
            dummy_hash = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=4))
            bcrypt.checkpw(b"dummy", dummy_hash)
            return False
        
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # 虚拟操作保持恒定时间
        dummy_hash = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=4))
        bcrypt.checkpw(b"dummy", dummy_hash)
        return False
```

**时间**: 1 小时

---

### 7. 添加日志记录

**文件**: 所有模块

**修复方案**:
```python
import logging

logger = logging.getLogger(__name__)

class JWTAuth:
    def verify_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(...)
            logger.debug(f"Token verified for user: {payload.get('sub')}")
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired token attempted")
            raise TokenExpiredError(...)
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise InvalidTokenError(...)
```

**时间**: 1-2 小时

---

### 8. 添加输入验证

**文件**: `src/fastapi_easy/security/rate_limit.py`

**修复方案**:
```python
def record_attempt(self, username: str, success: bool = False) -> None:
    """Record a login attempt"""
    # 验证输入
    if not isinstance(username, str):
        raise TypeError("username must be a string")
    
    if len(username) > 255:
        raise ValueError("username too long (max 255 characters)")
    
    if not username.strip():
        raise ValueError("username cannot be empty")
    
    with self._lock:
        # 现有代码
```

**时间**: 30 分钟

---

## 🟢 低优先级修复 (可选)

### 9. 改进全局状态管理

**文件**: `src/fastapi_easy/security/decorators.py`

**修复方案**: 使用 `contextvars` 替代全局变量

**时间**: 1 小时

---

### 10. 添加完整类型提示

**文件**: `src/fastapi_easy/security/crud_integration.py`

**时间**: 30 分钟

---

## 📅 修复时间表

| 周期 | 任务 | 时间 |
|------|------|------|
| 本周 | 1. 线程安全 (LoginAttemptTracker) | 30 分钟 |
|      | 2. 线程安全 (AuditLogger) | 30 分钟 |
|      | 3. CRUDRouter 集成 | 1 小时 |
|      | 测试和验证 | 1 小时 |
| 下周 | 4. 内存管理 | 30 分钟 |
|      | 5. 性能优化 | 1 小时 |
|      | 6. 时间恒定性 | 1 小时 |
|      | 7. 日志记录 | 1-2 小时 |
|      | 8. 输入验证 | 30 分钟 |
|      | 测试和验证 | 2 小时 |

**总计**: 约 10-12 小时

---

## ✅ 验收标准

- [ ] 所有线程安全问题已修复
- [ ] CRUDRouter 集成完整
- [ ] 所有新测试通过
- [ ] 性能基准测试通过
- [ ] 代码审查通过
- [ ] 文档已更新

---

**优先级修复计划完成**
