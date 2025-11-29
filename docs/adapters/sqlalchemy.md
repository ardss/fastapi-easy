# SQLAlchemy 适配器 (Async)

SQLAlchemy 是 Python 中最流行的 ORM 之一。fastapi-easy 提供了对 SQLAlchemy 异步模式（AsyncIO）的完整支持。

## 安装

```bash
pip install fastapi-easy[sqlalchemy]
pip install sqlalchemy[asyncio]
pip install aiosqlite  # SQLite 异步驱动
# 或
pip install asyncpg    # PostgreSQL 异步驱动
```

## 使用示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAdapter
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float
from pydantic import BaseModel

# 1. 定义 ORM 模型
Base = declarative_base()

class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)

# 2. 定义 Pydantic Schema
class Item(BaseModel):
    id: int
    name: str
    price: float
    
    class Config:
        from_attributes = True

# 3. 配置数据库连接
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

# 4. 创建应用和路由
app = FastAPI()

router = CRUDRouter(
    schema=Item,
    adapter=SQLAlchemyAdapter(ItemDB, get_db),
    prefix="/items",
)

app.include_router(router)
```

## 特性

- **完全异步**: 基于 `sqlalchemy.ext.asyncio`。
- **自动过滤**: 支持所有标准过滤操作符。
- **自动排序**: 支持多字段排序。
- **分页**: 自动处理 `limit` 和 `offset`。
- **软删除**: 支持软删除配置。

## 常见问题

**Q: 如何处理关系（Relationships）？**
A: 在 Pydantic 模型中定义嵌套模型，并确保 SQLAlchemy 模型配置了 `relationship`。在查询时，可能需要使用 `selectinload` 等加载策略（目前需要通过自定义钩子或覆盖 `get_all` 方法实现复杂加载）。

**Q: 支持同步模式吗？**
A: 目前仅支持异步模式。如果需要同步模式，请使用 FastAPI 的标准同步路由方式，或贡献同步适配器。
