# 安全文档索引

本目录包含 FastAPI-Easy 安全模块的详细文档。

## 核心模块

### [认证 (Authentication)](authentication.md)
介绍如何集成 JWT 认证、用户登录和令牌管理。

### [权限控制 (Permissions)](permissions.md)
详细介绍基于角色的访问控制 (RBAC) 和装饰器用法 (`require_role`, `require_permission`)。
*注：关于 CRUDRouter 的基础权限配置，请参考 [基础权限指南](../guides/permissions-basic.md)。*

### [审计日志 (Audit Logging)](audit-logging.md)
深入了解审计日志系统，包括自定义事件、存储后端和查询接口。
*注：关于 CRUDRouter 的基础审计配置，请参考 [基础审计指南](../guides/audit-logging-basic.md)。*

### [密码与速率限制 (Password & Rate Limit)](password-rate-limit.md)
密码哈希最佳实践和 API 速率限制配置。

## 高级组件

### [权限加载器 (Permission Loader)](permission-loader.md)
如何从文件或数据库动态加载权限配置。

### [资源检查器 (Resource Checker)](resource-checker.md)
实现细粒度的对象级权限控制（例如：用户只能修改自己的文章）。

### [权限引擎 (Permission Engine)](permission-engine.md)
权限系统的核心引擎架构和扩展方式。

### [安全配置 (Security Config)](security-config.md)
安全模块的完整配置参数参考。

## 最佳实践

### [安全最佳实践](security-best-practices.md)
生产环境部署的安全建议清单。
