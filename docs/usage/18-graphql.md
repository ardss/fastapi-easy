# GraphQL 支持

FastAPI-Easy 提供了完整的 GraphQL 支持，允许你轻松地将 CRUD API 转换为 GraphQL 端点。

---

## 什么是 GraphQL？

GraphQL 是一种 API 查询语言，相比 REST API 有以下优势：

- ✅ **精确查询** - 只获取需要的字段
- ✅ **单一端点** - 所有查询通过一个端点
- ✅ **强类型** - 自动生成 Schema
- ✅ **自文档化** - 自动生成 API 文档

---

## 基础使用

### 1. 安装依赖

```bash
pip install fastapi-easy[graphql]
pip install strawberry-graphql
```

### 2. 定义 GraphQL 类型

```python
from fastapi_easy.graphql import GraphQLType, GraphQLField

# 创建 Item GraphQL 类型
item_type = GraphQLType("Item")
item_type.add_field(GraphQLField("id", "Int", required=True))
item_type.add_field(GraphQLField("name", "String", required=True))
item_type.add_field(GraphQLField("price", "Float", required=True))
item_type.add_field(GraphQLField("description", "String"))

# 获取 GraphQL Schema
schema = item_type.to_schema()
print(schema)
# 输出：
# type Item {
#   id: Int!
#   name: String!
#   price: Float!
#   description: String
# }
```

### 3. 定义 GraphQL 查询

```python
from fastapi_easy.graphql import GraphQLQuery

# 创建查询
get_items_query = GraphQLQuery("items", "Item", list_type=True)
get_item_query = GraphQLQuery("item", "Item", required=True)
get_item_query.add_arg("id", "Int!")

# 获取 GraphQL Schema
print(get_items_query.to_schema())
# 输出：
# items: [Item]

print(get_item_query.to_schema())
# 输出：
# item(id: Int!): Item!
```

---

## 完整示例

### 项目结构

```
my_graphql_app/
├── main.py              # FastAPI 应用
├── models.py            # SQLAlchemy 模型
├── schemas.py           # Pydantic Schema
├── graphql_types.py     # GraphQL 类型定义
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

### 2. 定义 GraphQL 类型

**graphql_types.py**:
```python
from fastapi_easy.graphql import GraphQLType, GraphQLField, GraphQLQuery

# 定义 Item 类型
item_type = GraphQLType("Item")
item_type.add_field(GraphQLField("id", "Int", required=True))
item_type.add_field(GraphQLField("name", "String", required=True))
item_type.add_field(GraphQLField("price", "Float", required=True))
item_type.add_field(GraphQLField("description", "String"))

# 定义查询
get_items_query = GraphQLQuery("items", "Item", list_type=True)
get_item_query = GraphQLQuery("item", "Item", required=True)
get_item_query.add_arg("id", "Int!")

# 定义变更
create_item_mutation = GraphQLQuery("createItem", "Item", required=True)
create_item_mutation.add_arg("name", "String!")
create_item_mutation.add_arg("price", "Float!")
create_item_mutation.add_arg("description", "String")
```

### 3. 创建 FastAPI 应用

**main.py**:
```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAsyncBackend
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from models import ItemDB, Base
from schemas import Item
from graphql_types import item_type, get_items_query, get_item_query

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

# GraphQL Schema 端点
@app.get("/graphql/schema")
async def get_graphql_schema():
    """获取 GraphQL Schema"""
    return {
        "types": [item_type.to_schema()],
        "queries": [
            get_items_query.to_schema(),
            get_item_query.to_schema(),
        ]
    }

# 初始化数据库
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

---

## GraphQL 查询示例

### 查询所有项目

```graphql
query {
  items {
    id
    name
    price
  }
}
```

### 查询单个项目

```graphql
query {
  item(id: 1) {
    id
    name
    price
    description
  }
}
```

### 创建项目

```graphql
mutation {
  createItem(
    name: "Apple"
    price: 1.5
    description: "Fresh apple"
  ) {
    id
    name
    price
  }
}
```

---

## 高级功能

### 1. 自定义字段解析器

```python
from fastapi_easy.graphql import GraphQLField

class CustomGraphQLField(GraphQLField):
    def __init__(self, name: str, resolver: callable):
        super().__init__(name, "String")
        self.resolver = resolver
    
    async def resolve(self, obj):
        return await self.resolver(obj)
```

### 2. 字段别名

```python
# 在查询中使用别名
query = """
query {
  items {
    itemId: id
    itemName: name
    itemPrice: price
  }
}
"""
```

### 3. 片段重用

```graphql
fragment ItemFields on Item {
  id
  name
  price
  description
}

query {
  items {
    ...ItemFields
  }
  item(id: 1) {
    ...ItemFields
  }
}
```

---

## 最佳实践

### 1. 使用片段避免重复

```graphql
# ✅ 推荐
fragment ItemInfo on Item {
  id
  name
  price
}

query {
  items {
    ...ItemInfo
  }
}

# ❌ 不推荐
query {
  items {
    id
    name
    price
    id
    name
    price
  }
}
```

### 2. 使用变量参数化查询

```graphql
# ✅ 推荐
query GetItem($id: Int!) {
  item(id: $id) {
    id
    name
    price
  }
}

# ❌ 不推荐
query {
  item(id: 1) {
    id
    name
    price
  }
}
```

### 3. 限制查询深度

```python
# 防止深层嵌套查询导致性能问题
MAX_QUERY_DEPTH = 5

def validate_query_depth(query: str) -> bool:
    # 检查查询深度
    pass
```

---

## 常见问题

**Q: GraphQL 和 REST API 有什么区别？**

A: GraphQL 允许客户端精确指定需要的数据，而 REST API 返回固定的数据结构。GraphQL 通常更高效，但 REST API 更简单。

**Q: 如何处理 GraphQL 错误？**

A: GraphQL 错误在响应的 `errors` 字段中返回，格式为：
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
- 使用缓存
- 限制查询深度

---

## 相关资源

- [GraphQL 官方文档](https://graphql.org/)
- [Strawberry GraphQL](https://strawberry.rocks/)
- [GraphQL 最佳实践](https://graphql.org/learn/best-practices/)

---

**下一步**: [WebSocket 支持](19-websocket.md) →
