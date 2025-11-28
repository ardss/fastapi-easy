# FastAPI-Easy 示例集合

本目录包含多个循序渐进的示例，帮助用户从基础到高级逐步学习 FastAPI-Easy。

---

## 📚 示例结构

### 第一层：快速开始 (5 分钟)

**文件**: `01_hello_world.py`  
**目标**: 最简单的 CRUD API  
**学习内容**:
- ✅ 如何创建基本的 CRUD 路由
- ✅ 如何定义 Pydantic Schema
- ✅ 如何运行应用

**运行方式**:
```bash
uvicorn examples.01_hello_world:app --reload
```

**代码量**: ~50 行  
**复杂度**: ⭐ 极简

---

### 第二层：数据库集成 (15 分钟)

**文件**: `02_with_database.py`  
**目标**: 连接真实数据库  
**学习内容**:
- ✅ 如何配置数据库连接
- ✅ 如何定义 ORM 模型
- ✅ 如何使用 SQLAlchemy 适配器

**运行方式**:
```bash
uvicorn examples.02_with_database:app --reload
```

**代码量**: ~100 行  
**复杂度**: ⭐⭐ 简单

---

### 第三层：查询功能 (20 分钟)

**文件**: `03_with_queries.py`  
**目标**: 添加搜索、过滤、排序、分页  
**学习内容**:
- ✅ 如何启用过滤功能
- ✅ 如何启用排序功能
- ✅ 如何配置分页
- ✅ 如何使用查询参数

**运行方式**:
```bash
uvicorn examples.03_with_queries:app --reload
```

**代码量**: ~150 行  
**复杂度**: ⭐⭐⭐ 中等

---

### 第四层：高级功能 (30 分钟)

**文件**: `04_advanced_features.py`  
**目标**: 添加软删除、权限、审计日志  
**学习内容**:
- ✅ 如何启用软删除
- ✅ 如何配置权限控制
- ✅ 如何启用审计日志
- ✅ 如何使用 Hook

**运行方式**:
```bash
uvicorn examples.04_advanced_features:app --reload
```

**代码量**: ~200 行  
**复杂度**: ⭐⭐⭐⭐ 复杂

---

### 第五层：完整项目 (1 小时)

**文件**: `05_complete_ecommerce.py`  
**目标**: 完整的电商 API  
**学习内容**:
- ✅ 多个资源的管理
- ✅ 资源之间的关系
- ✅ 所有功能的综合应用
- ✅ 最佳实践

**运行方式**:
```bash
uvicorn examples.05_complete_ecommerce:app --reload
```

**代码量**: ~400 行  
**复杂度**: ⭐⭐⭐⭐⭐ 完整

---

## 🎯 学习路径

### 初学者路径 (30 分钟)

```
01_hello_world.py
    ↓
02_with_database.py
    ↓
03_with_queries.py
```

**学到的内容**:
- 基本 CRUD 操作
- 数据库集成
- 查询功能

---

### 中级开发者路径 (1 小时)

```
02_with_database.py
    ↓
03_with_queries.py
    ↓
04_advanced_features.py
```

**学到的内容**:
- 所有查询功能
- 高级功能（软删除、权限、审计）
- Hook 系统

---

### 完整学习路径 (2 小时)

```
01_hello_world.py
    ↓
02_with_database.py
    ↓
03_with_queries.py
    ↓
04_advanced_features.py
    ↓
05_complete_ecommerce.py
```

**学到的内容**:
- 从基础到高级的完整知识
- 最佳实践
- 实际项目开发

---

## 📖 对应文档

| 示例 | 对应文档 |
|------|---------|
| 01_hello_world.py | [快速开始](../docs/usage/01-quick-start.md) |
| 02_with_database.py | [支持的数据库](../docs/usage/02-databases.md) |
| 03_with_queries.py | [过滤](../docs/usage/04-filters.md)、[排序](../docs/usage/05-sorting.md) |
| 04_advanced_features.py | [软删除](../docs/usage/10-soft-delete.md)、[权限](../docs/usage/12-permissions.md)、[审计日志](../docs/usage/13-audit-logging.md) |
| 05_complete_ecommerce.py | [完整示例](../docs/usage/06-complete-example.md) |

