"""
Simple example demonstrating FastAPI-Easy after fixes

This example shows how to use the fixed CRUDRouter to automatically
generate CRUD API endpoints.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from fastapi_easy import CRUDRouter
from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter


# 1. Define SQLAlchemy model
Base = declarative_base()


class ProductModel(Base):
    """Product database model"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String(500), nullable=True)
    stock = Column(Integer, default=0)


# 2. Define Pydantic schema
class ProductSchema(BaseModel):
    """Product API schema"""
    id: int
    name: str
    price: float
    description: str | None = None
    stock: int = 0
    
    class Config:
        from_attributes = True


# 3. Setup database
DATABASE_URL = "sqlite+aiosqlite:///./example.db"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# 4. Create FastAPI app
app = FastAPI(
    title="FastAPI-Easy Example",
    description="Demonstration of automatic CRUD API generation",
    version="1.0.0"
)


# 5. Create CRUD router (automatically generates 6 endpoints!)
adapter = SQLAlchemyAdapter(
    model=ProductModel,
    session_factory=async_session_factory
)

product_router = CRUDRouter(
    schema=ProductSchema,
    adapter=adapter,
    prefix="/products",
    tags=["Products"]
)


# 6. Include router in app
app.include_router(product_router)


# 7. Add startup event
@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()


# 8. Add root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to FastAPI-Easy Example!",
        "docs": "/docs",
        "endpoints": {
            "GET /products/": "Get all products (with pagination)",
            "GET /products/{id}": "Get product by ID",
            "POST /products/": "Create new product",
            "PUT /products/{id}": "Update product",
            "DELETE /products/{id}": "Delete product",
            "DELETE /products/": "Delete all products"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting FastAPI-Easy Example Server...")
    print("📚 API Documentation: http://localhost:8001/docs")
    print("🔍 OpenAPI Schema: http://localhost:8001/openapi.json")
    print("\n✨ Automatically generated endpoints:")
    print("   GET    /products/        - Get all products")
    print("   GET    /products/{id}    - Get product by ID")
    print("   POST   /products/        - Create product")
    print("   PUT    /products/{id}    - Update product")
    print("   DELETE /products/{id}    - Delete product")
    print("   DELETE /products/        - Delete all products")
    print("\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
