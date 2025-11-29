# 审计日志指南

## 概述

FastAPI-Easy 提供了完整的审计日志系统，用于：

- 记录安全事件
- 跟踪用户活动
- 合规性审计
- 安全分析

## 快速开始

### 初始化审计日志

```python
from fastapi_easy.security import AuditLogger, AuditEventType

# 创建审计日志记录器
audit_logger = AuditLogger(max_logs=10000)
```

### 记录事件

```python
# 记录登录成功
audit_logger.log(
    event_type=AuditEventType.LOGIN_SUCCESS,
    user_id="user123",
    username="john_doe",
    status="success",
)

# 记录登录失败
audit_logger.log(
    event_type=AuditEventType.LOGIN_FAILURE,
    username="john_doe",
    status="failure",
    details={"reason": "invalid_password"},
)

# 记录权限被拒绝
audit_logger.log(
    event_type=AuditEventType.PERMISSION_DENIED,
    user_id="user123",
    resource="admin_panel",
    action="access",
    status="failure",
)
```

## 事件类型

### 认证事件

```python
AuditEventType.LOGIN_SUCCESS      # 登录成功
AuditEventType.LOGIN_FAILURE      # 登录失败
AuditEventType.LOGIN_LOCKED       # 账户被锁定
AuditEventType.LOGOUT             # 登出
AuditEventType.TOKEN_REFRESH      # Token 刷新
AuditEventType.TOKEN_EXPIRED      # Token 过期
```

### 授权事件

```python
AuditEventType.PERMISSION_DENIED      # 权限被拒绝
AuditEventType.PERMISSION_GRANTED     # 权限被授予
AuditEventType.UNAUTHORIZED           # 未授权
AuditEventType.ACCOUNT_LOCKED         # 账户被锁定
AuditEventType.ACCOUNT_UNLOCKED       # 账户被解锁
```

### 用户管理事件

```python
AuditEventType.PASSWORD_CHANGED       # 密码已更改
AuditEventType.ROLE_CHANGED           # 角色已更改
AuditEventType.PERMISSION_CHANGED     # 权限已更改
```

## 查询审计日志

### 获取所有日志

```python
# 获取最近 100 条日志
logs = audit_logger.get_logs(limit=100)

for log in logs:
    print(f"{log['timestamp']}: {log['event_type']} - {log['username']}")
```

### 按用户过滤

```python
# 获取特定用户的活动
user_logs = audit_logger.get_user_activity(
    username="john_doe",
    limit=50,
)

for log in user_logs:
    print(f"{log['timestamp']}: {log['event_type']}")
```

### 获取失败的登录

```python
# 获取特定用户的失败登录尝试
failed_logins = audit_logger.get_failed_logins(
    username="john_doe",
    limit=10,
)

for login in failed_logins:
    print(f"Failed login: {login['timestamp']}")
```

### 按事件类型过滤

```python
from fastapi_easy.security import AuditEventType

# 获取所有权限拒绝事件
permission_denied = audit_logger.get_logs(
    event_type=AuditEventType.PERMISSION_DENIED,
    limit=50,
)
```

## 完整的审计日志集成

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi_easy.security import (
    PasswordManager,
    LoginAttemptTracker,
    AuditLogger,
    AuditEventType,
    get_current_user,
    require_role,
)

app = FastAPI()

# 初始化
password_manager = PasswordManager()
tracker = LoginAttemptTracker()
audit_logger = AuditLogger()

