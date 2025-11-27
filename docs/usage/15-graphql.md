# GraphQL 支持

fastapi-easy 支持 GraphQL。本指南介绍如何使用 GraphQL 功能。

---

## 启用 GraphQL

```python
from fastapi_easy.graphql import GraphQLConfig

config = GraphQLConfig(
    enabled=True,
    endpoint="/graphql",
    playground=True,
)

router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    graphql_config=config,
)
```

---

## GraphQL 查询

```graphql
query {
  getItem(id: 1) {
    id
    name
    price
  }
  
  listItems(skip: 0, limit: 10) {
    id
    name
  }
}
```

---

## GraphQL 变更

```graphql
mutation {
  createItem(input: {name: "Item", price: 10.0}) {
    id
    name
  }
}
```

---

**下一步**: [WebSocket 支持](16-websocket.md) →
