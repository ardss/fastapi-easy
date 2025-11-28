# FastAPI-Easy 学习路径指南

这个文档帮助用户根据自己的水平选择合适的学习路径。

---

## 🎯 用户分类

### 👶 完全初学者

**背景**: 第一次接触 FastAPI 或 Web 框架

**学习时间**: 1-2 小时

**学习路径**:
```
1. 阅读 README.md (5 分钟)
   ↓
2. 运行 01_hello_world.py (5 分钟)
   ↓
3. 修改代码，看到效果 (10 分钟)
   ↓
4. 阅读 快速开始 文档 (10 分钟)
   ↓
5. 运行 02_with_database.py (10 分钟)
   ↓
6. 创建自己的第一个 API (30 分钟)
```

**关键文档**:
- [快速开始](docs/usage/01-quick-start.md)
- [支持的数据库](docs/usage/02-databases.md)

**示例代码**:
- `examples/01_hello_world.py` (50 行)
- `examples/02_with_database.py` (100 行)

---

### 🎓 有 FastAPI 基础的开发者

**背景**: 了解 FastAPI 基础，想学习 fastapi-easy 的高级功能

**学习时间**: 1-2 小时

**学习路径**:
```
1. 快速浏览 README.md (5 分钟)
   ↓
2. 运行 02_with_database.py (5 分钟)
   ↓
3. 阅读 过滤、排序、分页 文档 (15 分钟)
   ↓
4. 运行 03_with_queries.py (10 分钟)
   ↓
5. 阅读 高级功能 文档 (20 分钟)
   ↓
6. 运行 04_advanced_features.py (10 分钟)
   ↓
7. 实践：添加新功能到自己的项目 (30 分钟)
```

**关键文档**:
- [过滤](docs/usage/04-filters.md)
- [排序](docs/usage/05-sorting.md)
- [软删除](docs/usage/10-soft-delete.md)
- [权限控制](docs/usage/12-permissions.md)
- [审计日志](docs/usage/13-audit-logging.md)

**示例代码**:
- `examples/02_with_database.py` (100 行)
- `examples/03_with_queries.py` (150 行)
- `examples/04_advanced_features.py` (200 行)

---

### 🚀 有生产经验的开发者

**背景**: 有多个生产项目经验，想快速集成 fastapi-easy

**学习时间**: 30 分钟

**学习路径**:
```
1. 阅读 README.md 和 OPTIMIZATION_GUIDE.md (10 分钟)
   ↓
2. 快速浏览 05_complete_ecommerce.py (10 分钟)
   ↓
3. 查看 配置参考 文档 (10 分钟)
   ↓
4. 开始集成到项目中
```

**关键文档**:
- [完整配置参考](docs/usage/14-configuration.md)
- [最佳实践](docs/usage/16-best-practices.md)
- [性能优化指南](OPTIMIZATION_GUIDE.md)

**示例代码**:
- `examples/05_complete_ecommerce.py` (400 行)

---

## 📚 学习资源地图

```
初学者
├─ README.md (项目概述)
├─ examples/01_hello_world.py (最简单的示例)
├─ docs/usage/01-quick-start.md (快速开始)
└─ docs/usage/02-databases.md (数据库配置)

中级开发者
├─ examples/02_with_database.py (数据库集成)
├─ examples/03_with_queries.py (查询功能)
├─ docs/usage/04-filters.md (过滤)
├─ docs/usage/05-sorting.md (排序)
├─ examples/04_advanced_features.py (高级功能)
├─ docs/usage/10-soft-delete.md (软删除)
├─ docs/usage/12-permissions.md (权限)
└─ docs/usage/13-audit-logging.md (审计日志)

高级开发者
├─ examples/05_complete_ecommerce.py (完整项目)
├─ docs/usage/14-configuration.md (配置参考)
├─ docs/usage/16-best-practices.md (最佳实践)
├─ OPTIMIZATION_GUIDE.md (性能优化)
└─ ERROR_ANALYSIS_AND_LESSONS.md (错误分析)
```

