# FastAPI-Easy 使用指南

欢迎来到 fastapi-easy 的使用指南！本文档包含详细的教程和示例。

## 📚 文档列表

### 1. [快速开始](01-quick-start.md)
- 安装说明
- 最简单的例子
- 自动生成的 API
- 代码量对比

**适合**: 想快速上手的开发者
**阅读时间**: 5 分钟

---

### 2. [支持的数据库](02-databases.md)
- 4 种 ORM 支持（SQLAlchemy、Tortoise、MongoDB、SQLModel）
- 每种 ORM 的安装和使用
- 数据库选择指南
- 依赖关系

**适合**: 想了解数据库支持的开发者
**阅读时间**: 20 分钟

---

### 3. [数据到 API 的完整流程](03-data-flow.md)
- 完整流程图
- 详细步骤说明
- 依赖库详解
- 完整代码示例

**适合**: 想理解内部工作原理的开发者
**阅读时间**: 15 分钟

---

### 4. [搜索和过滤](04-filters.md)
- 过滤功能说明
- 支持的操作符
- 使用示例
- API 查询示例

**适合**: 想使用搜索功能的开发者
**阅读时间**: 10 分钟

---

### 5. [排序功能](05-sorting.md)
- 排序功能说明
- 升序和降序
- 多字段排序
- 使用示例

**适合**: 想使用排序功能的开发者
**阅读时间**: 10 分钟

---

### 6. [完整示例](06-complete-example.md)
- 完整的电商 API 示例
- 包含所有功能
- 代码详解
- 运行说明

**适合**: 想看完整项目的开发者
**阅读时间**: 20 分钟

---

### 7. [架构设计和扩展](07-architecture.md)
- 核心架构设计
- 操作系统（Operation System）
- ORM 适配器（ORM Adapter）
- 错误处理系统
- 钩子系统（Hook System）
- 响应格式系统
- 配置系统
- 完整的扩展示例

**适合**: 想深入了解架构和进行高度定制的开发者
**阅读时间**: 30 分钟

---

### 8. [错误处理](09-error-handling.md)
- 内置错误类型
- 自定义错误
- 错误响应格式
- 错误处理中间件

**适合**: 想处理和自定义错误的开发者
**阅读时间**: 10 分钟

---

### 9. [软删除](10-soft-delete.md)
- 软删除配置
- 恢复已删除数据
- 查询已删除记录
- 最佳实践

**适合**: 需要安全删除数据的开发者
**阅读时间**: 15 分钟

---

### 10. [批量操作](11-batch-operations.md)
- 批量创建、更新、删除
- 性能优化
- 事务管理

**适合**: 处理大量数据的开发者
**阅读时间**: 15 分钟

---

### 11. [权限控制](12-permissions.md)
- 基于角色的访问控制（RBAC）
- 基于属性的访问控制（ABAC）
- 多租户支持

**适合**: 需要权限管理的开发者
**阅读时间**: 20 分钟

---

### 12. [审计日志](13-audit-logging.md)
- 审计日志配置
- 操作记录
- 历史查询
- 合规性

**适合**: 需要追踪数据变更的开发者
**阅读时间**: 15 分钟

---

### 13. [配置管理](14-configuration.md)
- 集中配置
- 功能开关
- 环境变量
- 最佳实践

**适合**: 需要灵活配置的开发者
**阅读时间**: 15 分钟

---

### 14. [测试指南](15-testing.md)
- 单元测试
- 集成测试
- 测试工具
- 示例代码

**适合**: 想编写高质量测试的开发者
**阅读时间**: 20 分钟

---

### 15. [最佳实践](16-best-practices.md)
- 代码组织
- 性能优化
- 安全建议
- 常见陷阱

**适合**: 想遵循最佳实践的开发者
**阅读时间**: 20 分钟

---

### 16. [故障排除](17-troubleshooting.md)
- 常见问题
- 调试技巧
- 性能问题
- 错误解决

**适合**: 遇到问题需要快速解决的开发者
**阅读时间**: 15 分钟

---

## 🎯 快速导航

### 我想...

**快速开始使用**
→ 阅读 [快速开始](01-quick-start.md)

**了解支持的数据库**
→ 阅读 [支持的数据库](02-databases.md)

**理解工作原理**
→ 阅读 [数据到 API 的完整流程](03-data-flow.md)

**使用搜索功能**
→ 阅读 [搜索和过滤](04-filters.md)

