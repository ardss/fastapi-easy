"""
FastAPI-Easy 示例 3: 启用查询功能 (过滤、排序、分页)

这个示例展示如何通过配置启用高级查询功能。

对比传统 FastAPI:
  传统 FastAPI: 手动实现过滤、排序、分页 = 200+ 行
  fastapi-easy: 配置 CRUDConfig 启用 = 40 行

功能:
    - 过滤 (Filtering) - enable_filters
    - 排序 (Sorting) - enable_sorters
    - 分页 (Pagination) - enable_pagination

运行方式:
    python examples/03_with_queries.py

访问 API 文档:
    http://localhost:8001/docs

学习内容:
    - 如何启用过滤功能
    - 如何启用排序功能
    - 如何启用分页功能
    - 如何配置可过滤/可排序字段

预计学习时间: 10 分钟
代码行数: ~40 行 (不包括注释)
复杂度: ⭐⭐⭐ 中等

API 使用示例:
    GET /products?skip=0&limit=10 - 分页
    GET /products?name__like=notebook - 过滤
    GET /products?sort=-price - 排序
    GET /products?name__like=notebook&sort=-price&skip=0&limit=10 - 组合查询
"""

from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel
from typing import Optional
from fastapi_easy import CRUDRouter, SQLAlchemyAdapter, CRUDConfig

# ============ 1. 数据库配置 ============

DATABASE_URL = "sqlite:///./example_queries.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============ 2. ORM 模型 ============

class ProductDB(Base):
    """商品数据库模型"""
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    price = Column(Float, index=True)
    stock = Column(Integer, default=0)
    category = Column(String, index=True)


# ============ 3. Pydantic Schema ============

class Product(BaseModel):
    """商品 API Schema"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    category: str

    class Config:
        from_attributes = True


# ============ 4. 创建应用 ============

app = FastAPI(
    title="FastAPI-Easy 示例 3",
    description="启用查询功能 - 过滤、排序、分页",
    version="1.0.0",
)

# 创建数据库表
Base.metadata.create_all(bind=engine)


# ============ 5. 创建配置 (启用查询功能!) ============

config = CRUDConfig(
    enable_filters=True,          # 启用过滤
    enable_sorters=True,          # 启用排序
    enable_pagination=True,       # 启用分页
    filter_fields=["name", "price", "category"],  # 可过滤字段
    sort_fields=["name", "price", "category"],    # 可排序字段
    default_limit=10,             # 默认分页大小
    max_limit=100,                # 最大分页大小
)


# ============ 6. 创建适配器 ============

adapter = SQLAlchemyAdapter(model=ProductDB, session_factory=SessionLocal)


# ============ 7. 创建 CRUDRouter (自动启用查询功能!) ============

# 只需传入 config，所有查询功能自动启用！
router = CRUDRouter(schema=Product, adapter=adapter, config=config)

# 注册路由
app.include_router(router)


# ============ 8. 根路由 (可选) ============

@app.get("/", tags=["root"])
async def root():
    """欢迎页面"""
    return {
        "message": "欢迎使用 FastAPI-Easy 示例 3",
        "docs": "/docs",
        "note": "所有查询功能已自动启用！",
        "features": [
            "过滤 (Filtering)",
            "排序 (Sorting)",
            "分页 (Pagination)",
        ],
        "query_examples": [
            "GET /products?skip=0&limit=10 - 分页",
            "GET /products?name__like=notebook - 过滤",
            "GET /products?sort=-price - 排序 (降序)",
            "GET /products?name__like=notebook&sort=-price&skip=0&limit=10 - 组合查询",
        ]
    }


# ============ 9. 如何运行此示例 ============

if __name__ == "__main__":
    from utils import run_app
    
    # 自动处理端口占用，自动打开浏览器
    run_app(app, start_port=8000, open_browser=True)


# ============ 学习要点 ============

"""
✅ 这个示例展示了什么:

1. 定义 CRUDConfig
   - enable_filters=True: 启用过滤功能
   - enable_sorters=True: 启用排序功能
   - enable_pagination=True: 启用分页功能
   - filter_fields: 指定哪些字段可以过滤
   - sort_fields: 指定哪些字段可以排序

2. 创建 CRUDRouter 并传入 config
   - 只需一行代码: router = CRUDRouter(..., config=config)
   - 所有查询功能自动启用！

3. 自动生成的查询能力:
   - GET /products?skip=0&limit=10 - 分页
   - GET /products?name__like=notebook - 过滤
   - GET /products?sort=-price - 排序 (降序)
   - GET /products?price__gte=100&price__lte=1000 - 范围过滤
   - GET /products?name__like=notebook&sort=-price&skip=0&limit=10 - 组合查询

对比传统 FastAPI:
  传统 FastAPI: 200+ 行代码手动实现过滤、排序、分页
  fastapi-easy: 40 行代码配置启用！

节省 80% 的代码！

❓ 常见问题:

Q: 如何添加更多可过滤字段?
A: 修改 filter_fields 列表即可。

Q: 如何自定义排序逻辑?
A: 使用 Hook 系统，查看示例 4。

Q: 如何实现全文搜索?
A: 在 filter_fields 中添加搜索字段。

Q: 如何禁用某个功能?
A: 设置 enable_filters=False 等。

🔗 相关文档:
- 过滤: docs/usage/04-filters.md
- 排序: docs/usage/05-sorting.md
- 分页: docs/usage/06-pagination.md
- 配置: docs/usage/14-configuration.md

📚 下一步:
1. 运行此示例: python examples/03_with_queries.py
2. 访问 http://localhost:8001/docs 查看自动生成的查询参数
3. 尝试各种过滤、排序、分页组合
4. 查看示例 4 学习高级功能 (软删除、审计、Hook)
"""
