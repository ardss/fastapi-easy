"""
FastAPI-Easy 示例 5: 完整项目 (电商 API)

这个示例展示如何在实际项目中使用 fastapi-easy。

功能:
    - 多个资源 (Category, Product, Order)
    - 不同的配置
    - 综合应用所有特性

运行方式:
    python examples/05_complete_ecommerce.py

访问 API 文档:
    http://localhost:8001/docs

学习内容:
    - 如何管理多个资源
    - 如何为不同资源配置不同的功能
    - 如何在实际项目中使用 fastapi-easy

预计学习时间: 15 分钟
代码行数: ~100 行 (不包括注释)
复杂度: ⭐⭐⭐⭐⭐ 完整

API 资源:
    - /categories - 分类管理
    - /products - 商品管理 (支持过滤、排序)
    - /orders - 订单管理 (支持软删除)
"""

from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from fastapi_easy import CRUDRouter, SQLAlchemyAdapter, CRUDConfig

# ============ 1. 数据库配置 ============

DATABASE_URL = "sqlite:///./ecommerce.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============ 2. ORM 模型 ============

class CategoryDB(Base):
    """分类数据库模型"""
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)


class ProductDB(Base):
    """商品数据库模型"""
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float, index=True)
    stock = Column(Integer, default=0)
    category_id = Column(Integer, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class OrderDB(Base):
    """订单数据库模型 (支持软删除)"""
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True)
    customer_name = Column(String, index=True)
    total_amount = Column(Float)
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


# ============ 3. Pydantic Schema ============

class Category(BaseModel):
    """分类 API Schema"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class Product(BaseModel):
    """商品 API Schema"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    category_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class Order(BaseModel):
    """订单 API Schema"""
    id: Optional[int] = None
    order_number: str
    customer_name: str
    total_amount: float
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 4. 创建应用 ============

app = FastAPI(
    title="FastAPI-Easy 示例 5",
    description="完整项目 - 电商 API",
    version="1.0.0",
)

# 创建数据库表
Base.metadata.create_all(bind=engine)


# ============ 5. 为每个资源创建 CRUDRouter ============

# ===== 分类 (基础 CRUD) =====
category_adapter = SQLAlchemyAdapter(model=CategoryDB, session_factory=SessionLocal)
category_router = CRUDRouter(schema=Category, adapter=category_adapter)

# ===== 商品 (启用过滤、排序) =====
product_config = CRUDConfig(
    enable_filters=True,
    enable_sorters=True,
    enable_pagination=True,
    filter_fields=["name", "price", "category_id"],
    sort_fields=["name", "price", "created_at"],
)
product_adapter = SQLAlchemyAdapter(model=ProductDB, session_factory=SessionLocal)
product_router = CRUDRouter(schema=Product, adapter=product_adapter, config=product_config)

# ===== 订单 (启用软删除) =====
order_config = CRUDConfig(
    enable_soft_delete=True,
    enable_audit=True,
    deleted_at_field="deleted_at",
)
order_adapter = SQLAlchemyAdapter(model=OrderDB, session_factory=SessionLocal)
order_router = CRUDRouter(schema=Order, adapter=order_adapter, config=order_config)


# ============ 6. 注册所有路由 ============

app.include_router(category_router)
app.include_router(product_router)
app.include_router(order_router)


# ============ 7. 根路由 ============

@app.get("/", tags=["root"])
async def root():
    """欢迎页面"""
    return {
        "message": "欢迎使用 FastAPI-Easy 示例 5 - 电商 API",
        "docs": "/docs",
        "resources": {
            "categories": {
                "path": "/categories",
                "features": ["基础 CRUD"],
                "endpoints": [
                    "GET /categories - 获取所有分类",
                    "GET /categories/{id} - 获取单个分类",
                    "POST /categories - 创建分类",
                    "PUT /categories/{id} - 更新分类",
                    "DELETE /categories/{id} - 删除分类",
                ]
            },
            "products": {
                "path": "/products",
                "features": ["CRUD", "过滤", "排序", "分页"],
                "endpoints": [
                    "GET /products?skip=0&limit=10 - 获取商品列表",
                    "GET /products?price__gte=100&sort=-price - 过滤和排序",
                    "GET /products/{id} - 获取单个商品",
                    "POST /products - 创建商品",
                    "PUT /products/{id} - 更新商品",
                    "DELETE /products/{id} - 删除商品",
                ]
            },
            "orders": {
                "path": "/orders",
                "features": ["CRUD", "软删除", "审计日志"],
                "endpoints": [
                    "GET /orders - 获取所有订单",
                    "GET /orders/{id} - 获取单个订单",
                    "POST /orders - 创建订单",
                    "PUT /orders/{id} - 更新订单",
                    "DELETE /orders/{id} - 软删除订单",
                ]
            }
        }
    }


# ============ 8. 如何运行此示例 ============

if __name__ == "__main__":
    from utils import run_app
    
    # 自动处理端口占用，自动打开浏览器
    run_app(app, start_port=8000, open_browser=True)


# ============ 学习要点 ============

"""
✅ 这个示例展示了什么:

1. 定义多个 ORM 模型
   - CategoryDB: 分类
   - ProductDB: 商品
   - OrderDB: 订单 (支持软删除)

2. 定义多个 Pydantic Schema
   - Category: 分类 Schema
   - Product: 商品 Schema
   - Order: 订单 Schema

3. 为每个资源创建不同的配置
   - 分类: 基础 CRUD
   - 商品: 启用过滤、排序、分页
   - 订单: 启用软删除、审计日志

4. 为每个资源创建 CRUDRouter
   - 只需一行代码: router = CRUDRouter(...)
   - 所有功能自动生成！

5. 注册所有路由
   - app.include_router(category_router)
   - app.include_router(product_router)
   - app.include_router(order_router)

6. 自动生成的 API:
   - /categories - 完整 CRUD
   - /products - 完整 CRUD + 过滤 + 排序 + 分页
   - /orders - 完整 CRUD + 软删除 + 审计

对比传统 FastAPI:
  传统 FastAPI: 500+ 行代码手动实现所有功能
  fastapi-easy: 100 行代码配置生成！

节省 80% 的代码！

❓ 常见问题:

Q: 如何添加更多资源?
A: 重复相同的步骤：定义 ORM 模型 → 定义 Schema → 创建 CRUDRouter → 注册路由

Q: 如何为不同资源配置不同的功能?
A: 为每个资源创建不同的 CRUDConfig。

Q: 如何处理资源之间的关系?
A: 在 ORM 模型中使用 ForeignKey，在 Schema 中使用 relationship。

Q: 如何添加自定义端点?
A: 使用 @app.get()、@app.post() 等装饰器添加自定义路由。

🔗 相关文档:
- 快速开始: docs/usage/01-quick-start.md
- 配置: docs/usage/14-configuration.md
- 最佳实践: docs/usage/16-best-practices.md

📚 下一步:
1. 运行此示例: python examples/05_complete_ecommerce.py
2. 访问 http://localhost:8001/docs 查看所有 API
3. 尝试创建分类、商品、订单
4. 尝试过滤、排序、分页商品
5. 尝试软删除订单
6. 基于此示例创建自己的项目！
"""
