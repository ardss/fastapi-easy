# Tortoise ORM 适配器

Tortoise ORM 是一个易于使用的异步 ORM，灵感来自 Django。

## 安装

```bash
pip install fastapi-easy[tortoise]
pip install tortoise-orm
pip install aiosqlite  # SQLite 异步驱动
```

## 使用示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import TortoiseAdapter
from tortoise import fields
from tortoise.models import Model
from pydantic import BaseModel
from tortoise import Tortoise

# 1. 定义 ORM 模型
class ItemDB(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    price = fields.FloatField()

# 2. 定义 Pydantic Schema
class Item(BaseModel):
    id: int
    name: str
    price: float

# 3. 初始化 Tortoise (通常在 startup 事件中)
async def init_db():
    await Tortoise.init(
        db_url='sqlite://:memory:',
        modules={'models': ['main']}
    )
    await Tortoise.generate_schemas()

# 4. 创建应用和路由
app = FastAPI()

@app.on_event("startup")
async def startup():
    await init_db()

router = CRUDRouter(
    schema=Item,
    adapter=TortoiseAdapter(ItemDB),
    prefix="/items"
)

app.include_router(router)
```

## 特性

- **简单易用**: 类似 Django 的 API。
- **自动迁移**: Tortoise 提供了强大的迁移工具。
- **异步原生**: 从一开始就是为异步设计的。

## 注意事项

- 确保在应用启动时初始化 Tortoise。
- `TortoiseBackend` 不需要传递 session factory，因为 Tortoise 管理自己的连接池。
