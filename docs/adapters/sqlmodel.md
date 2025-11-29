# SQLModel 适配器

SQLModel 是基于 SQLAlchemy 和 Pydantic 构建的库，旨在简化 FastAPI 中的数据库交互。fastapi-easy 提供了专门的适配器。

## 安装

```bash
pip install fastapi-easy[sqlmodel]
pip install sqlmodel
pip install aiosqlite  # SQLite 异步驱动
```

## 使用示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLModelAdapter
from sqlmodel import SQLModel, Field, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

# 1. 定义 SQLModel 模型
# SQLModel 同时是 Pydantic 模型和 SQLAlchemy 模型
class Item(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    price: float

# 2. 配置数据库
DATABASE_URL = "sqlite+aiosqlite:///./test.db"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 3. 创建应用和路由
app = FastAPI()

# 注意：SQLModelAdapter 继承自 SQLAlchemyAdapter
router = CRUDRouter(
    schema=Item,
    adapter=SQLModelAdapter(Item, get_db),
    prefix="/items",
)

app.include_router(router)
```

## 为什么使用 SQLModel？

- **减少重复**: 同一个类既是数据库模型又是 API Schema。
- **类型安全**: 完美的编辑器支持。
- **FastAPI 最佳拍档**: 由 FastAPI 作者开发。

## 注意事项

- `SQLModelAdapter` 本质上是 `SQLAlchemyAdapter` 的封装，因此支持所有 SQLAlchemy 的特性。
- 确保安装了 `sqlmodel` 库。