---

## 🚀 快速开始

### 1. 查看最简单的示例

```bash
# 打开并阅读
cat examples/01_hello_world.py

# 运行
uvicorn examples.01_hello_world:app --reload

# 访问 API 文档
open http://localhost:8000/docs
```

### 2. 尝试修改代码

```python
# 在 01_hello_world.py 中修改
# 添加新字段、改变验证规则等
# 实时看到 API 文档的变化
```

### 3. 逐步学习

```bash
# 按顺序学习每个示例
01_hello_world.py → 02_with_database.py → 03_with_queries.py → ...
```

---

## 💡 每个示例的关键特点

### 01_hello_world.py
- **最小化代码** - 只有必要的部分
- **清晰注释** - 解释每一行代码
- **无依赖** - 不需要数据库
- **快速理解** - 5 分钟掌握核心概念

### 02_with_database.py
- **真实数据库** - 使用 SQLite
- **ORM 模型** - 展示如何定义模型
- **适配器** - 展示如何配置适配器
- **完整流程** - 从模型到 API

### 03_with_queries.py
- **过滤示例** - 多种过滤方式
- **排序示例** - 升序/降序
- **分页示例** - skip/limit 用法
- **实际应用** - 真实场景的查询

### 04_advanced_features.py
- **软删除** - 如何启用和使用
- **权限控制** - 基于角色的访问控制
- **审计日志** - 记录所有操作
- **Hook 系统** - 自定义业务逻辑

### 05_complete_ecommerce.py
- **多资源** - 分类、商品、订单
- **资源关系** - 外键关系
- **完整功能** - 所有功能的综合应用
- **最佳实践** - 生产级别的代码

---

## 🧪 测试示例

每个示例都有对应的测试文件：

```bash
# 运行所有示例的测试
pytest tests/unit/test_examples/

# 运行特定示例的测试
pytest tests/unit/test_examples/test_01_hello_world.py -v
```

---

## 📝 示例代码结构

每个示例都遵循相同的结构，便于理解：

```python
"""
示例标题和描述

功能:
- 功能1
- 功能2
- 功能3

运行方式:
    uvicorn examples.XX_name:app --reload

访问:
    http://localhost:8000/docs
"""

# 1. 导入
from fastapi import FastAPI
from pydantic import BaseModel

# 2. 数据模型
class Item(BaseModel):
    name: str
    price: float

# 3. 创建应用
app = FastAPI()

# 4. 创建路由
router = CRUDRouter(...)

# 5. 注册路由
app.include_router(router)

# 6. 根路由
@app.get("/")
async def root():
    return {"message": "..."}
```

---

## 🎓 学习建议

1. **按顺序学习** - 从简单到复杂
2. **边学边做** - 修改代码，看到效果
3. **查看文档** - 每个示例都有对应的文档
4. **运行测试** - 确保理解正确
5. **实践项目** - 基于示例创建自己的项目

---

## ❓ 常见问题

**Q: 我应该从哪个示例开始？**  
A: 如果你是初学者，从 `01_hello_world.py` 开始。如果你已经了解基础，可以从 `02_with_database.py` 开始。

**Q: 示例代码可以直接用于生产吗？**  
A: `05_complete_ecommerce.py` 接近生产级别，但仍需根据实际需求调整。

**Q: 如何修改示例以适应我的项目？**  
A: 复制示例文件，修改数据模型和业务逻辑，其他部分保持不变。

**Q: 示例中使用的数据库是什么？**  
A: 大多数示例使用 SQLite 以便快速运行，生产环境可改为 PostgreSQL 等。

---

## 📚 相关资源

- [完整文档](../docs/usage/README.md)
- [API 参考](../docs/usage/INDEX.md)
- [最佳实践](../docs/usage/16-best-practices.md)
- [故障排除](../docs/usage/17-troubleshooting.md)

---

**开始学习**: 打开 `01_hello_world.py` 并运行它！ 🚀