@app.post("/auth/login")
async def login(username: str, password: str):
    """登录端点（带审计日志）"""
    
    # 检查锁定
    if tracker.is_locked_out(username):
        audit_logger.log(
            event_type=AuditEventType.LOGIN_LOCKED,
            username=username,
            status="failure",
        )
        raise HTTPException(status_code=429, detail="Account locked")
    
    # 验证用户
    user = authenticate_user(username, password)
    
    if not user:
        tracker.record_attempt(username, success=False)
        audit_logger.log(
            event_type=AuditEventType.LOGIN_FAILURE,
            username=username,
            status="failure",
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 成功登录
    tracker.record_attempt(username, success=True)
    audit_logger.log(
        event_type=AuditEventType.LOGIN_SUCCESS,
        user_id=str(user.id),
        username=username,
        status="success",
    )
    
    # 生成 Token
    access_token = jwt_auth.create_access_token(subject=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """登出端点（带审计日志）"""
    audit_logger.log(
        event_type=AuditEventType.LOGOUT,
        user_id=current_user["user_id"],
        status="success",
    )
    return {"message": "Logged out successfully"}

@app.get("/admin-panel")
async def admin_panel(current_user: dict = Depends(require_role("admin"))):
    """管理员面板（带审计日志）"""
    audit_logger.log(
        event_type=AuditEventType.PERMISSION_GRANTED,
        user_id=current_user["user_id"],
        resource="admin_panel",
        action="access",
        status="success",
    )
    return {"message": "Welcome to admin panel"}

@app.get("/audit-logs")
async def get_audit_logs(
    current_user: dict = Depends(require_role("admin")),
):
    """获取审计日志（仅管理员）"""
    logs = audit_logger.export_logs()
    return {"logs": logs}
```

## 审计日志分析

### 检测异常活动

```python
def detect_suspicious_activity():
    """检测可疑活动"""
    
    # 检查多次失败的登录
    all_logs = audit_logger.export_logs()
    
    failed_logins = {}
    for log in all_logs:
        if log["event_type"] == "login_failure":
            username = log["username"]
            failed_logins[username] = failed_logins.get(username, 0) + 1
    
    # 如果某个用户有超过 10 次失败登录，发出警告
    for username, count in failed_logins.items():
        if count > 10:
            print(f"⚠️  Warning: {username} has {count} failed login attempts")

# 定期运行检测
import schedule

schedule.every(1).hour.do(detect_suspicious_activity)
```

### 生成审计报告

```python
def generate_audit_report(start_date, end_date):
    """生成审计报告"""
    
    logs = audit_logger.export_logs()
    
    # 按事件类型统计
    event_counts = {}
    for log in logs:
        event_type = log["event_type"]
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    # 按用户统计
    user_activity = {}
    for log in logs:
        username = log.get("username", "unknown")
        user_activity[username] = user_activity.get(username, 0) + 1
    
    return {
        "period": f"{start_date} to {end_date}",
        "event_counts": event_counts,
        "user_activity": user_activity,
        "total_events": len(logs),
    }

# 生成报告
report = generate_audit_report("2025-01-01", "2025-01-31")
print(report)
```

## 最佳实践

### 1. 定期导出和备份日志

```python
import json
from datetime import datetime

def backup_audit_logs():
    """备份审计日志"""
    logs = audit_logger.export_logs()
    
    filename = f"audit_logs_{datetime.now().isoformat()}.json"
    with open(filename, "w") as f:
        json.dump(logs, f, indent=2)
    
    print(f"Audit logs backed up to {filename}")

# 每天备份
schedule.every().day.at("23:59").do(backup_audit_logs)
```

### 2. 监控关键事件

```python
def monitor_critical_events():
    """监控关键事件"""
    logs = audit_logger.export_logs()
    
    critical_events = [
        AuditEventType.PERMISSION_DENIED,
        AuditEventType.LOGIN_LOCKED,
        AuditEventType.ACCOUNT_LOCKED,
    ]
    
    for log in logs:
        if log["event_type"] in [e.value for e in critical_events]:
            # 发送警告
            send_alert(f"Critical event: {log['event_type']}")
```

### 3. 保留日志策略

```python
def cleanup_old_logs(days=90):
    """清理旧日志"""
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # 导出日志到存储
    logs = audit_logger.export_logs()
    
    # 清理内存中的日志
    audit_logger.clear_logs()
    
    # 保存到数据库或文件系统
    save_logs_to_storage(logs)

# 每周清理
schedule.every().week.do(cleanup_old_logs)
```

### 4. 合规性报告

```python
def generate_compliance_report():
    """生成合规性报告"""
    logs = audit_logger.export_logs()
    
    # 统计登录事件
    login_events = [l for l in logs if "login" in l["event_type"]]
    
    # 统计权限变更
    permission_changes = [l for l in logs if "permission" in l["event_type"]]
    
    # 统计失败事件
    failed_events = [l for l in logs if l["status"] == "failure"]
    
    return {
        "total_logins": len(login_events),
        "permission_changes": len(permission_changes),
        "failed_events": len(failed_events),
        "compliance_status": "compliant" if len(failed_events) < 100 else "review_needed",
    }
```

## 完整示例

参考 `examples/06_with_permissions.py` 获取完整的工作示例。
