# FastAPI-Easy 文档

欢迎来到 FastAPI-Easy！这是一个现代化的 FastAPI CRUD 框架，可以让你用 **10 行代码** 替代 **240+ 行** 的重复代码。

---

## 🚀 快速开始（5 分钟）

如果你是第一次使用 FastAPI-Easy，从这里开始：

**[→ 快速开始教程](tutorial/01-quick-start.md)** - 运行你的第一个 CRUD API

---

## 📚 学习路径

### 初级（新手）- 30 分钟

学习 FastAPI-Easy 的基础用法：

1. **[快速开始](tutorial/01-quick-start.md)** (5 分钟)
   - 最简单的 CRUD 示例
   - 理解 CRUDRouter 的基本用法

2. **[数据库集成](tutorial/02-database-integration.md)** (10 分钟)
   - 连接真实数据库（SQLite、PostgreSQL 等）
   - 学习如何使用 Adapter

3. **[查询指南](guides/querying.md)** (15 分钟)
   - 实现搜索、过滤、排序、分页
   - 学习 URL 查询参数的用法

### 中级（进阶）- 1 小时

学习 FastAPI-Easy 的高级功能：

1. **[完整示例](tutorial/03-complete-example.md)** (15 分钟)
   - 多资源的电商 API 示例
   - 学习如何组织大型项目

2. **[权限控制](guides/permissions-basic.md)** (15 分钟)
   - 保护你的 API 端点
   - 实现基于角色的访问控制

3. **[错误处理](guides/error-handling.md)** (15 分钟)
   - 正确处理异常
   - 返回有意义的错误消息

4. **[Hook 系统](guides/hooks-advanced.md)** (15 分钟)
   - 在关键点插入自定义逻辑
   - 实现业务规则验证

### 高级（专家）- 2+ 小时

深入理解 FastAPI-Easy 的架构和高级特性：

1. **[架构设计](reference/architecture.md)** (30 分钟)
   - 理解系统的整体设计
   - 了解各个模块的职责

2. **[缓存系统](guides/caching.md)** (20 分钟)
   - 多层缓存优化性能
   - 缓存失效管理

3. **[数据库迁移](guides/migrations.md)** (20 分钟)
   - 自动检测 Schema 变更
   - 安全地应用数据库迁移

4. **[GraphQL 支持](guides/graphql-integration.md)** (15 分钟)
   - 使用 GraphQL 查询 API
   - 与 REST 共存

5. **[WebSocket 支持](guides/websocket-integration.md)** (15 分钟)
   - 实时推送数据更新
   - 双向通信

---

## 🎯 按场景快速查找

### 我想

**快速开始使用**
→ [快速开始](tutorial/01-quick-start.md)

**连接数据库**
→ [数据库集成](tutorial/02-database-integration.md)

**实现搜索和过滤**
→ [查询指南](guides/querying.md)

**保护 API**
→ [权限控制](guides/permissions-basic.md)

**添加自定义逻辑**
→ [Hook 系统](guides/hooks-advanced.md)

**优化性能**
→ [缓存系统](guides/caching.md)

**处理错误**
→ [错误处理](guides/error-handling.md)

**查看完整示例**
→ [完整示例](tutorial/03-complete-example.md)

**理解架构**
→ [架构设计](reference/architecture.md)

---

## 💡 核心概念

### CRUDRouter

自动生成 CRUD 路由的核心类。一行代码自动生成 6 个标准 API 端点。

### Adapter（适配器）

数据库适配层，负责连接具体的 ORM（如 SQLAlchemy、Tortoise、MongoDB 等）。

### Schema（数据模型）

Pydantic 数据模型，定义 API 的请求和响应格式。

### Config（配置）

`CRUDConfig` 对象，用于集中管理路由的行为配置（启用/禁用功能、字段配置等）。

---

## 🗄️ 支持的数据库

| ORM | 数据库 | 异步支持 |
|-----|--------|--------|
| **SQLAlchemy** | PostgreSQL、MySQL、SQLite、Oracle、SQL Server | ✅ |
| **Tortoise ORM** | PostgreSQL、MySQL、SQLite | ✅ |
| **MongoDB** | MongoDB (Motor) | ✅ |
| **SQLModel** | PostgreSQL、MySQL、SQLite、Oracle | ✅ |

详见 [数据库适配器](adapters/index.md)

---

## 📖 完整文档导航

- **[教程](tutorial/)** - 手把手教学（3 个教程）
- **[指南](guides/)** - 特定功能的详细说明（13 个指南）
- **[数据库适配器](adapters/)** - 选择和配置数据库
- **[参考手册](reference/)** - API 文档、配置、架构
- **[安全模块](security/)** - 认证、权限、审计
- **[开发指南](development/)** - 贡献、测试

---

## 🆘 常见问题

**Q: 支持哪些数据库？**
A: SQLite、PostgreSQL、MySQL、MongoDB 等。详见 [数据库适配器](adapters/index.md)

**Q: 如何实现搜索和过滤？**
A: 详见 [查询指南](guides/querying.md)

**Q: 有完整的项目示例吗？**
A: 有，详见 [完整示例](tutorial/03-complete-example.md)

**Q: 如何保护 API？**
A: 详见 [权限控制](guides/permissions-basic.md)

---

## 📝 文档版本

当前版本: **0.1.4**  
最后更新: **2025-12-03**
