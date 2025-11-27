# 支持的数据库和 ORM

## 概述

fastapi-easy 支持 4 种 ORM 和数据库，涵盖同步和异步场景：SQLAlchemy、Tortoise、MongoDB、SQLModel。

---

## 1. 内存存储（用于测试）

**适合**: 快速原型、测试、演示

```python
from fastapi_easy import CRUDRouter
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float

router = CRUDRouter(schema=Item)
# 数据存储在内存中，重启后丢失
```

**优点**:
- 无需配置数据库
- 快速测试
- 无依赖

**缺点**:
- 数据不持久化
- 不适合生产环境

---

## 2. SQLAlchemy 异步（推荐）

**适合**: 生产环境、高性能应用

### 安装

```bash
pip install fastapi-easy[sqlalchemy]
pip install sqlalchemy[asyncio]
pip install aiosqlite  # SQLite 异步驱动
# 或
pip install asyncpg    # PostgreSQL 异步驱动
```

### 支持的数据库

- SQLite（开发）
- PostgreSQL（生产）
- MySQL（生产）
- Oracle（生产）
- SQL Server（生产）

### 代码示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAsyncBackend
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
    backend=SQLAlchemyAsyncBackend(ItemDB, get_db),
    prefix="/items",
    tags=["items"]
)

app.include_router(router)
```

**优点**:
- 完全异步
- 支持 SQLAlchemy 2.0
- 高性能
- 支持多种数据库

**缺点**:
- 需要异步驱动
- 学习曲线稍陡

---

## 3. Tortoise ORM

**适合**: 异步应用、快速开发

### 安装

```bash
pip install fastapi-easy[tortoise]
pip install tortoise-orm
pip install aiosqlite  # SQLite 异步驱动
```

### 支持的数据库

- SQLite
- PostgreSQL
- MySQL
- Oracle

### 代码示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import TortoiseBackend
from tortoise import fields
from tortoise.models import Model
from pydantic import BaseModel

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

# 3. 初始化 Tortoise
from tortoise import Tortoise

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
    backend=TortoiseBackend(ItemDB),
    prefix="/items"
)

app.include_router(router)
```

**优点**:
- 异步 ORM
- 简单易用
- 自动迁移

**缺点**:
- 社区相对较小
- 功能不如 SQLAlchemy 完整

---

## 4. Gino

**适合**: 异步应用、PostgreSQL

### 安装

```bash
pip install fastapi-easy[gino]
pip install gino
pip install asyncpg
```

### 代码示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import GinoBackend
from gino import Gino
from pydantic import BaseModel

# 1. 初始化 Gino
db = Gino()

# 2. 定义 ORM 模型
class ItemDB(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String())
    price = db.Column(db.Float())

# 3. 定义 Pydantic Schema
class Item(BaseModel):
    id: int
    name: str
    price: float

# 4. 创建应用和路由
app = FastAPI()

@app.on_event("startup")
async def startup():
    await db.set_bind('postgresql://user:password@localhost/dbname')
    await db.gino.create_all()

router = CRUDRouter(
    schema=Item,
    backend=GinoBackend(ItemDB),
    prefix="/items"
)

app.include_router(router)
```

**优点**:
- 异步 ORM
- PostgreSQL 优化

**缺点**:
- 只支持 PostgreSQL
- 社区较小

---

## 5. Ormar

**适合**: 异步应用、快速开发

### 安装

```bash
pip install fastapi-easy[ormar]
pip install ormar
pip install databases
pip install sqlalchemy
```

### 代码示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import OrmarBackend
import databases
import sqlalchemy
from pydantic import BaseModel
import ormar

# 1. 配置数据库
DATABASE_URL = "sqlite:///./test.db"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

# 2. 定义 ORM 模型
class ItemDB(ormar.Model):
    class Meta:
        metadata = metadata
        database = database
        tablename = "items"
    
    id: int = ormar.Integer(primary_key=True)
    name: str = ormar.String(max_length=100)
    price: float = ormar.Float()

# 3. 定义 Pydantic Schema
class Item(BaseModel):
    id: int
    name: str
    price: float

# 4. 创建应用和路由
app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

router = CRUDRouter(
    schema=Item,
    backend=OrmarBackend(ItemDB),
    prefix="/items"
)

app.include_router(router)
```

**优点**:
- 异步 ORM
- 与 FastAPI 集成好
- 支持多种数据库

**缺点**:
- 相对较新
- 社区较小

---

## 6. Databases（异步驱动）

**适合**: 异步应用、原始 SQL

### 安装

```bash
pip install fastapi-easy[databases]
pip install databases
pip install aiosqlite  # SQLite
# 或
pip install asyncpg    # PostgreSQL
```

### 代码示例

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import DatabasesBackend
import databases
import sqlalchemy
from pydantic import BaseModel

# 1. 配置数据库
DATABASE_URL = "sqlite:///./test.db"
database = databases.Database(DATABASE_URL)

# 2. 定义表
metadata = sqlalchemy.MetaData()
items_table = sqlalchemy.Table(
    "items",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("price", sqlalchemy.Float),
)

# 3. 定义 Pydantic Schema
class Item(BaseModel):
    id: int
    name: str
    price: float

# 4. 创建应用和路由
app = FastAPI()

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

router = CRUDRouter(
    schema=Item,
    backend=DatabasesBackend(items_table, database),
    prefix="/items"
)

app.include_router(router)
```

**优点**:
- 轻量级
- 异步驱动
- 支持原始 SQL

**缺点**:
- 需要手动定义表
- 没有 ORM 的便利

---

## 数据库选择指南

| 场景 | 推荐 | 原因 |
|------|------|------|
| 快速原型 | 内存存储 | 无需配置 |
| 开发环境 | SQLAlchemy + SQLite | 简单易用 |
| 生产环境 | SQLAlchemy + PostgreSQL | 高性能、可靠 |
| 异步应用 | Tortoise / Ormar | 原生异步 |
| PostgreSQL 优化 | Gino | 专门优化 |
| 原始 SQL | Databases | 灵活高效 |

---

## 依赖关系

```
fastapi-easy
├── fastapi
├── pydantic >= 2.0
└── backends/
    ├── SQLAlchemy (可选)
    ├── Tortoise ORM (可选)
    ├── Gino (可选)
    ├── Ormar (可选)
    └── Databases (可选)
```

---

## 下一步

- 学习[搜索和过滤](03-filters.md)
- 了解[排序功能](04-sorting.md)
- 查看[完整示例](05-complete-example.md)
