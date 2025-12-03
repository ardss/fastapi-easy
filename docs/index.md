# FastAPI-Easy

<div align="center">

**一个生产级的 FastAPI CRUD 框架**

用 **10 行代码** 替代 **240+ 行** 的重复代码 | 加速开发 **87%+**

[快速开始](#快速开始){.md-button .md-button--primary} [用户指南](guides/index.md){.md-button} [API 参考](reference/api.md){.md-button} [GitHub](https://github.com/ardss/fastapi-easy){.md-button}

</div>

---

## 🎯 什么是 FastAPI-Easy？

FastAPI-Easy 是一个**自动化 CRUD API 生成框架**，让你用最少的代码构建生产级的 FastAPI 应用。

### ✨ 核心优势

- **代码量减少 95%** - 从 240+ 行减少到 10 行
- **开发时间减少 87%** - 从 90-120 小时减少到 12.5 小时
- **生产就绪** - 内置权限、审计、缓存、错误处理
- **多 ORM 支持** - SQLAlchemy、Tortoise、MongoDB、SQLModel
- **灵活扩展** - Hook 系统、自定义验证、权限控制

---

## 🚀 快速开始

### 1️⃣ 安装

```bash
pip install fastapi-easy fastapi uvicorn
```

### 2️⃣ 最简单的例子

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float

app = FastAPI()
router = CRUDRouter(schema=Item)
app.include_router(router)
```

### 3️⃣ 运行

```bash
uvicorn main:app --reload
```

访问 http://localhost:8000/docs 查看自动生成的 API 文档！

**[完整快速开始指南 →](getting-started.md){.md-button}**

---

## 📚 核心特性

### 🔄 自动 CRUD 生成
- 一行代码生成 6 个标准 API 端点
- GET /items - 获取所有
- GET /items/{id} - 获取单个
- POST /items - 创建
- PUT /items/{id} - 更新
- DELETE /items/{id} - 删除
- DELETE /items - 删除所有（可选）

### 🔍 搜索和过滤
- 9 种过滤操作符（精确、大于、小于、范围、模糊等）
- 示例: `GET /items?name=apple&price__gt=10`

### 📊 排序和分页
- 多字段排序、升序/降序
- 自动分页，支持自定义大小
- 示例: `GET /items?sort=-created_at&skip=0&limit=10`

### 🔐 权限和安全
- 端点级权限控制
- 字段级权限控制
- 内置认证支持

### 📝 审计和日志
- 自动记录所有操作历史
- 支持操作追踪和恢复

### ⚡ 性能优化
- 多层缓存系统（L1/L2）
- 异步批处理
- 查询投影优化

---

## 🗄️ 支持的数据库

| 数据库 | ORM | 支持 | 成熟度 |
|--------|-----|------|--------|
| PostgreSQL | SQLAlchemy | ✅ | ⭐⭐⭐⭐⭐ |
| MySQL | SQLAlchemy | ✅ | ⭐⭐⭐⭐⭐ |
| SQLite | SQLAlchemy | ✅ | ⭐⭐⭐⭐⭐ |
| MongoDB | Motor | ✅ | ⭐⭐⭐⭐ |
| Oracle | SQLAlchemy | ✅ | ⭐⭐⭐⭐ |
| SQL Server | SQLAlchemy | ✅ | ⭐⭐⭐⭐ |

---

## 📖 文档导航

### 🎓 新手入门
- **[快速开始](getting-started.md)** - 5 分钟快速上手
- **[教程](tutorials/index.md)** - 从基础到高级的完整学习路径

### 📚 教程（13 个章节）

**基础入门**
- [快速上手](tutorials/01-basics/quick-start.md) - 创建第一个 CRUD API
- [数据库集成](tutorials/01-basics/database-integration.md) - 连接真实数据库
- [完整示例](tutorials/01-basics/complete-example.md) - 构建完整应用

**核心功能**
- [查询和过滤](tutorials/02-core-features/querying.md) - 9 种过滤操作符
- [批量操作](tutorials/02-core-features/bulk-operations.md) - 批量创建、更新、删除
- [错误处理](tutorials/02-core-features/error-handling.md) - 优雅的错误处理

**高级特性**
- [Hook 系统](tutorials/03-advanced/hooks.md) - 扩展 CRUD 操作
- [缓存系统](tutorials/03-advanced/caching.md) - 多层缓存优化
- [软删除](tutorials/03-advanced/soft-delete.md) - 逻辑删除
- [审计日志](tutorials/03-advanced/audit-logging.md) - 操作历史追踪

**扩展集成**
- [GraphQL 支持](tutorials/04-integrations/graphql.md) - GraphQL API
- [WebSocket 支持](tutorials/04-integrations/websocket.md) - 实时通信
- [数据库迁移](tutorials/04-integrations/migrations.md) - 版本管理

### 🔐 安全指南（7 个主题）
- **[安全概览](security/index.md)** - 安全功能总览
- [认证系统](security/authentication.md) - JWT 认证
- [权限控制](security/permissions.md) - RBAC 权限管理
- [多租户](security/multi-tenancy.md) - 数据隔离
- [审计日志](security/audit-logging.md) - 操作审计
- [速率限制](security/rate-limiting.md) - API 保护
- [最佳实践](security/best-practices.md) - 安全建议

### 📚 参考文档
- **[API 参考](reference/api.md)** - 完整的 API 文档
- **[配置参数](reference/configuration.md)** - 所有配置选项
- **[Hook 参考](reference/hooks.md)** - Hook 系统参考
- **[CLI 工具](reference/cli.md)** - 命令行工具
- **[数据库适配器](reference/adapters/index.md)** - ORM 适配器

### 🏗️ 架构设计
- **[架构概览](architecture/index.md)** - 系统架构
- [架构设计](architecture/design.md) - 设计理念
- [数据流](architecture/data-flow.md) - 请求处理流程

### 💡 最佳实践
- **[最佳实践](best-practices/index.md)** - 生产环境指南
- [代码组织](best-practices/code-organization.md) - 项目结构
- [性能优化](best-practices/performance.md) - 性能提升
- [测试策略](best-practices/testing.md) - 测试指南
- [故障排查](best-practices/troubleshooting.md) - 问题解决

### 🤝 贡献
- **[贡献指南](contributing/index.md)** - 如何贡献代码
- [开发测试](contributing/development.md) - 开发环境配置

---

## 📊 性能指标

| 操作 | 响应时间 | 内存占用 |
|------|---------|---------|
| GET /items | 45ms | 2MB |
| GET /items?skip=0&limit=10 | 52ms | 2.5MB |
| POST /items | 35ms | 2.3MB |
| PUT /items/{id} | 38ms | - |
| DELETE /items/{id} | 32ms | - |

---

## 💡 为什么选择 FastAPI-Easy？

### 对比传统 FastAPI

| 方面 | 传统 FastAPI | FastAPI-Easy |
|------|-------------|-------------|
| 代码行数 | 240+ 行 | 10 行 |
| 开发时间 | 90-120 小时 | 12.5 小时 |
| 功能完整性 | 需要手写 | 内置 |
| 生产就绪 | 需要额外工作 | 开箱即用 |

### 适用场景

✅ 快速构建 CRUD API  
✅ 原型开发和 MVP  
✅ 微服务架构  
✅ 内部工具和管理系统  
✅ 学习 FastAPI 最佳实践  

---

## 🎓 学习资源

- **[示例代码](https://github.com/ardss/fastapi-easy/tree/main/examples)** - 14 个完整示例
- **[测试用例](https://github.com/ardss/fastapi-easy/tree/main/tests)** - 70+ 个测试
- **[GitHub 讨论](https://github.com/ardss/fastapi-easy/discussions)** - 社区讨论

---

## 📄 许可证

**AGPL-3.0** - 开源框架

- ✅ 可用于非商业用途
- 📝 修改代码必须共享
- 📦 使用本项目的软件也必须开源

**商业用途**？[联系我们](mailto:1339731209@qq.com)

---

## 🚀 开始使用

**[快速开始 →](getting-started.md){.md-button .md-button--primary}**
