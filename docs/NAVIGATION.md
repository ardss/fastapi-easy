# 文档导航指南

本指南帮助你快速找到所需的文档。

---

## 按学习路径

### 初学者路径

如果你是第一次使用 FastAPI-Easy，按以下顺序学习：

1. **[快速开始](./tutorial/01-quick-start.md)** (5 分钟)
   - 运行你的第一个 CRUD API
   - 了解基本概念

2. **[数据库集成](./tutorial/02-database-integration.md)** (15 分钟)
   - 连接到真实数据库
   - 配置 ORM 适配器

3. **[查询指南](./guides/querying.md)** (10 分钟)
   - 学习过滤、排序、分页
   - 构建复杂查询

4. **[完整示例](./tutorial/03-complete-example.md)** (20 分钟)
   - 查看完整的电商 API 示例
   - 理解最佳实践

### 中级路径

掌握基础后，学习高级功能：

1. **[Hook 系统](./guides/hooks-advanced.md)** (20 分钟)
   - 在关键点插入自定义逻辑
   - 实现审计日志、数据验证等

2. **[缓存系统](./guides/caching.md)** (15 分钟)
   - 优化应用性能
   - 配置 L1 和 L2 缓存

3. **[权限控制](./guides/permissions-basic.md)** (15 分钟)
   - 保护你的 API
   - 实现基于角色的访问控制

### 高级路径

深入了解高级功能：

1. **[GraphQL 集成](./guides/graphql-integration.md)** (10 分钟)
   - 使用 GraphQL 查询 API
   - 处理 N+1 查询问题

2. **[WebSocket 集成](./guides/websocket-integration.md)** (15 分钟)
   - 实时推送数据更新
   - 管理 WebSocket 连接

3. **[软删除](./guides/soft-delete.md)** (10 分钟)
   - 逻辑删除而不是物理删除
   - 恢复已删除数据

4. **[批量操作](./guides/bulk-operations.md)** (10 分钟)
   - 批量创建、更新、删除
   - 提高大数据量操作效率

---

## 按功能分类

### 核心功能

- **[API 参考](./reference/api.md)** - CRUDRouter、配置、Hook 等
- **[配置管理](./reference/configuration.md)** - 所有配置选项
- **[查询指南](./guides/querying.md)** - 过滤、排序、分页

### 性能优化

- **[缓存系统](./guides/caching.md)** - 多层缓存
- **[性能优化](./best-practices/performance.md)** - 优化建议

### 安全

- **[认证](./security/authentication.md)** - 用户认证
- **[权限](./security/permissions.md)** - 权限控制
- **[速率限制](./security/rate-limiting.md)** - 防止滥用

### 集成

- **[GraphQL 集成](./guides/graphql-integration.md)** - GraphQL 支持
- **[WebSocket 集成](./guides/websocket-integration.md)** - 实时通信

### 数据库

- **[SQLAlchemy](./adapters/sqlalchemy.md)** - 最成熟的选择
- **[Tortoise ORM](./adapters/tortoise.md)** - 异步 ORM
- **[MongoDB](./adapters/mongodb.md)** - NoSQL 数据库
- **[SQLModel](./adapters/sqlmodel.md)** - SQLAlchemy + Pydantic

---

## 按问题类型

### 我想...

#### 快速开始
- **运行第一个 API** → [快速开始](./tutorial/01-quick-start.md)
- **连接到数据库** → [数据库集成](./tutorial/02-database-integration.md)
- **查看完整示例** → [完整示例](./tutorial/03-complete-example.md)

#### 查询和过滤
- **过滤数据** → [查询指南](./guides/querying.md)
- **排序数据** → [查询指南](./guides/querying.md)
- **分页数据** → [查询指南](./guides/querying.md)

#### 自定义逻辑
- **在创建前验证数据** → [Hook 系统](./guides/hooks-advanced.md)
- **记录审计日志** → [Hook 系统](./guides/hooks-advanced.md)
- **清除缓存** → [Hook 系统](./guides/hooks-advanced.md)

#### 性能优化
- **缓存数据** → [缓存系统](./guides/caching.md)
- **优化查询** → [性能优化](./best-practices/performance.md)
- **监控性能** → [性能优化](./best-practices/performance.md)

#### 安全
- **认证用户** → [认证](./security/authentication.md)
- **控制权限** → [权限](./security/permissions.md)
- **防止滥用** → [速率限制](./security/rate-limiting.md)

#### 实时功能
- **实时数据推送** → [WebSocket 集成](./guides/websocket-integration.md)
- **GraphQL 查询** → [GraphQL 集成](./guides/graphql-integration.md)

#### 数据管理
- **逻辑删除** → [软删除](./guides/soft-delete.md)
- **批量操作** → [批量操作](./guides/bulk-operations.md)

#### 故障排查
- **遇到错误** → [常见问题](./troubleshooting/faq.md)
- **理解错误消息** → [错误消息](./troubleshooting/error-messages.md)
- **调试应用** → [调试技巧](./troubleshooting/debugging.md)

---

## 按数据库

### SQLAlchemy
1. [数据库集成](./tutorial/02-database-integration.md)
2. [SQLAlchemy 适配器](./adapters/sqlalchemy.md)
3. [查询指南](./guides/querying.md)

### Tortoise ORM
1. [数据库集成](./tutorial/02-database-integration.md)
2. [Tortoise 适配器](./adapters/tortoise.md)
3. [查询指南](./guides/querying.md)

### MongoDB
1. [数据库集成](./tutorial/02-database-integration.md)
2. [MongoDB 适配器](./adapters/mongodb.md)
3. [查询指南](./guides/querying.md)

### SQLModel
1. [数据库集成](./tutorial/02-database-integration.md)
2. [SQLModel 适配器](./adapters/sqlmodel.md)
3. [查询指南](./guides/querying.md)

---

## 完整文档列表

### 教程
- [快速开始](./tutorial/01-quick-start.md)
- [数据库集成](./tutorial/02-database-integration.md)
- [完整示例](./tutorial/03-complete-example.md)

### 指南
- [查询指南](./guides/querying.md)
- [Hook 系统](./guides/hooks-advanced.md)
- [缓存系统](./guides/caching.md)
- [GraphQL 集成](./guides/graphql-integration.md)
- [WebSocket 集成](./guides/websocket-integration.md)
- [权限控制](./guides/permissions-basic.md)
- [软删除](./guides/soft-delete.md)
- [批量操作](./guides/bulk-operations.md)

### 参考
- [API 参考](./reference/api.md)
- [配置管理](./reference/configuration.md)
- [错误处理](./reference/errors.md)

### 安全
- [认证](./security/authentication.md)
- [权限](./security/permissions.md)
- [速率限制](./security/rate-limiting.md)

### 适配器
- [SQLAlchemy](./adapters/sqlalchemy.md)
- [Tortoise ORM](./adapters/tortoise.md)
- [MongoDB](./adapters/mongodb.md)
- [SQLModel](./adapters/sqlmodel.md)

### 最佳实践
- [性能优化](./best-practices/performance.md)
- [错误处理](./best-practices/error-handling.md)
- [测试指南](./best-practices/testing.md)
- [部署指南](./best-practices/deployment.md)

### 故障排查
- [常见问题](./troubleshooting/faq.md)
- [错误消息](./troubleshooting/error-messages.md)
- [调试技巧](./troubleshooting/debugging.md)

---

## 快速链接

- **[文档主页](./README.md)** - 返回主页
- **[API 参考](./reference/api.md)** - 快速查看 API
- **[常见问题](./troubleshooting/faq.md)** - 常见问题解答

