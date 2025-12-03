# 📚 FastAPI-Easy 文档重构计划

> **创建时间**: 2025-12-03  
> **目标**: 重构文档结构，提升用户体验和学习效率  
> **预计工作量**: 8-12 小时

---

## 🎯 重构目标

### 核心问题
1. ❌ **信息架构混乱** - `tutorial/` vs `guides/` 职责不清
2. ❌ **内容重复冗余** - 多个文件内容重叠
3. ❌ **文档深度不一致** - 11个安全文档只显示3个
4. ❌ **学习路径缺失** - 没有清晰的初级→高级路径
5. ❌ **分类不合理** - 适配器、开发文档分类混乱

### 重构目标
1. ✅ **清晰的信息架构** - 教程、参考、安全三大支柱
2. ✅ **消除重复内容** - 合并重复文档
3. ✅ **完整的学习路径** - 基础→核心→高级→扩展
4. ✅ **合理的分类** - 按用户意图组织内容
5. ✅ **易于导航** - 左侧导航清晰直观

---

## 📋 新文档结构

```
docs/
├── index.md                          # 首页
├── getting-started.md                # 快速开始
│
├── tutorials/                        # 📖 教程（按学习路径）
│   ├── index.md                      # 教程导航页
│   ├── 01-basics/                    # 基础入门
│   │   ├── index.md
│   │   ├── quick-start.md
│   │   ├── database-integration.md
│   │   └── complete-example.md
│   ├── 02-core-features/             # 核心功能
│   │   ├── index.md
│   │   ├── querying.md
│   │   ├── pagination.md
│   │   ├── error-handling.md
│   │   └── bulk-operations.md
│   ├── 03-advanced/                  # 高级特性
│   │   ├── index.md
│   │   ├── hooks.md
│   │   ├── caching.md
│   │   ├── soft-delete.md
│   │   └── audit-logging.md
│   └── 04-integrations/              # 扩展集成
│       ├── index.md
│       ├── graphql.md
│       ├── websocket.md
│       └── migrations.md
│
├── security/                         # 🔐 安全（独立重要模块）
│   ├── index.md                      # 安全概览
│   ├── authentication.md             # 认证
│   ├── permissions.md                # 权限控制
│   ├── multi-tenancy.md              # 多租户
│   ├── audit-logging.md              # 审计日志
│   ├── rate-limiting.md              # 速率限制
│   └── best-practices.md             # 安全最佳实践
│
├── reference/                        # 📚 参考（查阅型）
│   ├── index.md                      # 参考导航
│   ├── api.md                        # API 参考
│   ├── configuration.md              # 配置参数
│   ├── hooks.md                      # Hook 参考
│   ├── cli.md                        # CLI 工具
│   └── adapters/                     # 数据库适配器
│       ├── index.md
│       ├── sqlalchemy.md
│       ├── sqlmodel.md
│       ├── tortoise.md
│       └── mongodb.md
│
├── architecture/                     # 🏗️ 架构（深度内容）
│   ├── index.md                      # 架构概览
│   ├── design.md                     # 架构设计
│   └── data-flow.md                  # 数据流
│
├── best-practices/                   # 💡 最佳实践
│   ├── index.md                      # 最佳实践导航
│   ├── code-organization.md          # 代码组织
│   ├── performance.md                # 性能优化
│   ├── testing.md                    # 测试策略
│   └── troubleshooting.md            # 故障排查
│
└── contributing/                     # 🤝 贡献
    ├── index.md                      # 贡献指南
    └── development.md                # 开发测试
```

---

## 🗂️ 文件迁移映射表

### 阶段 1: 教程重组

