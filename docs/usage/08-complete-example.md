# 完整实际示例

本文档提供一个完整的、可运行的 FastAPI-Easy 使用示例，展示如何构建一个真实的应用。

## 项目结构

```
my_app/
├── main.py              # FastAPI 应用入口
├── models.py            # SQLAlchemy 模型
├── schemas.py           # Pydantic 模式
├── database.py          # 数据库配置
└── requirements.txt     # 依赖列表
```

## 1. 安装依赖

```bash
pip install fastapi uvicorn sqlalchemy fastapi-easy
```

## 2. 数据库配置

**database.py**：

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_session():
    async with async_session_maker() as session:
        yield session
```

## 3. 定义模型

**models.py**：

```python
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500))
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

## 4. 定义模式

**schemas.py**：

```python
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    price: float = Field(..., gt=0)
    stock: int = Field(default=0, ge=0)

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    stock: int | None = None

class Product(ProductBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
```

## 5. 创建应用

**main.py**：

```python
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_easy import CRUDRouter
from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter
from fastapi_easy.core.config import CRUDConfig

from database import engine, async_session_maker, Base, get_session
from models import Product
from schemas import Product as ProductSchema, ProductCreate, ProductUpdate

# 初始化数据库
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 创建 FastAPI 应用
app = FastAPI(title="Product API", version="1.0.0")

# 初始化数据库
@app.on_event("startup")
async def startup():
    await init_db()

# 配置 CRUD 路由
config = CRUDConfig(
    enable_filters=True,
    enable_sorters=True,
    enable_pagination=True,
    default_limit=10,
    max_limit=100,
)

# 创建 SQLAlchemy 适配器
adapter = SQLAlchemyAdapter(
    model=Product,
    session_factory=async_session_maker,
    pk_field="id",
)

# 创建 CRUD 路由
router = CRUDRouter(
    schema=ProductSchema,
    create_schema=ProductCreate,
    update_schema=ProductUpdate,
    adapter=adapter,
    config=config,
    prefix="/api/products",
    tags=["products"],
)

# 注册路由
app.include_router(router)

# 自定义端点示例
@app.get("/api/products/by-price/{min_price}")
async def get_products_by_price(min_price: float, session: AsyncSession = Depends(get_session)):
    """获取价格大于指定值的产品"""
    from sqlalchemy import select
    
    query = select(Product).where(Product.price > min_price)
    result = await session.execute(query)
    return result.scalars().all()

@app.post("/api/products/bulk")
async def create_bulk_products(products: list[ProductCreate], session: AsyncSession = Depends(get_session)):
    """批量创建产品"""
    db_products = [Product(**product.model_dump()) for product in products]
    session.add_all(db_products)
    await session.commit()
    
    for product in db_products:
        await session.refresh(product)
    
    return db_products

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 6. 运行应用

```bash
python main.py
```

应用将在 `http://localhost:8000` 启动。

## 7. API 端点

### 自动生成的 CRUD 端点

- `GET /api/products` - 获取所有产品（支持分页、过滤、排序）
- `GET /api/products/{id}` - 获取单个产品
- `POST /api/products` - 创建产品
- `PUT /api/products/{id}` - 更新产品
- `DELETE /api/products/{id}` - 删除产品
- `DELETE /api/products` - 删除所有产品

### 查询参数示例

```bash
# 分页
GET /api/products?skip=0&limit=10

# 过滤
GET /api/products?price__gt=100&stock__gte=5

# 排序
GET /api/products?sort=-price,name

# 组合
GET /api/products?price__gt=50&sort=-created_at&skip=0&limit=20
```

## 8. 使用 Tortoise ORM

如果使用 Tortoise ORM，只需修改适配器部分：

```python
from fastapi_easy.backends.tortoise import TortoiseAdapter

# 初始化 Tortoise
from tortoise import Tortoise

async def init_tortoise():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["models"]},
    )
    await Tortoise.generate_schemas()

# 创建适配器
adapter = TortoiseAdapter(
    model=Product,
    pk_field="id",
)

# 其余代码相同
```

## 9. 添加钩子

```python
from fastapi_easy.core.hooks import HookRegistry, ExecutionContext

hooks = HookRegistry()

# 注册钩子
@hooks.register("before_create")
async def before_create(context: ExecutionContext):
    """在创建前验证数据"""
    print(f"Creating product: {context.data}")

@hooks.register("after_create")
async def after_create(context: ExecutionContext):
    """在创建后记录日志"""
    print(f"Product created: {context.result}")

# 在路由中使用钩子
router = CRUDRouter(
    schema=ProductSchema,
    create_schema=ProductCreate,
    update_schema=ProductUpdate,
    adapter=adapter,
    config=config,
    hooks=hooks,
    prefix="/api/products",
    tags=["products"],
)
```

## 10. 错误处理

FastAPI-Easy 自动处理常见错误：

```python
# 404 错误 - 资源不存在
GET /api/products/999

# 422 错误 - 验证失败
POST /api/products
{
    "name": "",  # 空字符串不符合 min_length=1
    "price": -10  # 负数不符合 gt=0
}

# 409 错误 - 冲突（唯一约束）
# 如果添加了唯一约束，重复数据会返回 409
```

## 11. 完整工作流

```bash
# 1. 创建产品
curl -X POST http://localhost:8000/api/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Laptop",
    "description": "High-performance laptop",
    "price": 999.99,
    "stock": 10
  }'

# 2. 获取所有产品
curl http://localhost:8000/api/products

# 3. 过滤产品
curl "http://localhost:8000/api/products?price__gt=500"

# 4. 排序产品
curl "http://localhost:8000/api/products?sort=-price"

# 5. 获取单个产品
curl http://localhost:8000/api/products/1

# 6. 更新产品
curl -X PUT http://localhost:8000/api/products/1 \
  -H "Content-Type: application/json" \
  -d '{
    "price": 899.99,
    "stock": 5
  }'

# 7. 删除产品
curl -X DELETE http://localhost:8000/api/products/1
```

## 12. 最佳实践

1. **使用异步操作** - 充分利用 FastAPI 的异步能力
2. **添加验证** - 在 Pydantic 模式中使用 Field 验证
3. **使用钩子** - 在关键操作前后执行自定义逻辑
4. **错误处理** - 利用自动错误处理机制
5. **文档化** - 使用 FastAPI 的自动文档生成
6. **测试** - 编写单元和集成测试
7. **性能** - 使用过滤和分页优化查询

## 总结

FastAPI-Easy 提供了一个强大而灵活的框架，用于快速构建 CRUD API。通过本示例，你可以：

- ✅ 快速生成 CRUD 端点
- ✅ 支持多种 ORM（SQLAlchemy、Tortoise）
- ✅ 自动处理错误和验证
- ✅ 添加自定义钩子和逻辑
- ✅ 实现高性能的异步操作

更多信息请参考 [架构文档](./07-architecture.md)。