---

## 🔄 功能学习顺序

### 第 1 阶段：核心 CRUD (30 分钟)

**目标**: 理解基本的 CRUD 操作

**学习内容**:
- 创建 (Create)
- 读取 (Read)
- 更新 (Update)
- 删除 (Delete)

**示例**: `01_hello_world.py`

**文档**: [快速开始](docs/usage/01-quick-start.md)

**实践**:
```python
# 创建一个简单的 Todo API
class Todo(BaseModel):
    title: str
    completed: bool = False

router = CRUDRouter(schema=Todo)
```

---

### 第 2 阶段：数据库 (30 分钟)

**目标**: 连接真实数据库

**学习内容**:
- 数据库配置
- ORM 模型定义
- 适配器配置

**示例**: `02_with_database.py`

**文档**: [支持的数据库](docs/usage/02-databases.md)

**实践**:
```python
# 配置 SQLAlchemy 适配器
from fastapi_easy import SQLAlchemyAdapter

adapter = SQLAlchemyAdapter(
    model=TodoDB,
    session_factory=SessionLocal
)
```

---

### 第 3 阶段：查询功能 (30 分钟)

**目标**: 实现搜索、过滤、排序、分页

**学习内容**:
- 过滤 (Filtering)
- 排序 (Sorting)
- 分页 (Pagination)
- 搜索 (Search)

**示例**: `03_with_queries.py`

**文档**: 
- [过滤](docs/usage/04-filters.md)
- [排序](docs/usage/05-sorting.md)

**实践**:
```python
# 启用查询功能
router = CRUDRouter(
    schema=Todo,
    adapter=adapter,
    enable_filters=True,
    enable_sorters=True,
    enable_pagination=True,
)

# 使用 API
# GET /todos?title__like=learn&sort=-created_at&skip=0&limit=10
```

---

### 第 4 阶段：高级功能 (1 小时)

**目标**: 实现企业级功能

**学习内容**:
- 软删除 (Soft Delete)
- 权限控制 (Permissions)
- 审计日志 (Audit Logging)
- Hook 系统 (Hooks)

**示例**: `04_advanced_features.py`

**文档**:
- [软删除](docs/usage/10-soft-delete.md)
- [权限控制](docs/usage/12-permissions.md)
- [审计日志](docs/usage/13-audit-logging.md)

**实践**:
```python
# 启用软删除
from fastapi_easy import SoftDeleteConfig

router = CRUDRouter(
    schema=Todo,
    adapter=adapter,
    soft_delete_config=SoftDeleteConfig(enabled=True)
)

# 启用权限控制
from fastapi_easy import PermissionConfig

router = CRUDRouter(
    schema=Todo,
    adapter=adapter,
    permission_config=PermissionConfig(enabled=True)
)
```

---

### 第 5 阶段：完整项目 (2 小时)

**目标**: 构建生产级别的 API

**学习内容**:
- 多资源管理
- 资源关系
- 所有功能的综合应用
- 最佳实践

**示例**: `05_complete_ecommerce.py`

**文档**:
- [完整配置参考](docs/usage/14-configuration.md)
- [最佳实践](docs/usage/16-best-practices.md)

**实践**:
```python
# 构建完整的电商 API
# - 分类管理
# - 商品管理
# - 订单管理
# - 所有高级功能
```

---

## 📊 学习进度跟踪

### 初学者检查清单

- [ ] 理解什么是 CRUD 操作
- [ ] 能运行 `01_hello_world.py`
- [ ] 能修改示例代码并看到效果
- [ ] 理解 Pydantic Schema
- [ ] 能创建简单的 API

**预计时间**: 1 小时

---

### 中级开发者检查清单