| 旧路径 | 新路径 | 操作 |
|--------|--------|------|
| `tutorial/01-quick-start.md` | `tutorials/01-basics/quick-start.md` | 移动 |
| `tutorial/02-database-integration.md` | `tutorials/01-basics/database-integration.md` | 移动 |
| `tutorial/03-complete-example.md` | `tutorials/01-basics/complete-example.md` | 移动 |
| `guides/querying.md` | `tutorials/02-core-features/querying.md` | 移动 |
| `guides/bulk-operations.md` | `tutorials/02-core-features/bulk-operations.md` | 移动 |
| `guides/error-handling.md` | `tutorials/02-core-features/error-handling.md` | 移动 |
| `guides/hooks-advanced.md` | `tutorials/03-advanced/hooks.md` | 移动+重命名 |
| `guides/caching.md` | `tutorials/03-advanced/caching.md` | 移动 |
| `guides/soft-delete.md` | `tutorials/03-advanced/soft-delete.md` | 移动 |
| `guides/audit-logging-basic.md` | `tutorials/03-advanced/audit-logging.md` | 移动+重命名 |
| `guides/graphql-integration.md` + `guides/graphql.md` | `tutorials/04-integrations/graphql.md` | **合并** |
| `guides/websocket-integration.md` + `guides/websocket.md` | `tutorials/04-integrations/websocket.md` | **合并** |
| `guides/migrations.md` | `tutorials/04-integrations/migrations.md` | 移动 |

### 阶段 2: 安全模块整合

| 旧路径 | 新路径 | 操作 |
|--------|--------|------|
| `security/index.md` | `security/index.md` | 保留+增强 |
| `security/authentication.md` | `security/authentication.md` | 保留 |
| `security/permissions.md` + `guides/permissions-basic.md` | `security/permissions.md` | **合并** |
| `security/multi-tenancy.md` | `security/multi-tenancy.md` | 保留 |
| `security/audit-logging.md` | `security/audit-logging.md` | 保留 |
| `security/password-rate-limit.md` | `security/rate-limiting.md` | 重命名 |
| `security/security-best-practices.md` | `security/best-practices.md` | 重命名 |
| `security/permission-engine.md` | 删除或合并到 `security/permissions.md` | **合并** |
| `security/permission-loader.md` | 删除或合并到 `security/permissions.md` | **合并** |
| `security/resource-checker.md` | 删除或合并到 `security/permissions.md` | **合并** |
| `security/security-config.md` | 删除或合并到 `security/index.md` | **合并** |

### 阶段 3: 参考文档重组

| 旧路径 | 新路径 | 操作 |
|--------|--------|------|
| `reference/api.md` | `reference/api.md` | 保留 |
| `reference/configuration.md` | `reference/configuration.md` | 保留 |
| `reference/hooks.md` | `reference/hooks.md` | 保留 |
| `reference/cli.md` | `reference/cli.md` | 保留 |
| `adapters/index.md` | `reference/adapters/index.md` | 移动 |
| `adapters/sqlalchemy.md` | `reference/adapters/sqlalchemy.md` | 移动 |
| `adapters/sqlmodel.md` | `reference/adapters/sqlmodel.md` | 移动 |
| `adapters/tortoise.md` | `reference/adapters/tortoise.md` | 移动 |
| `adapters/mongodb.md` | `reference/adapters/mongodb.md` | 移动 |

### 阶段 4: 架构文档

| 旧路径 | 新路径 | 操作 |
|--------|--------|------|
| `reference/architecture.md` | `architecture/design.md` | 移动+重命名 |
| `reference/data-flow.md` | `architecture/data-flow.md` | 移动 |

### 阶段 5: 最佳实践

| 旧路径 | 新路径 | 操作 |
|--------|--------|------|
| `guides/best-practices.md` | `best-practices/code-organization.md` | 移动+拆分 |
| `guides/troubleshooting.md` | `best-practices/troubleshooting.md` | 移动 |
| 新建 | `best-practices/performance.md` | **新建** |
| 新建 | `best-practices/testing.md` | **新建** |

### 阶段 6: 贡献文档

| 旧路径 | 新路径 | 操作 |
|--------|--------|------|
| `development/contributing.md` | `contributing/index.md` | 移动+重命名 |
| `development/testing.md` | `contributing/development.md` | 移动+重命名 |

---

## ✅ 执行步骤（TODO）

### Phase 1: 准备工作 ✅
- [x] 分析当前文档结构
- [x] 设计新文档架构
- [x] 创建迁移映射表
- [ ] **备份当前文档** (`git commit` 或创建分支)

### Phase 2: 创建新目录结构
- [ ] 创建 `tutorials/` 及子目录
  - [ ] `tutorials/01-basics/`
  - [ ] `tutorials/02-core-features/`
  - [ ] `tutorials/03-advanced/`
  - [ ] `tutorials/04-integrations/`
