"""
FastAPI-Easy 示例 2: 与数据库集成 (使用 SQLAlchemyAdapter)

这个示例展示如何将 CRUDRouter 连接到真实数据库。

对比传统 FastAPI:
  传统 FastAPI: 定义 ORM 模型 + 手动写 8 个数据库操作端点 = 150+ 行
  fastapi-easy: 定义 ORM 模型 + 创建适配器 + CRUDRouter = 30 行

功能:
    - 定义 SQLAlchemy ORM 模型
    - 创建 SQLAlchemyAdapter
    - 自动生成数据库操作的 CRUD API

运行方式:
    python examples/02_with_database.py

访问 API 文档:
    http://localhost:8001/docs

学习内容:
    - 如何定义 SQLAlchemy ORM 模型
    - 如何创建 SQLAlchemyAdapter
    - 如何将适配器传入 CRUDRouter
    - 自动连接到数据库的 CRUD 操作

预计学习时间: 10 分钟
代码行数: ~30 行 (不包括注释)
复杂度: ⭐⭐ 简单
"""

from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel
from typing import Optional
from fastapi_easy import CRUDRouter, SQLAlchemyAdapter

# ============ 1. 数据库配置 ============

DATABASE_URL = "sqlite:///./example.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============ 2. 定义 ORM 模型 ============

class ProductDB(Base):
    """商品数据库模型"""
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    stock = Column(Integer, default=0)


# ============ 3. 定义 Pydantic Schema ============

class Product(BaseModel):
    """商品 API Schema"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0

    class Config:
        from_attributes = True


# ============ 4. 创建 FastAPI 应用 ============

app = FastAPI(
    title="FastAPI-Easy 示例 2",
    description="与数据库集成 - 使用 SQLAlchemyAdapter 自动生成数据库操作 API",
    version="1.0.0",
)


# ============ 5. 创建数据库表 ============

Base.metadata.create_all(bind=engine)


# ============ 6. 创建 SQLAlchemyAdapter (自动连接数据库!) ============

adapter = SQLAlchemyAdapter(model=ProductDB, session_factory=SessionLocal)


# ============ 7. 创建 CRUDRouter (自动生成所有数据库操作!) ============

# 这一行代码就自动生成了所有 CRUD 端点，并连接到数据库！
router = CRUDRouter(schema=Product, adapter=adapter)

# 注册路由
app.include_router(router)


# ============ 8. 根路由 (可选) ============

@app.get("/", tags=["root"])
async def root():
    """欢迎页面"""
    return {
        "message": "欢迎使用 FastAPI-Easy 示例 2",
        "docs": "/docs",
        "note": "所有 CRUD API 已自动生成并连接到数据库！",
        "auto_generated_endpoints": [
            "GET /products - 获取所有商品 (支持分页)",
            "GET /products/{id} - 获取单个商品",
            "POST /products - 创建商品",
            "PUT /products/{id} - 更新商品",
            "DELETE /products/{id} - 删除商品",
        ],
        "database": "SQLite (example.db)"
    }


# ============ 9. 如何运行此示例 ============

if __name__ == "__main__":
    from utils import run_app
    
    # 自动处理端口占用，自动打开浏览器
    run_app(app, start_port=8000, open_browser=True)


# ============ 学习要点 ============

"""
✅ 这个示例展示了什么:

1. 定义 SQLAlchemy ORM 模型
   - 定义表结构
   - 定义列和约束

2. 定义 Pydantic Schema
   - 用于 API 验证和序列化
   - from_attributes = True 允许从 ORM 模型转换

3. 创建 SQLAlchemyAdapter
   - 只需一行代码: adapter = SQLAlchemyAdapter(...)
   - 自动处理数据库连接和会话管理

4. 创建 CRUDRouter 并传入 adapter
   - 只需一行代码: router = CRUDRouter(schema=Product, adapter=adapter)
   - 自动生成所有数据库操作的 CRUD API

5. 自动生成的 API:
   - GET /products - 获取所有商品 (支持分页)
   - GET /products/{id} - 获取单个商品
   - POST /products - 创建商品
   - PUT /products/{id} - 更新商品
   - DELETE /products/{id} - 删除商品

对比传统 FastAPI:
  传统 FastAPI: 150+ 行代码手动写数据库操作
  fastapi-easy: 30 行代码自动生成！

节省 80% 的代码！

❓ 常见问题:

Q: 为什么需要 ORM 模型和 Pydantic Schema?
A: ORM 模型定义数据库表结构，Pydantic Schema 定义 API 请求/响应格式。

Q: 如何使用其他数据库?
A: 修改 DATABASE_URL:
   - PostgreSQL: postgresql://user:password@localhost/dbname
   - MySQL: mysql://user:password@localhost/dbname

Q: 如何添加过滤、排序、分页?
A: 查看示例 3: 03_with_queries.py

Q: 如何添加软删除、审计日志?
A: 查看示例 4: 04_advanced_features.py

🔗 相关文档:
- 支持的数据库: docs/usage/02-databases.md
- CRUDRouter 配置: docs/usage/14-configuration.md
- 最佳实践: docs/usage/16-best-practices.md

📚 下一步:
1. 运行此示例: python examples/02_with_database.py
2. 访问 http://localhost:8001/docs 查看自动生成的 API
3. 尝试创建、读取、更新、删除商品
4. 查看 example.db 文件 (SQLite 数据库)
5. 查看示例 3 学习如何启用过滤、排序、分页
"""
