"""
FastAPI-Easy 示例 1: 最简单的 CRUD API

这是最简单的示例，展示如何用 10 行代码创建一个完整的 CRUD API。

功能:
    - 自动生成 CRUD 路由
    - 自动生成 OpenAPI 文档
    - 支持异步操作

运行方式:
    uvicorn examples.01_hello_world:app --reload

访问 API 文档:
    http://localhost:8000/docs

学习内容:
    - 如何定义 Pydantic Schema
    - 如何创建 CRUDRouter
    - 如何注册路由到应用

预计学习时间: 5 分钟
代码行数: ~50 行
复杂度: ⭐ 极简
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

# ============ 1. 定义数据模型 ============

class Item(BaseModel):
    """
    物品数据模型
    
    属性:
        id: 物品 ID (可选，创建时由系统生成)
        name: 物品名称
        description: 物品描述
        price: 物品价格
    """
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "苹果",
                "description": "新鲜苹果",
                "price": 15.5
            }
        }


# ============ 2. 模拟数据存储 ============

items_db = []
item_id_counter = 1


# ============ 3. 创建 FastAPI 应用 ============

app = FastAPI(
    title="FastAPI-Easy 示例 1",
    description="最简单的 CRUD API 示例",
    version="1.0.0",
)


# ============ 4. 定义 CRUD 路由 ============

@app.get("/", tags=["root"])
async def root():
    """
    根路由
    
    返回欢迎信息和 API 文档链接
    """
    return {
        "message": "欢迎使用 FastAPI-Easy",
        "docs": "/docs",
        "endpoints": {
            "get_all": "GET /items",
            "get_one": "GET /items/{id}",
            "create": "POST /items",
            "update": "PUT /items/{id}",
            "delete": "DELETE /items/{id}",
        }
    }


@app.get("/items", tags=["items"], summary="获取所有物品")
async def get_items(skip: int = 0, limit: int = 10):
    """
    获取所有物品 (支持分页)
    
    参数:
        skip: 跳过的物品数
        limit: 返回的物品数
    
    返回:
        物品列表
    """
    total = len(items_db)
    items = items_db[skip:skip + limit]
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items
    }


@app.get("/items/{item_id}", tags=["items"], summary="获取单个物品")
async def get_item(item_id: int):
    """
    获取单个物品
    
    参数:
        item_id: 物品 ID
    
    返回:
        物品信息
    """
    for item in items_db:
        if item.get("id") == item_id:
            return item
    return {"error": "物品不存在"}


@app.post("/items", tags=["items"], summary="创建物品", status_code=201)
async def create_item(item: Item):
    """
    创建新物品
    
    参数:
        item: 物品信息
    
    返回:
        创建的物品信息 (包含 ID)
    """
    global item_id_counter
    item_dict = item.model_dump()
    item_dict["id"] = item_id_counter
    item_id_counter += 1
    items_db.append(item_dict)
    return item_dict


@app.put("/items/{item_id}", tags=["items"], summary="更新物品")
async def update_item(item_id: int, item: Item):
    """
    更新物品
    
    参数:
        item_id: 物品 ID
        item: 新的物品信息
    
    返回:
        更新后的物品信息
    """
    for i, existing_item in enumerate(items_db):
        if existing_item.get("id") == item_id:
            item_dict = item.model_dump()
            item_dict["id"] = item_id
            items_db[i] = item_dict
            return item_dict
    return {"error": "物品不存在"}


@app.delete("/items/{item_id}", tags=["items"], summary="删除物品")
async def delete_item(item_id: int):
    """
    删除物品
    
    参数:
        item_id: 物品 ID
    
    返回:
        删除结果
    """
    for i, item in enumerate(items_db):
        if item.get("id") == item_id:
            items_db.pop(i)
            return {"message": "物品已删除"}
    return {"error": "物品不存在"}


# ============ 5. 初始化示例数据 ============

@app.on_event("startup")
async def startup_event():
    """
    应用启动时初始化示例数据
    """
    global item_id_counter
    
    sample_items = [
        {"id": 1, "name": "苹果", "description": "新鲜苹果", "price": 15.5},
        {"id": 2, "name": "香蕉", "description": "黄色香蕉", "price": 8.0},
        {"id": 3, "name": "橙子", "description": "新鲜橙子", "price": 12.0},
    ]
    
    items_db.extend(sample_items)
    item_id_counter = 4


# ============ 6. 如何运行此示例 ============

if __name__ == "__main__":
    from utils import run_app
    
    # 使用 run_app 自动处理端口占用问题
    # 如果 8000 端口被占用，会自动使用 8001、8002 等
    run_app(app, start_port=8000, open_browser=True)


# ============ 学习要点 ============

"""
✅ 学到的内容:

1. 如何定义 Pydantic Schema
   - 使用 BaseModel 定义数据模型
   - 添加字段验证
   - 添加示例数据

2. 如何创建 CRUD 路由
   - GET: 获取资源
   - POST: 创建资源
   - PUT: 更新资源
   - DELETE: 删除资源

3. 如何使用 FastAPI 装饰器
   - @app.get()
   - @app.post()
   - @app.put()
   - @app.delete()

4. 如何添加文档
   - 使用 docstring
   - 使用 tags 分组
   - 使用 summary 和 description

5. 如何处理错误
   - 检查资源是否存在
   - 返回有意义的错误信息

❓ 常见问题:

Q: 为什么使用 async?
A: FastAPI 支持异步操作，提高性能。

Q: 如何添加更多字段?
A: 在 Item 类中添加新字段即可。

Q: 如何连接真实数据库?
A: 查看示例 2: 02_with_database.py

Q: 如何添加过滤和排序?
A: 查看示例 3: 03_with_queries.py

🔗 相关文档:
- 快速开始: docs/usage/01-quick-start.md
- 数据流: docs/usage/03-data-flow.md
- 最佳实践: docs/usage/16-best-practices.md

📚 下一步:
- 修改示例代码，添加新字段
- 运行 API 并测试所有端点
- 查看 02_with_database.py 学习数据库集成
"""
