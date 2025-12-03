# GraphQL 集成指南

**难度**: ⭐⭐ 初级  
**预计时间**: 10 分钟  
**前置知识**: [快速开始](../tutorial/01-quick-start.md)

---

## 概述

FastAPI-Easy 支持 GraphQL 集成，允许你通过 GraphQL 查询访问 CRUD API。

---

## 启用 GraphQL

### 安装依赖

```bash
pip install strawberry-graphql
```

### 配置 GraphQL

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

## 性能考虑

### N+1 查询问题

GraphQL 容易出现 N+1 查询问题。使用 DataLoader 解决：

```python
from strawberry.dataloader import DataLoader

async def load_items(ids):
    return await db.query(Item).filter(Item.id.in_(ids)).all()

loader = DataLoader(load_items)
```

### 查询深度限制

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

---

## 最佳实践

1. **使用 DataLoader** - 避免 N+1 查询
2. **限制查询深度** - 防止恶意查询
3. **添加权限检查** - 保护敏感数据
4. **监控查询性能** - 记录慢查询

---

## 总结

GraphQL 集成提供了灵活的查询接口，但需要注意性能问题。