**使用排序功能**
→ 阅读 [排序功能](05-sorting.md)

**看完整示例**
→ 阅读 [完整示例](06-complete-example.md)

---

## 推荐阅读顺序

### 初学者（30 分钟）
1. [快速开始](01-quick-start.md)
2. [支持的数据库](02-databases.md)

### 开发者（2 小时）
1. [快速开始](01-quick-start.md)
2. [支持的数据库](02-databases.md)
3. [数据到 API 的完整流程](03-data-flow.md)
4. [搜索和过滤](04-filters.md)
5. [排序功能](05-sorting.md)
6. [完整示例](06-complete-example.md)
7. [错误处理](09-error-handling.md)
8. [软删除](10-soft-delete.md)

### 架构师/高级开发者（3 小时）
1. [快速开始](01-quick-start.md)
2. [支持的数据库](02-databases.md)
3. [数据到 API 的完整流程](03-data-flow.md)
4. [架构设计和扩展](07-architecture.md)
5. [搜索和过滤](04-filters.md)
6. [排序功能](05-sorting.md)
7. [完整示例](06-complete-example.md)
8. [批量操作](11-batch-operations.md)
9. [权限控制](12-permissions.md)
10. [审计日志](13-audit-logging.md)

### 生产环境部署（4 小时）
1. [快速开始](01-quick-start.md)
2. [支持的数据库](02-databases.md)
3. [架构设计和扩展](07-architecture.md)
4. [错误处理](09-error-handling.md)
5. [软删除](10-soft-delete.md)
6. [批量操作](11-batch-operations.md)
7. [权限控制](12-permissions.md)
8. [审计日志](13-audit-logging.md)
9. [配置管理](14-configuration.md)
10. [测试指南](15-testing.md)
11. [最佳实践](16-best-practices.md)
12. [故障排除](17-troubleshooting.md)

---

## 相关文档

- [项目分析](../../ANALYSIS_SUMMARY.md)
- [实现路线图](../../IMPLEMENTATION_ROADMAP.md)
- [快速参考](../../QUICK_REFERENCE.md)
- [对比分析](../../BEFORE_AFTER_COMPARISON.md)

---

## 💡 核心概念

### CRUDRouter
自动生成 CRUD 路由的核心类。

```python
from fastapi_easy import CRUDRouter

router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_filters=True,
    enable_sorters=True,
)
```

### Backend
数据库适配器，支持多种 ORM。

```python
from fastapi_easy.backends import SQLAlchemyAsyncBackend

backend = SQLAlchemyAsyncBackend(ItemDB, get_db)
```

### Schema
Pydantic 数据模型，定义 API 的请求和响应格式。

```python
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float
```

---

## 🚀 快速示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float

app = FastAPI()

# 一行代码生成完整的 CRUD API
router = CRUDRouter(schema=Item)
app.include_router(router)

# 自动支持：
# GET /item
# GET /item/{id}
# POST /item
# PUT /item/{id}
# DELETE /item/{id}
# DELETE /item
```

---

## 📊 功能对比

| 功能 | 支持 |
|------|------|
| 基础 CRUD | ✅ |
| 搜索/过滤 | ✅ |
| 排序 | ✅ |
| 分页 | ✅ |
| 软删除 | ✅ |
| 批量操作 | ✅ |
| 权限控制 | ✅ |
| 审计日志 | ✅ |
| 关系处理 | ✅ |

---

## 🆘 常见问题

**Q: 支持哪些数据库？**
A: 支持 SQLite、PostgreSQL、MySQL、Oracle、SQL Server 等。详见 [支持的数据库](02-databases.md)

**Q: 如何使用搜索功能？**
A: 详见 [搜索和过滤](04-filters.md)

**Q: 如何使用排序功能？**
A: 详见 [排序功能](05-sorting.md)

**Q: 如何理解工作流程？**
A: 详见 [数据到 API 的完整流程](03-data-flow.md)

---

## 📝 文档统计

| 指标 | 数值 |
|------|------|
| 总文档数 | 17 份 |
| 总行数 | ~8000 行 |
| 代码示例 | 100+ 个 |
| 图表 | 10+ 个 |

---

## 🎓 学习资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Pydantic 官方文档](https://docs.pydantic.dev/)
- [SQLAlchemy 官方文档](https://docs.sqlalchemy.org/)

---

**开始学习**: [快速开始](01-quick-start.md) →
