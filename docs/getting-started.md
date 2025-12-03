# 快速开始

**预计时间**: 5 分钟

---

## 1. 安装

```bash
pip install fastapi-easy fastapi uvicorn sqlalchemy aiosqlite
```

---

## 2. 最简单的例子

创建文件 `main.py`:

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAdapter
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
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

# 3. 配置数据库
engine = create_async_engine("sqlite+aiosqlite:///./test.db")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 4. 创建应用
app = FastAPI(title="FastAPI-Easy 快速开始")

# 5. 初始化数据库表
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 6. 一行代码生成完整的 CRUD API!
router = CRUDRouter(
    schema=Item,
    adapter=SQLAlchemyAdapter(ItemDB, get_db)
)
app.include_router(router)
```

---

## 3. 运行

```bash
uvicorn main:app --reload
```

访问 http://localhost:8000/docs 查看自动生成的 API 文档。

---

## 4. 下一步

- **[用户指南](user-guide/index.md)** - 深入学习各项功能
- **[API 参考](reference/api.md)** - 查看完整的 API 文档
