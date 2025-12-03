# 数据库集成快速指南

**预计时间**: 10 分钟  
**难度**: ⭐⭐ 简单  
**目标**: 快速集成数据库，实现数据持久化

---

## 概述

本指南展示如何将 fastapi-easy 与数据库集成，实现真实的数据持久化。

**支持的数据库**:
- SQLite (推荐用于开发)
- PostgreSQL (推荐用于生产)
- MySQL
- MongoDB

本指南以 **SQLite + SQLAlchemy** 为例 (最简单的方式)。

---

## 1. 安装依赖

```bash
pip install fastapi-easy fastapi uvicorn sqlalchemy
```

---

## 2. 完整示例代码

创建文件 `main_db.py`:

```python
from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel
from typing import Optional
from fastapi_easy import CRUDRouter, SQLAlchemyAdapter

# ============ 1. 数据库配置 ============

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============ 2. 定义 ORM 模型 ============

class ItemDB(Base):
    """数据库模型"""
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)


# ============ 3. 定义 Pydantic Schema ============

class Item(BaseModel):
    """API 数据模型"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    
    class Config:
        from_attributes = True


# ============ 4. 创建表 ============

Base.metadata.create_all(bind=engine)


# ============ 5. 创建应用 ============

app = FastAPI(title="FastAPI-Easy 数据库示例")


# ============ 6. 创建适配器 ============

adapter = SQLAlchemyAdapter(model=ItemDB, session_factory=SessionLocal)


# ============ 7. 创建 CRUDRouter ============

router = CRUDRouter(schema=Item, adapter=adapter)
app.include_router(router)


# ============ 8. 根路由 ============

@app.get("/")
async def root():
    return {
        "message": "欢迎使用 FastAPI-Easy 数据库示例",
        "docs": "/docs",
        "database": "SQLite (test.db)",
        "note": "所有数据都会被持久化到数据库"
    }
```

---

## 3. 运行

```bash
uvicorn main_db:app --reload
```

---

## 4. 测试 API

访问 http://localhost:8000/docs

### 创建项目

```bash
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{
    "name": "笔记本电脑",
    "description": "高性能笔记本",
    "price": 5999.99
  }'
```

响应:
```json
{
  "id": 1,
  "name": "笔记本电脑",
  "description": "高性能笔记本",
  "price": 5999.99
}
```

### 获取所有项目

```bash
curl http://localhost:8000/items
```

响应:
```json
[
  {
    "id": 1,
    "name": "笔记本电脑",
    "description": "高性能笔记本",
    "price": 5999.99
  }
]
```

### 更新项目

```bash
curl -X PUT http://localhost:8000/items/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "笔记本电脑 (更新)",
    "description": "高性能笔记本",
    "price": 6999.99
  }'
```

### 删除项目

```bash
curl -X DELETE http://localhost:8000/items/1
```

---

## 5. 关键概念

### ORM 模型 vs Pydantic Schema

| 方面 | ORM 模型 | Pydantic Schema |
|------|---------|-----------------|
| 用途 | 定义数据库表结构 | 定义 API 请求/响应格式 |
| 位置 | 数据库层 | API 层 |
| 示例 | `ItemDB` | `Item` |
| 字段定义 | SQLAlchemy Column | Pydantic Field |

### SQLAlchemyAdapter

`SQLAlchemyAdapter` 是连接 CRUDRouter 和数据库的桥梁:

```python
adapter = SQLAlchemyAdapter(
    model=ItemDB,              # ORM 模型
    session_factory=SessionLocal  # 数据库会话工厂
)
```

它自动处理:
- 数据库连接
- 会话管理
- CRUD 操作
- 事务管理

---

## 6. 数据持久化验证

重启应用后，数据仍然存在:

```bash
# 第一次运行，创建项目
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "苹果", "price": 15.5}'

# 停止应用 (Ctrl+C)

# 重新启动应用
uvicorn main_db:app --reload

# 数据仍然存在!
curl http://localhost:8000/items
```

---

## 7. 使用其他数据库

### PostgreSQL

```python
# 安装依赖
# pip install psycopg2-binary

DATABASE_URL = "postgresql://user:password@localhost/dbname"
engine = create_engine(DATABASE_URL)
```

### MySQL

```python
# 安装依赖
# pip install pymysql

DATABASE_URL = "mysql+pymysql://user:password@localhost/dbname"
engine = create_engine(DATABASE_URL)
```

### MongoDB

```python
# 安装依赖
# pip install motor

# 使用 Tortoise ORM 而不是 SQLAlchemy
from fastapi_easy import TortoiseAdapter
```

---

## 8. 常见问题

**Q: 如何查看生成的数据库文件?**  
A: SQLite 会在当前目录生成 `test.db` 文件。可以用 SQLite 客户端打开查看。

**Q: 如何添加更多字段?**  
A: 在 ORM 模型中添加列，在 Pydantic Schema 中添加字段:

```python
# ORM 模型
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
    stock = Column(Integer)  # 新字段

# Pydantic Schema
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    price: float
    stock: int = 0  # 新字段
```

**Q: 如何重置数据库?**  
A: 删除 `test.db` 文件，重新运行应用会自动创建新的数据库。

**Q: 如何在生产环境使用?**  
A: 使用 PostgreSQL 或 MySQL，配置环境变量管理数据库 URL。

---

## 9. 下一步

现在你已经掌握了数据库集成，可以继续学习:

1. **[启用查询功能](../guides/querying.md)** - 添加过滤、排序、分页
   - 查看示例: `examples/03_with_queries.py`

2. **[高级功能](../guides/soft-delete.md)** - 软删除、审计日志
   - 查看示例: `examples/04_advanced_features.py`

3. **[完整项目](03-complete-example.md)** - 多资源电商 API
   - 查看示例: `examples/05_complete_ecommerce.py`

---

## 10. 相关资源

- 📚 [完整数据库文档](../adapters/index.md)
- 💻 [示例代码](https://github.com/ardss/fastapi-easy/blob/main/examples/02_with_database.py)
- 🐛 [故障排除](../guides/troubleshooting.md)
- 🎓 [最佳实践](../guides/best-practices.md)
