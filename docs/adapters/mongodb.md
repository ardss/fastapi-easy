# MongoDB 适配器 (Motor)

fastapi-easy 通过 `motor` 驱动提供对 MongoDB 的异步支持。

## 安装

```bash
pip install fastapi-easy[mongodb]
pip install motor
```

## 使用示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import MongoAdapter
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional

# 1. 定义 Pydantic Schema
# 注意：MongoDB 使用 _id，通常映射为 id 字符串
class Item(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str
    price: float

    class Config:
        populate_by_name = True

# 2. 连接 MongoDB
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.test_database
collection = db.items

# 3. 创建应用和路由
app = FastAPI()

router = CRUDRouter(
    schema=Item,
    adapter=MongoAdapter(collection),
    prefix="/items",
)

app.include_router(router)
```

## 特性

- **Motor 驱动**: 高性能异步 MongoDB 驱动。
- **灵活查询**: 支持 MongoDB 的查询语法。
- **自动映射**: 自动处理 `_id` 映射（需配合 Pydantic 配置）。

## 过滤操作符映射

| fastapi-easy 操作符 | MongoDB 操作符 |
| :--- | :--- |
| `exact` | `{field: value}` |
| `ne` | `$ne` |
| `gt` | `$gt` |
| `gte` | `$gte` |
| `lt` | `$lt` |
| `lte` | `$lte` |
| `in` | `$in` |
| `like` | `$regex` |
| `ilike` | `$regex` (with `$options: "i"`) |

## 注意事项

- 确保 Pydantic 模型正确处理 `_id` 字段（通常使用 `alias="_id"`）。
- `MongoAdapter` 直接接受 `motor` 的 `collection` 对象。
