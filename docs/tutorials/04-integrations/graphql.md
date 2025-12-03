# GraphQL 集成

**难度**: ⭐⭐ 初级  
**预计时间**: 15 分钟  
**前置知识**: [快速开始](../01-basics/quick-start.md)

---

## 概述

FastAPI-Easy 提供了完整的 GraphQL 支持，允许你轻松地将 CRUD API 转换为 GraphQL 端点。

### 什么是 GraphQL？

GraphQL 是一种 API 查询语言，相比 REST API 有以下优势：

- ✅ **精确查询** - 只获取需要的字段
- ✅ **单一端点** - 所有查询通过一个端点
- ✅ **强类型** - 自动生成 Schema
- ✅ **自文档化** - 自动生成 API 文档

---

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi-easy[graphql]
pip install strawberry-graphql
```

### 2. 基础配置

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.graphql import setup_graphql
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float

app = FastAPI()

# 创建 CRUD 路由
router = CRUDRouter(schema=Item)
app.include_router(router)

# 启用 GraphQL
setup_graphql(app, [Item])
```

访问 `http://localhost:8000/graphql` 查看 GraphQL Playground！

---

## GraphQL 查询示例

### 获取所有项目

```graphql
query {
  items {
    id
    name
    price
  }
}
```

### 获取单个项目

```graphql
query {
  item(id: 1) {
    id
    name
    price
  }
}
```

### 过滤和排序

```graphql
query {
  items(
    filters: {name: "apple"}
    sort: "-price"
    skip: 0
    limit: 10
  ) {
    id
    name
    price
  }
}
```

---

## GraphQL 变更示例

### 创建项目

```graphql
mutation {
  createItem(data: {name: "apple", price: 10.5}) {
    id
    name
    price
  }
}
```

### 更新项目

```graphql
mutation {
  updateItem(id: 1, data: {name: "orange", price: 12.0}) {
    id
    name
    price
  }
}
```

### 删除项目

```graphql
mutation {
  deleteItem(id: 1) {
    id
    name
    price
  }
}
```

---

## 完整示例

### 项目结构

```
my_graphql_app/
├── main.py              # FastAPI 应用
├── models.py            # SQLAlchemy 模型
├── schemas.py           # Pydantic Schema
└── requirements.txt     # 依赖
```

### 1. 定义模型和 Schema

**models.py**:
```python
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
    description = Column(String, nullable=True)
```

**schemas.py**:
```python
from pydantic import BaseModel
from typing import Optional

class Item(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str] = None
    
    class Config:
        from_attributes = True
```

### 2. 创建 FastAPI 应用

**main.py**:
```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAsyncBackend
from fastapi_easy.graphql import setup_graphql
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from models import ItemDB, Base
from schemas import Item

# 配置数据库
DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 创建应用
app = FastAPI()

# 创建 CRUD 路由
backend = SQLAlchemyAsyncBackend(ItemDB, get_db)
router = CRUDRouter(schema=Item, backend=backend)
app.include_router(router)

# 启用 GraphQL
setup_graphql(app, [Item])

# 初始化数据库
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

## 高级功能

### 1. 使用片段避免重复

```graphql
fragment ItemInfo on Item {
  id
  name
  price
}

query {
  items {
    ...ItemInfo
  }
  item(id: 1) {
    ...ItemInfo
  }
}
```

### 2. 使用变量参数化查询

```graphql
query GetItem($id: Int!) {
  item(id: $id) {
    id
    name
    price
  }
}
```

变量：
```json
{
  "id": 1
}
```

### 3. 字段别名

```graphql
query {
  items {
    itemId: id
    itemName: name
    itemPrice: price
  }
}
```

---

## 性能优化

### 1. 解决 N+1 查询问题

GraphQL 容易出现 N+1 查询问题。使用 DataLoader 解决：

```python
from strawberry.dataloader import DataLoader

async def load_items(ids):
    return await db.query(Item).filter(Item.id.in_(ids)).all()

loader = DataLoader(load_items)
```

### 2. 限制查询深度

限制 GraphQL 查询深度以防止恶意查询：

```python
from graphql import validate, NoSchemaIntrospectionCustomRule

setup_graphql(
    app,
    [Item],
    max_depth=5,
    rules=[NoSchemaIntrospectionCustomRule]
)
```

### 3. 查询复杂度分析

```python
# 防止深层嵌套查询导致性能问题
MAX_QUERY_DEPTH = 5
MAX_QUERY_COMPLEXITY = 100

def validate_query_complexity(query: str) -> bool:
    # 检查查询复杂度
    pass
```

---

## 最佳实践

1. **使用 DataLoader** - 避免 N+1 查询问题
2. **限制查询深度** - 防止恶意深层嵌套查询
3. **添加权限检查** - 保护敏感数据访问
4. **监控查询性能** - 记录和分析慢查询
5. **使用片段** - 避免重复的字段定义
6. **参数化查询** - 使用变量而不是硬编码值

---

## 常见问题

**Q: GraphQL 和 REST API 有什么区别？**

A: GraphQL 允许客户端精确指定需要的数据，而 REST API 返回固定的数据结构。GraphQL 通常更高效，但 REST API 更简单。

**Q: 如何处理 GraphQL 错误？**

A: GraphQL 错误在响应的 `errors` 字段中返回：
```json
{
  "errors": [
    {
      "message": "Field not found",
      "locations": [{"line": 1, "column": 5}]
    }
  ]
}
```

**Q: 如何优化 GraphQL 性能？**

A: 
- 使用数据加载器避免 N+1 查询
- 实现查询复杂度分析
- 使用缓存机制
- 限制查询深度和复杂度

---

## 相关资源

- [GraphQL 官方文档](https://graphql.org/)
- [Strawberry GraphQL](https://strawberry.rocks/)
- [GraphQL 最佳实践](https://graphql.org/learn/best-practices/)

---

## 总结

GraphQL 集成提供了灵活强大的查询接口，但需要注意性能和安全问题。通过合理使用 DataLoader、查询深度限制和复杂度分析，可以构建高性能的 GraphQL API。

---

**下一步**: [WebSocket 支持](websocket.md) →
