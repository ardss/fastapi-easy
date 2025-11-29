# FastAPI-Easy 文档重构计划

## 1. 现状分析与问题诊断

经过对 `docs/` 目录和 `src/` 源码的深入对比分析，发现当前文档体系存在以下严重问题：

### 1.1 致命的准确性问题
- **虚假功能宣传**：`docs/usage/02-databases.md` 宣称支持 **Gino** 和 **Ormar**，并提供了详细代码示例，但源码 `src/fastapi_easy/backends/` 中根本不存在这些实现。这会直接导致用户信任崩塌。
- **术语混乱**：文档中混用 "Backend" 和 "Adapter"。
    - 代码事实：`CRUDRouter.__init__` 的参数名为 `adapter`，基类为 `ORMAdapter`。
    - 结论：应统一使用 **Adapter (适配器)** 作为标准术语，"Backend" 仅用于指代底层技术（如 SQLAlchemy Backend）。

### 1.2 结构性混乱
- **文件冲突**：`docs/usage/` 下同时存在 `02-database-quick-guide.md` (教程) 和 `02-databases.md` (手册)，内容重叠且编号冲突。
- **信息孤岛**：`docs/security/` 包含 9 份高质量文档，但在主目录 `docs/usage/` 中几乎没有入口，导致这部分核心价值被埋没。
- **编号断层**：文件编号不连续（如缺 `08`），且缺乏逻辑分组。
- **冗余导航**：多个 `README.md` (根目录, `docs/`, `docs/usage/`) 都在做导航，维护成本高且易不同步。

---

## 2. 重构目标

1.  **单一事实来源 (Single Source of Truth)**：确保文档描述与代码实现（特别是 `CRUDRouter` 和 `CRUDConfig`）完全一致。
2.  **术语标准化**：全局统一使用代码中的术语（如 `Adapter`, `Schema`, `Config`）。
3.  **结构模块化**：采用 **Diátaxis** 框架思想（教程、指南、参考、解释），将文档按功能而非编号分组。
4.  **清理与瘦身**：删除不存在的功能文档，归档过时的过程性文档。

---

## 3. 新文档架构设计

建议废弃扁平的 `docs/usage/01...20` 结构，采用语义化目录结构：

```text
docs/
├── index.md                     # 文档总入口 (原 docs/README.md)
├── tutorial/                    # 教程：手把手教学
│   ├── 01-quick-start.md        # 5分钟上手 (原 usage/01)
│   └── 02-database-integration.md # 数据库集成 (合并原 usage/02 两个文件)
│
├── guides/                      # 指南：特定任务的解决方案
│   ├── querying.md              # 搜索、过滤与排序 (合并 usage/04, 05)
│   ├── pagination.md            # 分页详解
│   ├── error-handling.md        # 错误处理与自定义
│   ├── bulk-operations.md       # 批量操作
│   └── soft-delete.md           # 软删除
│
├── security/                    # 安全：整合现有的 security 目录
│   ├── index.md                 # 安全概览 (引导至子文档)
│   ├── authentication.md
│   ├── permissions.md           # 权限控制 (整合 usage/12)
│   └── audit-logging.md         # 审计日志 (整合 usage/13)
│
├── adapters/                    # 适配器：数据库支持详解
│   ├── index.md                 # 适配器概览 & 选择指南
│   ├── sqlalchemy.md            # SQLAlchemy (Async)
│   ├── tortoise.md              # Tortoise ORM
│   ├── mongodb.md               # MongoDB (Motor)
│   └── sqlmodel.md              # SQLModel
│
├── reference/                   # 参考：API 与配置手册
│   ├── configuration.md         # CRUDConfig 完整参数详解
│   ├── architecture.md          # 架构设计 (原 usage/07)
│   └── hooks.md                 # 钩子系统详解
│
└── development/                 # 开发：贡献与测试
    ├── contributing.md          # (原 DEVELOPMENT.md)
    └── testing.md               # (原 usage/15)
```

---

## 4. 执行计划 (Action Items)

### 第一阶段：清理与修正 (P0 - 立即执行)
1.  **删除虚假内容**：
    - 编辑 `docs/usage/02-databases.md`，**彻底删除** Gino 和 Ormar 的所有章节。
    - 修正 `README.md` 中的支持列表。
2.  **术语统一**：
    - 全局搜索 "Backend"，在指代 `CRUDRouter` 参数或类实例时，替换为 "Adapter"。
    - 明确 `ORMAdapter` 是核心接口。

### 第二阶段：结构重组 (P1)
1.  **创建新目录**：建立 `tutorial`, `guides`, `adapters`, `reference` 目录。
2.  **文件迁移与合并**：
    - `usage/04-filters.md` + `usage/05-sorting.md` -> `guides/querying.md`
    - `usage/02-*.md` -> `tutorial/02-database-integration.md` (保留教程部分，提取手册部分到 `adapters/`)
    - 将 `docs/security/` 下的文件整理，并在 `docs/index.md` 建立索引。

### 第三阶段：内容增强 (P2)
1.  **配置详解**：基于 `src/fastapi_easy/core/config.py`，在 `reference/configuration.md` 中生成一份自动化的配置参数表。
2.  **钩子文档**：专门编写 `reference/hooks.md`，列出所有可用钩子（`before_create`, `after_get_all` 等）及其上下文对象 `ExecutionContext` 的属性。

---

## 5. 核心概念映射表 (用于文档编写)

| 文档术语 | 代码对应 | 说明 |
| :--- | :--- | :--- |
| **Router** | `CRUDRouter` | 核心入口类 |
| **Adapter** | `ORMAdapter` | 数据库适配层 (原 Backend) |
| **Config** | `CRUDConfig` | 集中配置对象 |
| **Schema** | `pydantic.BaseModel` | 数据模型 (API 层) |
| **Model** | (Depends on ORM) | 数据库模型 (ORM 层) |
| **Hook** | `HookRegistry` | 生命周期钩子 |
| **Context** | `ExecutionContext` | 钩子传递的上下文 |

---

## 6. 总结

目前的文档虽然内容丰富，但缺乏维护和系统性规划。通过这次重构，我们将从“堆砌功能介绍”转变为“以用户为中心的文档体系”，确保新手能看懂教程，专家能查到手册，且所有信息真实可靠。