- [ ] 理解数据库配置
- [ ] 能使用过滤功能
- [ ] 能使用排序功能
- [ ] 能使用分页功能
- [ ] 理解软删除的概念
- [ ] 能配置权限控制
- [ ] 能启用审计日志

**预计时间**: 2-3 小时

---

### 高级开发者检查清单

- [ ] 理解所有配置选项
- [ ] 能优化性能
- [ ] 能处理复杂的业务逻辑
- [ ] 能使用 Hook 系统
- [ ] 能集成到现有项目
- [ ] 理解最佳实践

**预计时间**: 1-2 小时

---

## 🎓 推荐学习方式

### 方式 1：循序渐进 (推荐初学者)

```
1. 阅读文档
2. 运行示例
3. 修改代码
4. 实践项目
```

**优点**: 循序渐进，容易理解  
**缺点**: 耗时较长

---

### 方式 2：快速上手 (推荐有经验的开发者)

```
1. 快速浏览示例
2. 查看配置参考
3. 开始集成
```

**优点**: 快速高效  
**缺点**: 可能遗漏细节

---

### 方式 3：问题驱动 (推荐实战开发者)

```
1. 遇到问题
2. 查看相关文档
3. 查看示例代码
4. 解决问题
```

**优点**: 针对性强  
**缺点**: 需要主动搜索

---

## 💡 学习建议

### ✅ 应该做

1. **边学边做** - 不要只读文档，要运行代码
2. **修改示例** - 改变参数，看到效果
3. **循序渐进** - 从简单到复杂
4. **查看测试** - 测试代码展示了使用方式
5. **实践项目** - 基于示例创建自己的项目

### ❌ 不应该做

1. **只读不练** - 阅读文档但不运行代码
2. **跳过基础** - 直接学习高级功能
3. **复制粘贴** - 不理解代码就复制
4. **忽视错误** - 遇到错误时放弃
5. **不查文档** - 遇到问题时不查相关文档

---

## 🆘 遇到问题怎么办？

### 问题 1：不知道从哪里开始

**解决方案**:
1. 确定你的水平（初学者/中级/高级）
2. 按照对应的学习路径进行
3. 从第一个示例开始

### 问题 2：代码运行出错

**解决方案**:
1. 查看错误信息
2. 查看 [故障排除](docs/usage/17-troubleshooting.md)
3. 查看相关示例代码
4. 查看测试代码

### 问题 3：不理解某个功能

**解决方案**:
1. 查看对应的文档
2. 查看示例代码
3. 查看测试代码
4. 修改代码，实验

### 问题 4：想要更多示例

**解决方案**:
1. 查看 `tests/unit/` 中的测试代码
2. 查看 `docs/usage/` 中的文档示例
3. 查看 GitHub Issues 中的讨论

---

## 📈 学习效果评估

### 初学者

**学完后能做**:
- ✅ 创建基本的 CRUD API
- ✅ 连接数据库
- ✅ 理解 fastapi-easy 的基本概念

**评估方式**:
- 能独立创建一个简单的 API
- 能解释 CRUD 操作的含义
- 能修改示例代码

---

### 中级开发者

**学完后能做**:
- ✅ 实现复杂的查询功能
- ✅ 配置高级功能
- ✅ 处理实际项目需求

**评估方式**:
- 能实现过滤、排序、分页
- 能配置权限和审计日志
- 能解决常见问题

---

### 高级开发者

**学完后能做**:
- ✅ 优化性能
- ✅ 处理复杂业务逻辑
- ✅ 集成到现有项目

**评估方式**:
- 能配置所有选项
- 能优化查询性能
- 能解决复杂问题

---

## 🎯 下一步

**初学者**: 打开 `examples/01_hello_world.py` 并运行它！

**中级开发者**: 查看 `examples/03_with_queries.py` 并学习查询功能！

**高级开发者**: 查看 `OPTIMIZATION_GUIDE.md` 并优化性能！

---

**祝你学习愉快！** 🚀
