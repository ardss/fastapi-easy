# FastAPI-Easy 文档中心

欢迎来到 FastAPI-Easy 项目的文档中心！这里汇集了从入门教程到深度架构解析的所有资源。

## 📚 文档结构

我们采用 Diátaxis 框架将文档分为四类：

```text
docs/
├── index.md                     # 本文件 (文档总入口)
├── tutorial/                    # 教程：手把手教学
│   ├── 01-quick-start.md        # 5分钟上手
│   ├── 02-database-integration.md # 数据库集成指南
│   └── 03-complete-example.md   # 完整电商 API 示例
│
├── guides/                      # 指南：特定任务的解决方案
│   ├── querying.md              # 搜索、过滤与排序
│   ├── permissions-basic.md     # 基础权限控制
│   ├── audit-logging-basic.md   # 基础审计日志
│   ├── error-handling.md        # 错误处理
│   ├── soft-delete.md           # 软删除
│   ├── bulk-operations.md       # 批量操作
│   └── migrations.md            # 数据库迁移
│
├── adapters/                    # 适配器：数据库支持详解
│   └── index.md                 # 适配器概览 & 选择指南
│
├── reference/                   # 参考：API 与配置手册
│   ├── configuration.md         # 配置参数详解
│   ├── architecture.md          # 架构设计
│   ├── data-flow.md             # 内部数据流
│   └── cli.md                   # 命令行工具
│
├── security/                    # 安全：高级安全模块
│   ├── 01-authentication.md     # 认证
│   ├── 02-permissions.md        # 高级权限
│   └── ...
│
└── development/                 # 开发：贡献与测试
    ├── contributing.md          # 贡献指南
    └── testing.md               # 测试指南
```

---

## 🎯 快速导航

### 我想...

**快速开始使用库**
→ [快速开始](tutorial/01-quick-start.md)

**连接数据库**
→ [数据库集成](tutorial/02-database-integration.md)

**实现搜索、过滤和排序**
→ [查询指南](guides/querying.md)

**了解架构设计**
→ [架构设计](reference/architecture.md)

**查看完整示例**
→ [完整示例](tutorial/03-complete-example.md)

---

## 📖 推荐阅读顺序

### 初学者（30 分钟）
1. [快速开始](tutorial/01-quick-start.md)
2. [数据库集成](tutorial/02-database-integration.md)
3. [查询指南](guides/querying.md)

### 进阶开发者（1 小时）
1. [完整示例](tutorial/03-complete-example.md)
2. [基础权限控制](guides/permissions-basic.md)
3. [错误处理](guides/error-handling.md)

### 架构师（2 小时）
1. [架构设计](reference/architecture.md)
2. [数据流解析](reference/data-flow.md)
3. [配置详解](reference/configuration.md)

---

## 💡 核心概念

### CRUDRouter
自动生成 CRUD 路由的核心类。

### Adapter (适配器)
数据库适配层，负责连接具体的 ORM（如 SQLAlchemy, Tortoise）。
*注意：旧文档中可能称为 Backend，现已统一为 Adapter。*

### Schema
Pydantic 数据模型，定义 API 的请求和响应格式。

### Config
`CRUDConfig` 对象，用于集中管理路由的行为配置。

---

## 🗄️ 支持的数据库

| ORM | 数据库 | 类型 |
|-----|--------|------|
| **SQLAlchemy** | PostgreSQL、MySQL、SQLite、Oracle、SQL Server | 异步 |
| **Tortoise** | PostgreSQL、MySQL、SQLite | 异步 |
| **MongoDB** | MongoDB (Motor) | 异步 |
| **SQLModel** | PostgreSQL、MySQL、SQLite、Oracle | 异步 |

---

## 🆘 常见问题

**Q: 支持哪些数据库？**
A: 支持 SQLite、PostgreSQL、MySQL、MongoDB 等。详见 [适配器概览](adapters/index.md)

**Q: 如何使用搜索功能？**
A: 详见 [查询指南](guides/querying.md)

**Q: 有完整的项目示例吗？**
A: 有，详见 [完整示例](tutorial/03-complete-example.md)
