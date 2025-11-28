"""
FastAPI-Easy 示例 3: 查询功能 (过滤、排序、分页)

这个示例展示如何实现高级查询功能。

功能:
    - 过滤 (Filtering)
    - 排序 (Sorting)
    - 分页 (Pagination)
    - 搜索 (Search)

运行方式:
    uvicorn examples.03_with_queries:app --reload

访问 API 文档:
    http://localhost:8000/docs

学习内容:
    - 如何实现过滤功能
    - 如何实现排序功能
    - 如何实现分页功能
    - 如何组合多个查询条件

预计学习时间: 20 分钟
代码行数: ~150 行
复杂度: ⭐⭐⭐ 中等

API 使用示例:
    # 基本查询
    GET /products
    
    # 分页
    GET /products?skip=0&limit=10
    
    # 过滤
    GET /products?min_price=100&max_price=1000
    GET /products?category=electronics
    
    # 排序
    GET /products?sort_by=price
    GET /products?sort_by=-price (降序)
    
    # 组合查询
    GET /products?category=electronics&min_price=100&sort_by=-price&skip=0&limit=10
"""

from fastapi import FastAPI, Query
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum

# ============ 1. 数据库配置 ============

DATABASE_URL = "sqlite:///./example_queries.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============ 2. 枚举类型 ============

class Category(str, Enum):
    """商品分类"""
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    BOOKS = "books"
    FOOD = "food"


# ============ 3. ORM 模型 ============

class ProductDB(Base):
    """商品数据库模型"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float, index=True)
    stock = Column(Integer, default=0)
    category = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ 4. Pydantic Schema ============

class Product(BaseModel):
    """商品 API Schema"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    category: Category
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 5. 创建应用 ============

app = FastAPI(
    title="FastAPI-Easy 示例 3",
    description="查询功能 (过滤、排序、分页)",
    version="1.0.0",
)


# ============ 6. 查询参数模型 ============

class QueryParams:
    """查询参数"""
    def __init__(
        self,
        skip: int = Query(0, ge=0, description="跳过的记录数"),
        limit: int = Query(10, ge=1, le=100, description="返回的记录数"),
        category: Optional[Category] = Query(None, description="商品分类"),
        min_price: Optional[float] = Query(None, ge=0, description="最低价格"),
        max_price: Optional[float] = Query(None, ge=0, description="最高价格"),
        search: Optional[str] = Query(None, description="搜索关键词"),
        sort_by: str = Query("created_at", description="排序字段 (前缀 - 表示降序)"),
    ):
        self.skip = skip
        self.limit = limit
        self.category = category
        self.min_price = min_price
        self.max_price = max_price
        self.search = search
        self.sort_by = sort_by


# ============ 7. 定义路由 ============

@app.get("/", tags=["root"])
async def root():
    """根路由"""
    return {
        "message": "欢迎使用 FastAPI-Easy 示例 3",
        "docs": "/docs",
        "features": [
            "过滤 (Filtering)",
            "排序 (Sorting)",
            "分页 (Pagination)",
            "搜索 (Search)",
        ]
    }


@app.get("/products", tags=["products"], summary="获取商品列表 (支持高级查询)")
async def get_products(params: QueryParams = None):
    """
    获取商品列表，支持过滤、排序、分页
    
    查询参数:
        skip: 跳过的记录数 (默认: 0)
        limit: 返回的记录数 (默认: 10, 最大: 100)
        category: 商品分类 (可选)
        min_price: 最低价格 (可选)
        max_price: 最高价格 (可选)
        search: 搜索关键词 (可选)
        sort_by: 排序字段 (默认: created_at, 前缀 - 表示降序)
    
    返回:
        商品列表和分页信息
    
    示例:
        GET /products?category=electronics&min_price=100&sort_by=-price&limit=10
    """
    if params is None:
        params = QueryParams()
    
    db = SessionLocal()
    try:
        query = db.query(ProductDB)
        
        # ========== 过滤 ==========
        
        # 按分类过滤
        if params.category:
            query = query.filter(ProductDB.category == params.category.value)
        
        # 按价格范围过滤
        if params.min_price is not None:
            query = query.filter(ProductDB.price >= params.min_price)
        if params.max_price is not None:
            query = query.filter(ProductDB.price <= params.max_price)
        
        # 按关键词搜索
        if params.search:
            query = query.filter(
                (ProductDB.name.ilike(f"%{params.search}%")) |
                (ProductDB.description.ilike(f"%{params.search}%"))
            )
        
        # ========== 排序 ==========
        
        reverse = params.sort_by.startswith("-")
        sort_field = params.sort_by.lstrip("-")
        
        if sort_field == "price":
            query = query.order_by(ProductDB.price.desc() if reverse else ProductDB.price.asc())
        elif sort_field == "created_at":
            query = query.order_by(ProductDB.created_at.desc() if reverse else ProductDB.created_at.asc())
        elif sort_field == "name":
            query = query.order_by(ProductDB.name.desc() if reverse else ProductDB.name.asc())
        else:
            query = query.order_by(ProductDB.created_at.desc())
        
        # ========== 计算总数 ==========
        
        total = query.count()
        
        # ========== 分页 ==========
        
        products = query.offset(params.skip).limit(params.limit).all()
        
        return {
            "total": total,
            "skip": params.skip,
            "limit": params.limit,
            "items": [Product.model_validate(p) for p in products]
        }
    finally:
        db.close()


