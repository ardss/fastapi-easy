# 数据到 API 的完整流程

## 概述

本文档详细解释从数据库到 API 的完整流程，以及中间使用的依赖库。

---

## 完整流程图

```
┌─────────────────────────────────────────────────────────────┐
│                      用户请求                                │
│                   (HTTP Request)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI 框架                              │
│  (接收请求、路由匹配、参数验证)                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  fastapi-easy 路由                           │
│  (CRUDRouter 处理请求、调用后端)                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   后端适配器                                 │
│  (SQLAlchemyAdapter / TortoiseAdapter / ...)           │
│  (构建查询、应用过滤、排序、分页)                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    ORM 层                                    │
│  (SQLAlchemy / Tortoise / Gino / ...)                       │
│  (生成 SQL、执行查询)                                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   数据库驱动                                 │
│  (asyncpg / aiosqlite / ...)                                │
│  (异步执行 SQL)                                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    数据库                                    │
│  (PostgreSQL / SQLite / MySQL / ...)                        │
│  (存储和检索数据)                                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   数据返回                                   │
│  (ORM 对象 → Pydantic Schema → JSON)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   HTTP 响应                                  │
│  (JSON 格式返回给客户端)                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 详细步骤说明

### 步骤 1: 用户发送 HTTP 请求

```bash
GET /items?name=apple&price__gt=10&sort=-created_at&skip=0&limit=10
```

**请求包含**:
- 路径: `/items`
- 查询参数: `name=apple`, `price__gt=10`, `sort=-created_at`, `skip=0`, `limit=10`

---

### 步骤 2: FastAPI 接收请求

**依赖库**: `fastapi`

```python
from fastapi import FastAPI

app = FastAPI()

# FastAPI 做的事：
# 1. 路由匹配 (GET /items)
# 2. 参数提取 (name, price__gt, sort, skip, limit)
# 3. 类型验证 (确保参数类型正确)
```

---

### 步骤 3: fastapi-easy 路由处理

**依赖库**: `fastapi-easy`

```python
from fastapi_easy import CRUDRouter

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    enable_filters=True,
    filter_fields=["name", "price"],
    enable_sorters=True,
    sort_fields=["name", "created_at"]
)

# CRUDRouter 做的事：
# 1. 解析过滤参数 (name=apple, price__gt=10)
# 2. 解析排序参数 (sort=-created_at)
# 3. 解析分页参数 (skip=0, limit=10)
# 4. 调用后端处理
```

---

### 步骤 4: 后端适配器处理

**依赖库**: `fastapi-easy.backends`

```python
from fastapi_easy.backends import SQLAlchemyAdapter

adapter = SQLAlchemyAdapter(ItemDB, get_db)

# 后端做的事：
# 1. 构建基础查询
# 2. 应用过滤条件
# 3. 应用排序条件
# 4. 应用分页条件
# 5. 执行查询
```

**具体代码流程**:

```python
# 伪代码
class SQLAlchemyAdapter:
    async def get_all(self, filters, sorts, skip, limit):
        # 1. 构建基础查询
        query = select(ItemDB)
        
        # 2. 应用过滤
        if filters:
            # name=apple → where name = 'apple'
            # price__gt=10 → where price > 10
            query = apply_filters(query, filters)
        
        # 3. 应用排序
        if sorts:
            # sort=-created_at → order by created_at desc
            query = apply_sorts(query, sorts)
        
        # 4. 应用分页
        query = query.offset(skip).limit(limit)
        
        # 5. 执行查询
        result = await db.execute(query)
        return result.scalars().all()
```

---

### 步骤 5: ORM 层生成 SQL

**依赖库**: `sqlalchemy` (或其他 ORM)

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# SQLAlchemy 做的事：
# 1. 将 Python 对象转换为 SQL
# 2. 生成 SQL 语句

# 生成的 SQL 类似于：
# SELECT * FROM items 
# WHERE name = 'apple' AND price > 10 
# ORDER BY created_at DESC 
# LIMIT 10 OFFSET 0
```

---

### 步骤 6: 数据库驱动执行 SQL

**依赖库**: `asyncpg` (PostgreSQL) 或 `aiosqlite` (SQLite)

```python
# asyncpg 做的事：
# 1. 建立数据库连接
# 2. 异步执行 SQL
# 3. 获取结果

# 伪代码
async with engine.connect() as conn:
    result = await conn.execute(sql_statement)
    rows = await result.fetchall()
```

---

### 步骤 7: 数据库返回数据

**数据库**: PostgreSQL / SQLite / MySQL / ...

