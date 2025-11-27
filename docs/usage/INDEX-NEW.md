# FastAPI-Easy 使用指南 - 完整索引

FastAPI-Easy 是一个 Python 库，用于快速生成 CRUD API。本指南涵盖所有功能和使用方法。

---

## 📚 文档结构

### 第一部分：快速开始（5 分钟）

**01-quick-start.md** - 快速开始
- 安装说明
- 最简单的例子
- 自动生成的 API
- 代码量对比

**02-databases.md** - 支持的数据库
- 6 种 ORM 支持
- 每种 ORM 的安装和使用
- 数据库选择指南

---

### 第二部分：基础功能（30 分钟）

**03-data-flow.md** - 完整流程
- 数据到 API 的完整流程
- 11 个详细步骤
- 依赖库详解

**04-filters.md** - 过滤功能
- 9 种过滤操作符
- 组合过滤
- 性能建议

**05-sorting.md** - 排序功能
- 升序、降序
- 多字段排序
- 与其他功能组合

**06-complete-example.md** - 完整示例
- 完整的电商 API 项目
- 所有功能演示
- 代码详解

---

### 第三部分：高级功能（1 小时）

**07-architecture.md** - 架构设计和扩展
- 核心架构设计
- 操作系统（Operation System）
- ORM 适配器（ORM Adapter）
- 错误处理系统
- 钩子系统（Hook System）
- 响应格式系统
- 配置系统
- 完整的扩展示例

**08-error-handling.md** - 错误处理
- 内置错误类型
- 自定义错误
- 错误响应格式
- 错误处理中间件

**09-soft-delete.md** - 软删除
- 启用软删除
- 使用软删除
- 恢复已删除的记录
- 最佳实践

**10-batch-operations.md** - 批量操作
- 批量创建、更新、删除
- 处理部分失败
- 事务模式
- 性能优化

**11-permissions.md** - 权限控制
- 基于角色的访问控制（RBAC）
- 基于属性的访问控制（ABAC）
- 集成到 CRUDRouter
- 多租户支持

**12-audit-logging.md** - 审计日志
- 启用审计日志
- 自动记录和手动记录
- 查询审计日志
- 追踪数据变化历史

---

### 第四部分：参考文档（30 分钟）

**18-configuration.md** - 完整配置参考
- CRUDRouter 配置
- 所有功能的配置选项
- 环境变量配置
- 配置优先级
- 常见配置组合

**19-testing.md** - 测试指南
- 单元测试
- 集成测试
- 测试覆盖

**21-best-practices.md** - 最佳实践
- 项目结构
- 代码组织
- 数据库操作
- 性能优化
- 安全性
- 错误处理
- 测试
- 监控和日志
- 常见陷阱

**23-troubleshooting.md** - 故障排除
- 常见问题和解决方案
- 调试技巧
- 获取帮助

---

## 🎯 推荐学习路径

### 路径 1：快速上手（30 分钟）
```
01-quick-start.md
    ↓
02-databases.md
```

### 路径 2：完整学习（2 小时）
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

### 路径 3：深入学习（3 小时）
```
01-quick-start.md
    ↓
02-databases.md
    ↓
03-data-flow.md
    ↓
07-architecture.md ⭐ 重点
    ↓
08-12 高级功能
    ↓
18-21 参考文档
```

---

## 📊 功能清单

| 功能 | 文档 | 状态 |
|------|------|------|
| **核心功能** | | |
| CRUD 操作 | 01, 06 | ✅ |
| 过滤 | 04 | ✅ |
| 排序 | 05 | ✅ |
| 分页 | 03, 06 | ✅ |
| **高级功能** | | |
| 软删除 | 09 | ✅ |
| 批量操作 | 10 | ✅ |
| 权限控制 | 11 | ✅ |
| 审计日志 | 12 | ✅ |
| **系统功能** | | |
| 错误处理 | 08 | ✅ |
| 配置系统 | 18 | ✅ |
| 钩子系统 | 07 | ✅ |
| 响应格式化 | 07, 18 | ✅ |
| 日志系统 | 21 | ✅ |
| 输入验证 | 08 | ✅ |
| 中间件系统 | 21 | ✅ |
| 缓存支持 | 18 | ✅ |
| 速率限制 | 18 | ✅ |

---

## ❓ 常见问题导航

**我想快速开始**
→ 阅读 [01-quick-start.md](01-quick-start.md)

**我想了解支持的数据库**
→ 阅读 [02-databases.md](02-databases.md)

**我想理解工作原理**
→ 阅读 [03-data-flow.md](03-data-flow.md)

**我想使用过滤功能**
→ 阅读 [04-filters.md](04-filters.md)

**我想使用排序功能**
→ 阅读 [05-sorting.md](05-sorting.md)

**我想看完整示例**
→ 阅读 [06-complete-example.md](06-complete-example.md)

**我想深入了解架构**
→ 阅读 [07-architecture.md](07-architecture.md)

**我想处理错误**
→ 阅读 [08-error-handling.md](08-error-handling.md)

**我想使用软删除**
→ 阅读 [09-soft-delete.md](09-soft-delete.md)

**我想批量操作**
→ 阅读 [10-batch-operations.md](10-batch-operations.md)

**我想控制权限**
→ 阅读 [11-permissions.md](11-permissions.md)

**我想审计日志**
→ 阅读 [12-audit-logging.md](12-audit-logging.md)

**我想配置系统**
→ 阅读 [18-configuration.md](18-configuration.md)

**我想测试代码**
→ 阅读 [19-testing.md](19-testing.md)

**我想了解最佳实践**
→ 阅读 [21-best-practices.md](21-best-practices.md)

**我遇到问题**
→ 阅读 [23-troubleshooting.md](23-troubleshooting.md)

---

## 📖 文档统计

- 总文档数：16 份
- 总行数：4000+ 行
- 代码示例：100+ 个
- 功能覆盖：100%

---

**开始学习**: [01-quick-start.md](01-quick-start.md) →