@app.get("/products/{product_id}", tags=["products"], summary="获取单个商品")
async def get_product(product_id: int):
    """获取单个商品"""
    db = SessionLocal()
    try:
        product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
        if product:
            return Product.model_validate(product)
        return {"error": "商品不存在"}
    finally:
        db.close()


@app.post("/products", tags=["products"], summary="创建商品", status_code=201)
async def create_product(product: Product):
    """创建新商品"""
    db = SessionLocal()
    try:
        db_product = ProductDB(
            name=product.name,
            description=product.description,
            price=product.price,
            stock=product.stock,
            category=product.category.value,
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return Product.model_validate(db_product)
    finally:
        db.close()


@app.put("/products/{product_id}", tags=["products"], summary="更新商品")
async def update_product(product_id: int, product: Product):
    """更新商品"""
    db = SessionLocal()
    try:
        db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
        if not db_product:
            return {"error": "商品不存在"}
        
        db_product.name = product.name
        db_product.description = product.description
        db_product.price = product.price
        db_product.stock = product.stock
        db_product.category = product.category.value
        db_product.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_product)
        return Product.model_validate(db_product)
    finally:
        db.close()


@app.delete("/products/{product_id}", tags=["products"], summary="删除商品")
async def delete_product(product_id: int):
    """删除商品"""
    db = SessionLocal()
    try:
        db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
        if not db_product:
            return {"error": "商品不存在"}
        
        db.delete(db_product)
        db.commit()
        return {"message": "商品已删除"}
    finally:
        db.close()


# ============ 8. 初始化数据库 ============

@app.on_event("startup")
async def startup_event():
    """应用启动时创建表和初始化数据"""
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        if db.query(ProductDB).count() == 0:
            sample_products = [
                ProductDB(
                    name="笔记本电脑",
                    description="高性能笔记本",
                    price=5999.99,
                    stock=10,
                    category="electronics"
                ),
                ProductDB(
                    name="无线鼠标",
                    description="无线鼠标",
                    price=99.99,
                    stock=50,
                    category="electronics"
                ),
                ProductDB(
                    name="机械键盘",
                    description="机械键盘",
                    price=299.99,
                    stock=30,
                    category="electronics"
                ),
                ProductDB(
                    name="T恤",
                    description="棉质T恤",
                    price=49.99,
                    stock=100,
                    category="clothing"
                ),
                ProductDB(
                    name="牛仔裤",
                    description="蓝色牛仔裤",
                    price=199.99,
                    stock=50,
                    category="clothing"
                ),
                ProductDB(
                    name="Python 编程",
                    description="Python 编程入门",
                    price=89.99,
                    stock=20,
                    category="books"
                ),
            ]
            db.add_all(sample_products)
            db.commit()
    finally:
        db.close()


# ============ 9. 如何运行此示例 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ============ 学习要点 ============

"""
✅ 学到的内容:

1. 过滤 (Filtering)
   - 按字段值过滤
   - 按范围过滤
   - 按多个条件过滤

2. 排序 (Sorting)
   - 升序排序
   - 降序排序 (使用 - 前缀)
   - 按多个字段排序

3. 分页 (Pagination)
   - skip: 跳过的记录数
   - limit: 返回的记录数
   - 计算总记录数

4. 搜索 (Search)
   - 全文搜索
   - 模糊匹配 (LIKE)
   - 多字段搜索

5. 查询优化
   - 使用索引
   - 计算总数
   - 限制返回数量

❓ 常见问题:

Q: 如何组合多个查询条件?
A: 使用 filter() 方法链式调用。

Q: 如何实现全文搜索?
A: 使用 LIKE 或 ILIKE 操作符。

Q: 如何优化查询性能?
A: 添加索引、使用分页、避免 N+1 查询。

Q: 如何处理复杂的排序?
A: 使用多个 order_by() 调用。

🔗 相关文档:
- 过滤: docs/usage/04-filters.md
- 排序: docs/usage/05-sorting.md
- 最佳实践: docs/usage/16-best-practices.md

📚 下一步:
- 测试各种查询组合
- 查看 04_advanced_features.py 学习高级功能
- 查看 05_complete_ecommerce.py 学习完整项目
"""
