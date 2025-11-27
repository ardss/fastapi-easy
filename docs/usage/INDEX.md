# 使用指南完整索引

## 📚 文档概览

fastapi-easy 使用指南现在包含 **17 份详细文档**，涵盖从快速开始到高级架构设计的所有内容。

---

## 📖 文档清单

### 基础文档（适合所有开发者）

#### 1. [快速开始](01-quick-start.md) ⭐ 从这里开始
- **内容**: 安装、最简单的例子、自动生成的 API
- **时间**: 5 分钟
- **目标**: 快速上手，5 分钟内运行第一个 API

#### 2. [支持的数据库](02-databases.md)
- **内容**: 4 种 ORM 支持（SQLAlchemy、Tortoise、MongoDB、SQLModel）、安装指南、数据库选择
- **时间**: 20 分钟
- **目标**: 了解支持的数据库和 ORM，选择合适的方案

#### 3. [数据到 API 的完整流程](03-data-flow.md)
- **内容**: 完整流程图、11 个详细步骤、依赖库详解
- **时间**: 15 分钟
- **目标**: 理解内部工作原理，知道数据如何变成 API

---

### 功能文档（适合普通开发者）

#### 4. [搜索和过滤](04-filters.md)
- **内容**: 9 种过滤操作符、组合过滤、性能建议
- **时间**: 10 分钟
- **目标**: 学会使用搜索和过滤功能

#### 5. [排序功能](05-sorting.md)
- **内容**: 升序、降序、多字段排序、与其他功能组合
- **时间**: 10 分钟
- **目标**: 学会使用排序功能

#### 6. [完整示例](06-complete-example.md)
- **内容**: 完整的电商 API 项目、所有功能演示、代码详解
- **时间**: 20 分钟
- **目标**: 看到完整的项目实现，理解如何组合各个功能

---

### 高级文档（适合架构师和高级开发者）

#### 7. [架构设计和扩展](07-architecture.md) ⭐ 重点
- **内容**:
  - 核心架构设计（分离职责）
  - 操作系统（Operation System）
  - ORM 适配器（ORM Adapter）
  - 错误处理系统（结构化错误）
  - 钩子系统（Hook System）
  - 响应格式系统（自定义响应）
  - 配置系统（集中配置）
  - 完整的扩展示例
- **时间**: 30 分钟
- **目标**: 深入理解架构，学会进行高度定制

---

### 企业级功能文档（适合生产环境）

#### 8. [错误处理](09-error-handling.md)
- **内容**: 内置错误类型、自定义错误、错误响应、错误处理中间件
- **时间**: 10 分钟
- **目标**: 学会处理和自定义错误

#### 9. [软删除](10-soft-delete.md)
- **内容**: 软删除配置、恢复数据、查询已删除记录、最佳实践
- **时间**: 15 分钟
- **目标**: 实现数据安全删除和恢复

#### 10. [批量操作](11-batch-operations.md)
- **内容**: 批量创建、更新、删除、性能优化
- **时间**: 15 分钟
- **目标**: 提高大批量数据操作的效率

#### 11. [权限控制](12-permissions.md)
- **内容**: RBAC、ABAC、权限检查、多租户支持
- **时间**: 20 分钟
- **目标**: 实现安全的权限管理

#### 12. [审计日志](13-audit-logging.md)
- **内容**: 审计日志配置、记录操作、查询历史、合规性
- **时间**: 15 分钟
- **目标**: 追踪所有数据变更

#### 13. [配置管理](14-configuration.md)
- **内容**: 集中配置、功能开关、环境变量、最佳实践
- **时间**: 15 分钟
- **目标**: 灵活管理应用配置

#### 14. [测试指南](15-testing.md)
- **内容**: 单元测试、集成测试、测试工具、示例
- **时间**: 20 分钟
- **目标**: 编写高质量的测试

#### 15. [最佳实践](16-best-practices.md)
- **内容**: 代码组织、性能优化、安全建议、常见陷阱
- **时间**: 20 分钟
- **目标**: 遵循行业最佳实践

#### 16. [故障排除](17-troubleshooting.md)
- **内容**: 常见问题、调试技巧、性能问题、错误解决
- **时间**: 15 分钟
- **目标**: 快速解决常见问题

---

## 🎯 推荐学习路径

### 路径 1: 快速上手（30 分钟）
```
01-quick-start.md
    ↓
02-databases.md
```
**适合**: 想快速开始使用的开发者

---

