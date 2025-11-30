# API 参考

本页面提供 FastAPI-Easy 的完整 API 参考文档。

---

## 核心模块

### CRUDRouter

自动生成 CRUD 路由的核心类。

::: fastapi_easy.core.crud_router.CRUDRouter
    options:
      show_root_heading: true
      show_source: false
      members_order: source

---

## 适配器 (Adapters)

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

### CRUD 配置

::: fastapi_easy.core.config.CRUDConfig
    options:
      show_root_heading: true
      show_source: false
      members_order: source

---

## 使用说明

本 API 参考文档自动从代码的 docstring 生成。如果某些类或方法缺少文档，说明源代码中尚未添加文档字符串。

更多详细的使用指南，请参考：

- [快速上手](../tutorial/01-quick-start.md)
- [数据库集成](../tutorial/02-database-integration.md)
- [完整示例](../tutorial/03-complete-example.md)
