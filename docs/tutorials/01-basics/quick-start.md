# 快速开始

**预计时间**: 5 分钟  
**难度**: ⭐ 极简  
**目标**: 运行第一个完整的 CRUD API

---

## 1. 安装

```bash
pip install fastapi-easy fastapi uvicorn sqlalchemy aiosqlite
```

---

## 2. 最简单的例子 (SQLite)

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

# 3. 配置数据库 (SQLite)
engine = create_async_engine("sqlite+aiosqlite:///./test.db")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 4. 创建应用
app = FastAPI(title="FastAPI-Easy 快速开始")

# 5. 初始化数据库表 (仅用于演示，生产环境请使用迁移工具)
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

输出:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

---

## 4. 测试 API

访问 http://localhost:8000/docs

你会看到所有自动生成的 API 端点：

- `GET /item` - 获取所有项目
- `GET /item/{id}` - 获取单个项目
- `POST /item` - 创建项目
- `PUT /item/{id}` - 更新项目
- `DELETE /item/{id}` - 删除项目
- `DELETE /item` - 删除所有项目 (需配置开启)

---

## 5. 下一步

现在你已经掌握了基础，可以继续学习:

### 初级 (推荐顺序)

1. **[与数据库集成](database-integration.md)** - 深入了解数据库配置
2. **[查询指南](../../tutorials/02-core-features/querying.md)** - 学习搜索、过滤、排序

### 中级

3. **[完整项目](complete-example.md)** - 查看完整的电商 API
4. **[基础权限](../../security/permissions.md)** - 添加权限控制

### 高级

5. **[架构设计](../../architecture/index.md)** - 深入理解内部架构
6. **[适配器概览](../../reference/adapters/index.md)** - 了解支持的其他数据库