### 路径 2: 完整学习（1.5 小时）
```
01-quick-start.md
    ↓
02-databases.md
    ↓
03-data-flow.md
    ↓
04-filters.md
    ↓
05-sorting.md
    ↓
06-complete-example.md
```
**适合**: 想全面了解功能的开发者

---

### 路径 3: 架构设计（2 小时）
```
01-quick-start.md
    ↓
02-databases.md
    ↓
03-data-flow.md
    ↓
07-architecture.md ⭐ 重点
    ↓
04-filters.md
    ↓
05-sorting.md
    ↓
06-complete-example.md
```
**适合**: 想深入理解架构和进行高度定制的开发者

---

## 📊 文档统计

| 指标 | 数值 |
|------|------|
| 总文档数 | 17 份 |
| 总行数 | ~8000 行 |
| 代码示例 | 100+ 个 |
| 架构图 | 3 个 |
| 对比表格 | 30+ 个 |

---

## 🔑 核心概念速览

### 分离的职责
```
CRUDGenerator → OperationRegistry → APIRouter
```

### 操作系统
- 内置操作: GetAll、GetOne、Create、Update、DeleteOne、DeleteAll
- 自定义操作: 搜索、导出、导入等
- 钩子系统: before_execute、after_execute

### ORM 适配器
- 统一的 ORM 接口
- SQLAlchemy、Tortoise、MongoDB、SQLModel
- 易于添加新的 ORM

### 错误处理
- 结构化错误（ErrorCode、AppError）
- 错误中间件
- 自定义错误响应

### 钩子系统
- 全局钩子注册表
- 支持的事件: before_create、after_create、before_delete 等
- 用于权限检查、日志记录、通知发送等

### 响应格式
- 默认分页响应
- 自定义响应格式化器
- 支持 GraphQL 等格式

### 配置系统
- 集中配置对象
- 功能开关
- 字段配置

---

## 💡 关键改进点

### 解决的问题

✅ **职责混乱** → 分离 CRUDGenerator 和 APIRouter
✅ **模板方法局限** → 操作系统支持自定义操作
✅ **ORM 抽象不足** → 统一的 ORM 适配器接口
✅ **错误处理简单** → 结构化错误系统
✅ **缺少钩子** → 完整的钩子系统
✅ **响应格式固定** → 自定义响应格式化器
✅ **配置参数多** → 集中配置对象

---

## 🚀 快速参考

### 基础使用
```python
from fastapi_easy import CRUDRouter
router = CRUDRouter(schema=Item, backend=backend)
```

### 启用功能
```python
router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_filters=True,
    enable_sorters=True,
    enable_soft_delete=True,
)
```

### 自定义操作
```python
class CustomOperation(Operation):
    async def execute(self, context):
        pass

router.register_operation(CustomOperation())
```

### 注册钩子
```python
async def on_create(context):
    await send_email(context.result.email)

router.hooks.register("after_create", on_create)
```

### 自定义响应
```python
class CustomFormatter(ResponseFormatter):
    def format_list(self, items, total, pagination):
        return {"items": items, "meta": {...}}

router = CRUDRouter(
    schema=Item,
    backend=backend,
    response_formatter=CustomFormatter()
)
```

---

## 📚 相关文档

- [项目分析](../../ANALYSIS_SUMMARY.md)
- [实现路线图](../../IMPLEMENTATION_ROADMAP.md)
- [快速参考](../../QUICK_REFERENCE.md)
- [对比分析](../../BEFORE_AFTER_COMPARISON.md)
- [项目 README](../../README.md)

---

## 🎓 学习建议

1. **第一天**: 阅读 01-quick-start 和 02-databases，运行第一个例子
2. **第二天**: 阅读 03-data-flow 和 04-filters，理解工作原理
3. **第三天**: 阅读 05-sorting 和 06-complete-example，看完整项目
4. **第四天**: 阅读 07-architecture，学习如何扩展

---

## ❓ 常见问题

**Q: 我应该从哪里开始？**
A: 从 [快速开始](01-quick-start.md) 开始，5 分钟内运行第一个 API。

**Q: 我想了解所有功能**
A: 按照"路径 2: 完整学习"阅读所有文档。

**Q: 我想进行高度定制**
A: 重点阅读 [架构设计和扩展](07-architecture.md)。

**Q: 我想了解工作原理**
A: 阅读 [数据到 API 的完整流程](03-data-flow.md)。

---

## 📝 文档版本

- **版本**: 1.0
- **最后更新**: 2024 年
- **总字数**: ~3500 行

---

**开始学习**: [快速开始](01-quick-start.md) →
