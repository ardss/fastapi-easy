# 安全

保护你的 FastAPI-Easy 应用，构建安全可靠的 API！

---

## 📚 本章内容

### 核心安全功能

| 章节 | 难度 | 描述 |
|------|------|------|
| [安全概览](index.md) | ⭐ 入门 | 安全功能总览 |
| [认证系统](authentication.md) | ⭐⭐ 初级 | JWT 认证、用户登录 |
| [权限控制](permissions.md) | ⭐⭐ 初级 | RBAC 角色权限管理 |
| [多租户](multi-tenancy.md) | ⭐⭐⭐ 中级 | 多租户数据隔离 |
| [审计日志](audit-logging.md) | ⭐⭐ 初级 | 操作审计和追踪 |
| [速率限制](rate-limiting.md) | ⭐⭐ 初级 | API 速率限制和密码保护 |
| [最佳实践](best-practices.md) | ⭐⭐⭐ 中级 | 生产环境安全建议 |

### 高级组件

| 章节 | 难度 | 描述 |
|------|------|------|
| [权限引擎](permission-engine.md) | ⭐⭐⭐⭐ 高级 | 权限系统核心架构 |
| [权限加载器](permission-loader.md) | ⭐⭐⭐ 中级 | 动态加载权限配置 |
| [资源检查器](resource-checker.md) | ⭐⭐⭐ 中级 | 对象级权限控制 |
| [安全配置](security-config.md) | ⭐⭐ 初级 | 完整配置参数 |

---

## 🎯 学习目标

完成本章后，你将能够：

- ✅ 实现 JWT 认证和用户登录
- ✅ 配置基于角色的权限控制
- ✅ 实现多租户数据隔离
- ✅ 记录完整的审计日志
- ✅ 配置 API 速率限制
- ✅ 遵循安全最佳实践

---

## 🔐 安全功能概览

### 认证 (Authentication)
- JWT Token 认证
- 用户登录/登出
- Token 刷新机制
- 密码哈希和验证

### 权限 (Authorization)
- 基于角色的访问控制 (RBAC)
- 端点级权限控制
- 字段级权限控制
- 自定义权限检查

### 审计 (Auditing)
- 自动记录所有操作
- 操作历史追踪
- 审计日志查询
- 合规性报告

### 防护 (Protection)
- API 速率限制
- 密码强度验证
- 防暴力破解
- CORS 配置

---

## 🚀 快速开始

### 1. 启用认证

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.security import init_jwt_auth

app = FastAPI()
jwt_auth = init_jwt_auth(secret_key="your-secret-key")

router = CRUDRouter(
    schema=Item,
    auth=jwt_auth,
)
```

### 2. 配置权限

```python
from fastapi_easy.security import require_role

@app.get("/admin")
async def admin_panel(
    current_user = Depends(require_role("admin"))
):
    return {"message": "Welcome admin"}
```

### 3. 启用审计日志

```python
router = CRUDRouter(
    schema=Item,
    enable_audit=True,
)
```

---

## 📖 推荐学习路径

1. **[认证系统](authentication.md)** - 从这里开始
2. **[权限控制](permissions.md)** - 学习 RBAC
3. **[审计日志](audit-logging.md)** - 记录操作
4. **[速率限制](rate-limiting.md)** - 保护 API
5. **[最佳实践](best-practices.md)** - 生产部署

---

## 🛡️ 安全检查清单

在部署到生产环境前，确保：

- [ ] 使用强密钥 (至少 32 字符)
- [ ] 启用 HTTPS
- [ ] 配置 CORS
- [ ] 启用速率限制
- [ ] 启用审计日志
- [ ] 定期审查权限
- [ ] 使用环境变量存储敏感信息
- [ ] 定期更新依赖

---

## 💡 最佳实践

1. **最小权限原则** - 只授予必要的权限
2. **定期审计** - 定期检查用户权限和操作日志
3. **多层防护** - 认证 + 权限 + 审计 + 速率限制
4. **安全配置** - 使用强密钥和安全的配置
5. **监控告警** - 监控异常访问和失败的认证

---

**开始学习**: [认证系统 →](authentication.md)
