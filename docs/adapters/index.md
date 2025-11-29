# 适配器概览 (Adapters Overview)

fastapi-easy 通过适配器模式（Adapter Pattern）支持多种数据库后端。这意味着你可以使用统一的 API (`CRUDRouter`) 来操作不同的数据库。

## 支持的适配器

| 适配器 | 底层库 | 数据库支持 | 特点 | 文档 |
| :--- | :--- | :--- | :--- | :--- |
| **SQLAlchemy** | `sqlalchemy` | PostgreSQL, MySQL, SQLite, Oracle, SQL Server | 行业标准，功能最强 | [查看文档](sqlalchemy.md) |
| **Tortoise** | `tortoise-orm` | PostgreSQL, MySQL, SQLite | 类似 Django，简单易用 | [查看文档](tortoise.md) |
| **MongoDB** | `motor` | MongoDB | 高性能异步 NoSQL | [查看文档](mongodb.md) |
| **SQLModel** | `sqlmodel` | 同 SQLAlchemy | 结合 Pydantic 与 SQLAlchemy | [查看文档](sqlmodel.md) |

## 如何选择？

- **新项目 (SQL)**: 推荐 **SQLModel** 或 **SQLAlchemy**。
- **新项目 (NoSQL)**: 使用 **MongoDB**。
- **习惯 Django**: 使用 **Tortoise ORM**。
- **企业级应用**: **SQLAlchemy** 是最稳健的选择。

## 自定义适配器

如果你需要支持其他数据库（如 Redis, Elasticsearch），可以继承 `BaseORMAdapter` 并实现以下方法：

```python
from fastapi_easy.backends.base import BaseORMAdapter

class MyCustomAdapter(BaseORMAdapter):
    async def get_all(self, filters, sorts, pagination):
        ...
    
    async def get_one(self, id):
        ...
        
    async def create(self, data):
        ...
        
    async def update(self, id, data):
        ...
        
    async def delete_one(self, id):
        ...
```
