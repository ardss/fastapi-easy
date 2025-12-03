# API 参考

本页面提供 FastAPI-Easy 的完整 API 参考文档。

---

## 核心模块

### CRUDRouter

自动生成 CRUD 路由的核心类。

**主要功能**:
- 自动生成 6 个标准 CRUD 端点 (GET all, GET one, POST, PUT, DELETE one, DELETE all)
- 支持过滤、排序、分页
- 支持 Hook 系统
- 支持多种 ORM 适配器

**主要方法**:
- `__init__()` - 初始化路由器
- `_generate_routes()` - 生成 CRUD 路由
- `get_config()` - 获取当前配置
- `update_config()` - 更新配置

**使用示例**:
```python
from fastapi_easy import CRUDRouter
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str

router = CRUDRouter(
    schema=Item,
    adapter=your_adapter,
    prefix="/items"
)
```

::: fastapi_easy.core.crud_router.CRUDRouter
    options:
      show_root_heading: true
      show_source: false
      members_order: source

---

## Hook 系统

### HookRegistry

管理操作 Hook 的注册表。

**支持的 Hook 事件** (10 个):
- `before_create` - 创建前
- `after_create` - 创建后
- `before_update` - 更新前
- `after_update` - 更新后
- `before_delete` - 删除前
- `after_delete` - 删除后
- `before_get_all` - 获取所有前
- `after_get_all` - 获取所有后
- `before_get_one` - 获取单个前
- `after_get_one` - 获取单个后

**主要方法**:
- `register(event, callback)` - 注册 Hook
- `unregister(event, callback)` - 取消注册 Hook
- `trigger(event, context)` - 触发 Hook
- `get_hooks(event)` - 获取特定事件的所有 Hook
- `clear(event)` - 清除 Hook

**使用示例**:
```python
async def before_create_hook(context):
    print(f"Creating item: {context.data}")

router.hooks.register("before_create", before_create_hook)
```

::: fastapi_easy.core.hooks.HookRegistry
    options:
      show_root_heading: true
      show_source: false
      members_order: source

---

## ORM 适配器

### ORMAdapter (基类)

所有 ORM 适配器的基类。

**抽象方法** (7 个):
- `get_all(filters, sorts, pagination)` - 获取所有项
- `get_one(id)` - 获取单个项
- `create(data)` - 创建项
- `update(id, data)` - 更新项
- `delete_one(id)` - 删除单个项
- `delete_all()` - 删除所有项
- `count(filters)` - 计数

::: fastapi_easy.core.adapters.ORMAdapter
    options:
      show_root_heading: true
      show_source: false
      members_order: source

### SQLAlchemy 适配器

::: fastapi_easy.backends.sqlalchemy.SQLAlchemyAdapter
    options:
      show_root_heading: true
      show_source: false
      members_order: source

### Tortoise 适配器

::: fastapi_easy.backends.tortoise.TortoiseAdapter
    options:
      show_root_heading: true
      show_source: false
      members_order: source

---

## 配置

### CRUDConfig

CRUD 路由的配置类。

**功能开关** (6 个):
- `enable_filters` - 启用过滤 (默认: True)
- `enable_sorters` - 启用排序 (默认: True)
- `enable_pagination` - 启用分页 (默认: True)
- `enable_soft_delete` - 启用软删除 (默认: False)
- `enable_audit` - 启用审计日志 (默认: False)
- `enable_bulk_operations` - 启用批量操作 (默认: False)

**过滤配置**:
- `filter_fields` - 可过滤字段列表
- `sort_fields` - 可排序字段列表

**分页配置**:
- `default_limit` - 默认分页大小 (默认: 10)
- `max_limit` - 最大分页大小 (默认: 100)

**软删除配置**:
- `deleted_at_field` - 软删除标记字段名 (默认: "deleted_at")

**其他配置**:
- `include_error_details` - 包含错误详情 (默认: True)
- `log_errors` - 记录错误 (默认: True)
- `enable_delete_all` - 启用删除所有 (默认: False, 安全考虑)

**使用示例**:
```python
from fastapi_easy import CRUDConfig

config = CRUDConfig(
    enable_filters=True,
    enable_sorters=True,
    enable_pagination=True,
    default_limit=20,
    max_limit=100,
    filter_fields=["name", "status"],
    sort_fields=["created_at", "name"]
)
```

::: fastapi_easy.core.config.CRUDConfig
    options:
      show_root_heading: true
      show_source: false
      members_order: source

---

## 错误处理

### AppError

应用错误的基类。

**错误代码** (7 个):
- `NOT_FOUND` - 资源未找到 (404)
- `VALIDATION_ERROR` - 验证错误 (422)
- `PERMISSION_DENIED` - 权限拒绝 (403)
- `CONFLICT` - 资源冲突 (409)
- `INTERNAL_ERROR` - 内部错误 (500)
- `UNAUTHORIZED` - 未授权 (401)
- `BAD_REQUEST` - 错误请求 (400)

::: fastapi_easy.core.errors.AppError
    options:
      show_root_heading: true
      show_source: false
      members_order: source

---

## 使用说明

本 API 参考文档自动从代码的 docstring 生成。如果某些类或方法缺少文档，说明源代码中尚未添加文档字符串。

更多详细的使用指南，请参考：

- [快速上手](../tutorials/01-basics/quick-start.md)
- [数据库集成](../tutorials/01-basics/database-integration.md)
- [完整示例](../tutorials/01-basics/complete-example.md)
- [Hook 系统](../reference/hooks.md)
- [配置管理](../reference/configuration.md)