```
数据库返回的原始数据：
[
    {'id': 1, 'name': 'apple', 'price': 15.5, 'created_at': '2024-01-01'},
    {'id': 2, 'name': 'apple pie', 'price': 25.0, 'created_at': '2024-01-02'},
]
```

---

### 步骤 8: ORM 转换为 Python 对象

**依赖库**: `sqlalchemy`

```python
# SQLAlchemy 做的事：
# 1. 将数据库行转换为 ORM 对象
# 2. 创建 ItemDB 实例

# 转换后：
[
    ItemDB(id=1, name='apple', price=15.5, created_at=datetime(...)),
    ItemDB(id=2, name='apple pie', price=25.0, created_at=datetime(...)),
]
```

---

### 步骤 9: 转换为 Pydantic Schema

**依赖库**: `pydantic`

```python
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float
    created_at: datetime
    
    class Config:
        from_attributes = True

# Pydantic 做的事：
# 1. 验证数据
# 2. 类型转换
# 3. 创建 Pydantic 模型实例

# 转换后：
[
    Item(id=1, name='apple', price=15.5, created_at=datetime(...)),
    Item(id=2, name='apple pie', price=25.0, created_at=datetime(...)),
]
```

---

### 步骤 10: 序列化为 JSON

**依赖库**: `fastapi` (使用 `pydantic` 的序列化)

```python
# FastAPI 做的事：
# 1. 调用 Pydantic 的 model_dump()
# 2. 序列化为 JSON

# 最终 JSON：
{
    "data": [
        {
            "id": 1,
            "name": "apple",
            "price": 15.5,
            "created_at": "2024-01-01T00:00:00"
        },
        {
            "id": 2,
            "name": "apple pie",
            "price": 25.0,
            "created_at": "2024-01-02T00:00:00"
        }
    ],
    "total": 2,
    "page": 1,
    "pages": 1,
    "limit": 10,
    "skip": 0
}
```

---

### 步骤 11: 返回 HTTP 响应

```
HTTP/1.1 200 OK
Content-Type: application/json

{
    "data": [...],
    "total": 2,
    ...
}
```

---

## 依赖库详解

### 核心依赖

| 库 | 版本 | 用途 |
|-----|------|------|
| **fastapi** | ≥0.100 | Web 框架、路由、请求处理 |
| **pydantic** | ≥2.0 | 数据验证、序列化 |
| **typing-extensions** | ≥4.0 | 类型提示 |

### 可选依赖（ORM）

| 库 | 用途 |
|-----|------|
| **sqlalchemy** | ORM、SQL 构建 |
| **tortoise-orm** | 异步 ORM |
| **databases** | 异步数据库驱动 |

### 可选依赖（数据库驱动）

| 库 | 数据库 | 类型 |
|-----|--------|------|
| **aiosqlite** | SQLite | 异步驱动 |
| **asyncpg** | PostgreSQL | 异步驱动 |
| **aiomysql** | MySQL | 异步驱动 |
| **psycopg2** | PostgreSQL | 同步驱动 |
| **pymysql** | MySQL | 同步驱动 |

---

## 完整代码示例

```python
# 1. 导入依赖
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAdapter
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Float
from pydantic import BaseModel

# 2. 定义 ORM 模型（与数据库对应）
Base = declarative_base()

class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)

# 3. 定义 Pydantic Schema（API 响应格式）
class Item(BaseModel):
    id: int
    name: str
    price: float
    
    class Config:
        from_attributes = True

# 4. 配置数据库连接
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

# 5. 创建 FastAPI 应用
app = FastAPI()

# 6. 创建 CRUDRouter（自动生成路由）
router = CRUDRouter(
    schema=Item,
    adapter=SQLAlchemyAdapter(ItemDB, get_db),
    prefix="/items",
    enable_filters=True,
    filter_fields=["name", "price"],
    enable_sorters=True,
    sort_fields=["name"],
)

# 7. 注册路由
app.include_router(router)

# 现在自动支持：
# GET /items?name=apple&price__gt=10&sort=-name
```

---

## 数据流总结

```
用户请求
    ↓
FastAPI (接收、路由)
    ↓
fastapi-easy (解析参数)
    ↓
后端适配器 (构建查询)
    ↓
ORM (生成 SQL)
    ↓
数据库驱动 (执行 SQL)
    ↓
数据库 (返回数据)
    ↓
ORM (转换对象)
    ↓
Pydantic (验证、序列化)
    ↓
FastAPI (返回 JSON)
    ↓
HTTP 响应
```

---

## 下一步

- 学习[搜索和过滤](../guides/querying.md)
- 了解[排序功能](../guides/querying.md)
- 查看[完整示例](../tutorial/03-complete-example.md)
