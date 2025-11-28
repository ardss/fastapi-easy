"""
完整的电商 API 示例

这个示例展示了如何使用 fastapi-easy 快速构建一个功能完整的电商 API。

功能包括：
- CRUD 操作
- 搜索和过滤
- 排序
- 分页
- 异步支持

运行方式：
    uvicorn examples.ecommerce_api:app --reload

访问 API 文档：
    http://localhost:8000/docs
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import asyncio

# ============ 数据模型 ============

class Category(BaseModel):
    """商品分类"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "水果",
                "description": "新鲜水果"
            }
        }


class Product(BaseModel):
    """商品"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    stock: int
    category_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "苹果",
                "description": "新鲜苹果",
                "price": 15.5,
                "stock": 100,
                "category_id": 1,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"
            }
        }


class Order(BaseModel):
    """订单"""
    id: Optional[int] = None
    order_number: str
    total_price: float
    status: str = "pending"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "order_number": "ORD-001",
                "total_price": 150.0,
                "status": "pending",
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"
            }
        }


# ============ 模拟数据存储 ============

# 使用内存存储进行演示
categories_db: List[Category] = []
products_db: List[Product] = []
orders_db: List[Order] = []

category_id_counter = 1
product_id_counter = 1
order_id_counter = 1


# ============ 创建 FastAPI 应用 ============

app = FastAPI(
    title="电商 API",
    description="完整的电商 API 示例，展示 fastapi-easy 的功能",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============ 根路由 ============

@app.get("/")
async def root():
    """根路由"""
    return {
        "message": "欢迎来到电商 API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "categories": "/categories",
            "products": "/products",
            "orders": "/orders"
        }
    }


# ============ 分类 API ============

@app.get("/categories", tags=["categories"], summary="获取所有分类")
async def get_categories(skip: int = 0, limit: int = 10):
    """获取所有分类（支持分页）"""
    total = len(categories_db)
    items = categories_db[skip:skip + limit]
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }


@app.get("/categories/{category_id}", tags=["categories"], summary="获取单个分类")
async def get_category(category_id: int):
    """获取单个分类"""
    for cat in categories_db:
        if cat.id == category_id:
            return cat
    return {"error": "分类不存在"}


@app.post("/categories", tags=["categories"], summary="创建分类", status_code=201)
async def create_category(category: Category):
    """创建新分类"""
    global category_id_counter
    category.id = category_id_counter
    category_id_counter += 1
    categories_db.append(category)
    return category


@app.put("/categories/{category_id}", tags=["categories"], summary="更新分类")
async def update_category(category_id: int, category: Category):
    """更新分类"""
    for i, cat in enumerate(categories_db):
        if cat.id == category_id:
            category.id = category_id
            categories_db[i] = category
            return category
    return {"error": "分类不存在"}


@app.delete("/categories/{category_id}", tags=["categories"], summary="删除分类")
async def delete_category(category_id: int):
    """删除分类"""
    for i, cat in enumerate(categories_db):
        if cat.id == category_id:
            categories_db.pop(i)
            return {"message": "分类已删除"}
    return {"error": "分类不存在"}


# ============ 商品 API ============

@app.get("/products", tags=["products"], summary="获取所有商品")
async def get_products(
    skip: int = 0,
    limit: int = 10,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = "created_at"
):
    """获取所有商品（支持过滤、排序、分页）"""
    # 过滤
    filtered = products_db
    if category_id is not None:
        filtered = [p for p in filtered if p.category_id == category_id]
    if min_price is not None:
        filtered = [p for p in filtered if p.price >= min_price]
    if max_price is not None:
        filtered = [p for p in filtered if p.price <= max_price]
    
    # 排序
    reverse = sort_by.startswith("-")
    sort_field = sort_by.lstrip("-")
    if sort_field == "price":
        filtered = sorted(filtered, key=lambda p: p.price, reverse=reverse)
    elif sort_field == "created_at":
        filtered = sorted(filtered, key=lambda p: p.created_at or datetime.now(), reverse=reverse)
    
    # 分页
    total = len(filtered)
    items = filtered[skip:skip + limit]
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }


@app.get("/products/{product_id}", tags=["products"], summary="获取单个商品")
async def get_product(product_id: int):
    """获取单个商品"""
    for prod in products_db:
        if prod.id == product_id:
            return prod
    return {"error": "商品不存在"}


@app.post("/products", tags=["products"], summary="创建商品", status_code=201)
async def create_product(product: Product):
    """创建新商品"""
    global product_id_counter
    product.id = product_id_counter
    product_id_counter += 1
    product.created_at = datetime.now()
    product.updated_at = datetime.now()
    products_db.append(product)
    return product


@app.put("/products/{product_id}", tags=["products"], summary="更新商品")
async def update_product(product_id: int, product: Product):
    """更新商品"""
    for i, prod in enumerate(products_db):
        if prod.id == product_id:
            product.id = product_id
            product.created_at = prod.created_at
            product.updated_at = datetime.now()
            products_db[i] = product
            return product
    return {"error": "商品不存在"}


@app.delete("/products/{product_id}", tags=["products"], summary="删除商品")
async def delete_product(product_id: int):
    """删除商品"""
    for i, prod in enumerate(products_db):
        if prod.id == product_id:
            products_db.pop(i)
            return {"message": "商品已删除"}
    return {"error": "商品不存在"}


# ============ 订单 API ============

@app.get("/orders", tags=["orders"], summary="获取所有订单")
async def get_orders(
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
    sort_by: str = "-created_at"
):
    """获取所有订单（支持过滤、排序、分页）"""
    # 过滤
    filtered = orders_db
    if status is not None:
        filtered = [o for o in filtered if o.status == status]
    
    # 排序
    reverse = sort_by.startswith("-")
    sort_field = sort_by.lstrip("-")
    if sort_field == "created_at":
        filtered = sorted(filtered, key=lambda o: o.created_at or datetime.now(), reverse=reverse)
    elif sort_field == "total_price":
        filtered = sorted(filtered, key=lambda o: o.total_price, reverse=reverse)
    
    # 分页
    total = len(filtered)
    items = filtered[skip:skip + limit]
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }


@app.get("/orders/{order_id}", tags=["orders"], summary="获取单个订单")
async def get_order(order_id: int):
    """获取单个订单"""
    for order in orders_db:
        if order.id == order_id:
            return order
    return {"error": "订单不存在"}


@app.post("/orders", tags=["orders"], summary="创建订单", status_code=201)
async def create_order(order: Order):
    """创建新订单"""
    global order_id_counter
    order.id = order_id_counter
    order_id_counter += 1
    order.created_at = datetime.now()
    order.updated_at = datetime.now()
    orders_db.append(order)
    return order


@app.put("/orders/{order_id}", tags=["orders"], summary="更新订单")
async def update_order(order_id: int, order: Order):
    """更新订单"""
    for i, ord in enumerate(orders_db):
        if ord.id == order_id:
            order.id = order_id
            order.created_at = ord.created_at
            order.updated_at = datetime.now()
            orders_db[i] = order
            return order
    return {"error": "订单不存在"}


@app.delete("/orders/{order_id}", tags=["orders"], summary="删除订单")
async def delete_order(order_id: int):
    """删除订单"""
    for i, ord in enumerate(orders_db):
        if ord.id == order_id:
            orders_db.pop(i)
            return {"message": "订单已删除"}
    return {"error": "订单不存在"}


# ============ 统计 API ============

@app.get("/stats", tags=["stats"], summary="获取统计信息")
async def get_stats():
    """获取统计信息"""
    return {
        "categories_count": len(categories_db),
        "products_count": len(products_db),
        "orders_count": len(orders_db),
        "total_revenue": sum(o.total_price for o in orders_db),
        "average_order_value": sum(o.total_price for o in orders_db) / len(orders_db) if orders_db else 0,
    }


# ============ 初始化示例数据 ============

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化示例数据"""
    global category_id_counter, product_id_counter, order_id_counter
    
    # 创建示例分类
    categories = [
        Category(name="水果", description="新鲜水果"),
        Category(name="蔬菜", description="新鲜蔬菜"),
        Category(name="肉类", description="优质肉类"),
    ]
    
    for cat in categories:
        cat.id = category_id_counter
        category_id_counter += 1
        categories_db.append(cat)
    
    # 创建示例商品
    products = [
        Product(name="苹果", description="新鲜苹果", price=15.5, stock=100, category_id=1),
        Product(name="香蕉", description="黄色香蕉", price=8.0, stock=150, category_id=1),
        Product(name="番茄", description="红色番茄", price=5.5, stock=200, category_id=2),
        Product(name="牛肉", description="优质牛肉", price=85.0, stock=50, category_id=3),
    ]
    
    for prod in products:
        prod.id = product_id_counter
        product_id_counter += 1
        prod.created_at = datetime.now()
        prod.updated_at = datetime.now()
        products_db.append(prod)
    
    # 创建示例订单
    orders = [
        Order(order_number="ORD-001", total_price=150.0, status="completed"),
        Order(order_number="ORD-002", total_price=200.0, status="pending"),
        Order(order_number="ORD-003", total_price=85.0, status="shipped"),
    ]
    
    for order in orders:
        order.id = order_id_counter
        order_id_counter += 1
        order.created_at = datetime.now()
        order.updated_at = datetime.now()
        orders_db.append(order)


if __name__ == "__main__":
    from utils import run_app
    
    # 使用 run_app 自动处理端口占用问题
    run_app(app, start_port=8000, open_browser=True)
