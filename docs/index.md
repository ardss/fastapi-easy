# FastAPI-Easy

一个现代化的 FastAPI CRUD 框架。用 **10 行代码** 替代 **240+ 行** 的重复代码。

**[快速开始](getting-started.md)** | **[用户指南](user-guide/)** | **[API 参考](reference/api.md)** | **[贡献](development/contributing.md)**

---

## 什么是 FastAPI-Easy？

FastAPI-Easy 自动生成完整的 CRUD API，无需手写重复代码。

**核心特性**:
- 自动生成 6 个标准 API 端点
- 支持过滤、排序、分页
- 支持多种 ORM（SQLAlchemy、Tortoise、MongoDB 等）
- 内置权限控制、审计日志、缓存等

**支持的数据库**: SQLite、PostgreSQL、MySQL、MongoDB、Oracle、SQL Server

---

## 快速开始

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float

app = FastAPI()
router = CRUDRouter(schema=Item)
app.include_router(router)
```

**[完整快速开始指南 →](getting-started.md)**

---

## 文档

- **[用户指南](user-guide/)** - 学习如何使用 FastAPI-Easy
- **[API 参考](reference/api.md)** - 完整的 API 文档
- **[常见问题](faq.md)** - 常见问题解答
- **[贡献](development/contributing.md)** - 如何贡献代码