- [ ] 创建 `architecture/` 目录
- [ ] 创建 `best-practices/` 目录
- [ ] 创建 `contributing/` 目录
- [ ] 创建 `reference/adapters/` 目录

### Phase 3: 迁移和合并文件
- [ ] **教程模块** (tutorials/)
  - [ ] 移动基础入门文档 (3个文件)
  - [ ] 移动核心功能文档 (4个文件)
  - [ ] 移动高级特性文档 (4个文件)
  - [ ] **合并** GraphQL 文档 (2→1)
  - [ ] **合并** WebSocket 文档 (2→1)
  - [ ] 移动集成文档 (1个文件)
  - [ ] 创建各级 `index.md` 导航页 (5个)

- [ ] **安全模块** (security/)
  - [ ] **合并** 权限相关文档 (4→1)
  - [ ] 重命名速率限制文档
  - [ ] 重命名最佳实践文档
  - [ ] 更新 `index.md` 导航

- [ ] **参考模块** (reference/)
  - [ ] 移动适配器文档 (5个文件)
  - [ ] 创建 `reference/index.md`
  - [ ] 创建 `reference/adapters/index.md`

- [ ] **架构模块** (architecture/)
  - [ ] 移动架构设计文档
  - [ ] 移动数据流文档
  - [ ] 创建 `architecture/index.md`

- [ ] **最佳实践** (best-practices/)
  - [ ] 拆分并移动代码组织文档
  - [ ] 移动故障排查文档
  - [ ] **新建** 性能优化文档
  - [ ] **新建** 测试策略文档
  - [ ] 创建 `best-practices/index.md`

- [ ] **贡献模块** (contributing/)
  - [ ] 移动贡献指南
  - [ ] 移动开发测试文档
  - [ ] 重命名为 `index.md`

### Phase 4: 更新导航配置
- [ ] 更新 `mkdocs.yml` 导航结构
- [ ] 更新首页 (`index.md`) 的文档链接
- [ ] 更新 `getting-started.md` 的"下一步"链接

### Phase 5: 内容增强
- [ ] 为每个目录创建 `index.md` 导航页
- [ ] 添加学习路径指引
- [ ] 添加"上一篇/下一篇"链接
- [ ] 新建缺失的文档:
  - [ ] `best-practices/performance.md`
  - [ ] `best-practices/testing.md`
  - [ ] `tutorials/02-core-features/pagination.md` (如需要)

### Phase 6: 清理和验证
- [ ] 删除旧的空目录
  - [ ] `tutorial/`
  - [ ] `guides/`
  - [ ] `adapters/`
  - [ ] `development/`
- [ ] 删除重复/过时的文档
- [ ] 检查所有内部链接
- [ ] 本地构建测试 (`mkdocs serve`)
- [ ] 修复所有警告和错误

### Phase 7: 最终审查
- [ ] 审查所有文档内容
- [ ] 确保学习路径流畅
- [ ] 检查代码示例
- [ ] 更新 README.md 文档链接
- [ ] Git commit 提交

---

## 📊 工作量估算

| 阶段 | 任务数 | 预计时间 |
|------|--------|----------|
| Phase 1: 准备 | 4 | 0.5h |
| Phase 2: 创建目录 | 8 | 0.5h |
| Phase 3: 迁移文件 | 40+ | 4-6h |
| Phase 4: 更新导航 | 3 | 1h |
| Phase 5: 内容增强 | 10+ | 2-3h |
| Phase 6: 清理验证 | 8 | 1h |
| Phase 7: 最终审查 | 5 | 1h |
| **总计** | **78+** | **10-13h** |

---

## 🎯 优先级建议

### 🔴 高优先级（立即执行）
1. **Phase 1-2**: 准备和创建目录结构
2. **Phase 3**: 迁移教程和安全文档（核心内容）
3. **Phase 4**: 更新导航配置

### 🟡 中优先级（第二批）
4. **Phase 5**: 内容增强和新建文档
5. **Phase 6**: 清理和验证

### 🟢 低优先级（最后）
6. **Phase 7**: 最终审查和优化

---

## 🚀 开始执行

准备好了吗？我们可以按照以下方式执行：

1. **一次性执行** - 我帮你自动完成所有步骤
2. **分阶段执行** - 每次执行一个 Phase，你审查后再继续
3. **手动执行** - 我提供详细指令，你手动操作

请告诉我你希望如何进行！
