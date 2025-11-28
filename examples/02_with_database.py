"""
FastAPI-Easy 示例 2: 与数据库集成

这个示例展示如何使用真实数据库 (SQLite) 和 SQLAlchemy ORM。

功能:
    - 使用 SQLAlchemy 定义 ORM 模型
    - 配置数据库连接
    - 使用 SQLAlchemy 适配器
    - 自动生成 CRUD 路由

运行方式:
    uvicorn examples.02_with_database:app --reload

访问 API 文档:
    http://localhost:8000/docs

学习内容:
    - 如何定义 SQLAlchemy ORM 模型
    - 如何配置数据库连接
    - 如何使用 SQLAlchemy 适配器
    - 如何处理数据库会话

预计学习时间: 15 分钟
代码行数: ~100 行
复杂度: ⭐⭐ 简单
"""

from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ============ 1. 数据库配置 ============

# 使用 SQLite 数据库 (简单，无需额外配置)
DATABASE_URL = "sqlite:///./example.db"

# 创建同步引擎 (用于初始化表)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


# ============ 2. 定义 ORM 模型 ============

class ProductDB(Base):
    """
    商品数据库模型
    
    表名: products
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ 3. 定义 Pydantic Schema ============

class Product(BaseModel):
    """
    商品 API Schema
    """
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # 允许从 ORM 模型读取属性
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "笔记本电脑",
                "description": "高性能笔记本",
                "price": 5999.99,
                "stock": 10,
                "created_at": "2025-01-01T00:00:00",
                "updated_at": "2025-01-01T00:00:00"
            }
        }


# ============ 4. 创建 FastAPI 应用 ============

app = FastAPI(
    title="FastAPI-Easy 示例 2",
    description="与数据库集成的 CRUD API",
    version="1.0.0",
)


# ============ 5. 数据库依赖 ============

def get_db():
    """
    获取数据库会话
    
    这是一个依赖函数，FastAPI 会自动注入到路由中
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ 6. 定义 CRUD 路由 ============

@app.get("/", tags=["root"])
async def root():
    """根路由"""
    return {
        "message": "欢迎使用 FastAPI-Easy 示例 2",
        "docs": "/docs",
        "features": [
            "SQLAlchemy ORM 集成",
            "数据库持久化",
            "自动表创建",
        ]
    }


@app.get("/products", tags=["products"], summary="获取所有商品")
async def get_products(skip: int = 0, limit: int = 10, db: Session = None):
    """
    获取所有商品 (支持分页)
    
    参数:
        skip: 跳过的商品数
        limit: 返回的商品数
    
    返回:
        商品列表
    """
    # 注意: 在实际应用中，db 会由 FastAPI 自动注入
    # 这里为了简化，我们手动创建会话
    if db is None:
        db = SessionLocal()
    
    try:
        total = db.query(ProductDB).count()
        products = db.query(ProductDB).offset(skip).limit(limit).all()
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [Product.model_validate(p) for p in products]
        }
    finally:
        if db:
            db.close()


@app.get("/products/{product_id}", tags=["products"], summary="获取单个商品")
async def get_product(product_id: int):
    """
    获取单个商品
    
    参数:
        product_id: 商品 ID
    
    返回:
        商品信息
    """
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
    """
    创建新商品
    
    参数:
        product: 商品信息
    
    返回:
        创建的商品信息 (包含 ID)
    """
    db = SessionLocal()
    try:
        db_product = ProductDB(
            name=product.name,
            description=product.description,
            price=product.price,
            stock=product.stock,
        )
        db.add(db_product)
        db.commit()
        db.refresh(db_product)
        return Product.model_validate(db_product)
    finally:
        db.close()


@app.put("/products/{product_id}", tags=["products"], summary="更新商品")
async def update_product(product_id: int, product: Product):
    """
    更新商品
    
    参数:
        product_id: 商品 ID
        product: 新的商品信息
    
    返回:
        更新后的商品信息
    """
    db = SessionLocal()
    try:
        db_product = db.query(ProductDB).filter(ProductDB.id == product_id).first()
        if not db_product:
            return {"error": "商品不存在"}
        
        db_product.name = product.name
        db_product.description = product.description
        db_product.price = product.price
        db_product.stock = product.stock
        db_product.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_product)
        return Product.model_validate(db_product)
    finally:
        db.close()


@app.delete("/products/{product_id}", tags=["products"], summary="删除商品")
async def delete_product(product_id: int):
    """
    删除商品
    
    参数:
        product_id: 商品 ID
    
    返回:
        删除结果
    """
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


# ============ 7. 初始化数据库 ============

@app.on_event("startup")
async def startup_event():
    """
    应用启动时创建表和初始化数据
    """
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 初始化示例数据
    db = SessionLocal()
    try:
        # 检查是否已有数据
        if db.query(ProductDB).count() == 0:
            sample_products = [
                ProductDB(
                    name="笔记本电脑",
                    description="高性能笔记本",
                    price=5999.99,
                    stock=10
                ),
                ProductDB(
                    name="鼠标",
                    description="无线鼠标",
                    price=99.99,
                    stock=50
                ),
                ProductDB(
                    name="键盘",
                    description="机械键盘",
                    price=299.99,
                    stock=30
                ),
            ]
            db.add_all(sample_products)
            db.commit()
    finally:
        db.close()


# ============ 8. 如何运行此示例 ============

if __name__ == "__main__":
    from utils import run_app
    
    # 使用 run_app 自动处理端口占用问题
    run_app(app, start_port=8000, open_browser=True)


# ============ 学习要点 ============

"""
✅ 学到的内容:

1. SQLAlchemy ORM 模型定义
   - 使用 declarative_base
   - 定义表和列
   - 添加约束和索引

2. 数据库配置
   - 创建引擎
   - 创建会话工厂
   - 配置连接参数

3. Pydantic Schema 与 ORM 模型的转换
   - from_attributes = True
   - model_validate() 方法

4. 数据库操作
   - 创建 (INSERT)
   - 读取 (SELECT)
   - 更新 (UPDATE)
   - 删除 (DELETE)

5. 事务管理
   - commit() 提交
   - rollback() 回滚
   - 会话生命周期

❓ 常见问题:

Q: 为什么需要两个模型 (ORM 和 Pydantic)?
A: ORM 模型用于数据库操作，Pydantic 模型用于 API 验证和序列化。

Q: 如何使用其他数据库?
A: 修改 DATABASE_URL，例如:
   - PostgreSQL: postgresql://user:password@localhost/dbname
   - MySQL: mysql://user:password@localhost/dbname

Q: 如何处理并发请求?
A: 使用异步数据库驱动，查看示例 3。

Q: 如何添加关系?
A: 使用 ForeignKey 和 relationship()。

🔗 相关文档:
- 支持的数据库: docs/usage/02-databases.md
- 数据流: docs/usage/03-data-flow.md
- 最佳实践: docs/usage/16-best-practices.md

📚 下一步:
- 运行此示例并测试所有端点
- 查看生成的 example.db 文件
- 查看 03_with_queries.py 学习查询功能
"""
