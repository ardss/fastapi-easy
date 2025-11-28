"""
FastAPI-Easy 示例 1: 最简单的 CRUD API (使用 CRUDRouter 自动生成)

这个示例展示 fastapi-easy 的核心价值：
只需要 10 行代码就能自动生成完整的 CRUD API！

对比传统 FastAPI:
  传统 FastAPI: 需要手动写 GET、POST、PUT、DELETE 等 8+ 个端点
  fastapi-easy: 只需要定义 Schema + 创建 CRUDRouter

功能:
    - 自动生成 GET /items (获取所有)
    - 自动生成 GET /items/{id} (获取单个)
    - 自动生成 POST /items (创建)
    - 自动生成 PUT /items/{id} (更新)
    - 自动生成 DELETE /items/{id} (删除)
    - 自动生成 OpenAPI 文档

运行方式:
    python examples/01_hello_world.py

访问 API 文档:
    http://localhost:8001/docs

学习内容:
    - 如何定义 Pydantic Schema
    - 如何创建 CRUDRouter
    - 如何自动生成 CRUD API

预计学习时间: 5 分钟
代码行数: ~20 行 (不包括注释)
复杂度: ⭐ 极简
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi_easy import CRUDRouter

# ============ 1. 定义数据模型 (Schema) ============

class Item(BaseModel):
    """物品数据模型"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float

    class Config:
        json_schema_extra = {
            "example": {
                "name": "苹果",
                "description": "新鲜苹果",
                "price": 15.5
            }
        }


# ============ 2. 创建 FastAPI 应用 ============

app = FastAPI(
    title="FastAPI-Easy 示例 1",
    description="展示如何用 CRUDRouter 自动生成 CRUD API",
    version="1.0.0",
)


# ============ 3. 创建 CRUDRouter (自动生成所有 API) ============

# 这一行代码就自动生成了所有 CRUD 端点！
router = CRUDRouter(schema=Item)

# 注册路由到应用
app.include_router(router)


# ============ 4. 根路由 (可选) ============

@app.get("/", tags=["root"])
async def root():
    """欢迎页面"""
    return {
        "message": "欢迎使用 FastAPI-Easy",
        "docs": "/docs",
        "note": "所有 CRUD API 已自动生成！查看 /docs 查看完整 API 列表",
        "auto_generated_endpoints": [
            "GET /items - 获取所有物品",
            "GET /items/{id} - 获取单个物品",
            "POST /items - 创建物品",
            "PUT /items/{id} - 更新物品",
            "DELETE /items/{id} - 删除物品",
        ]
    }


# ============ 5. 如何运行此示例 ============

if __name__ == "__main__":
    from utils import run_app
    
    # 自动处理端口占用，自动打开浏览器
    run_app(app, start_port=8000, open_browser=True)


# ============ 学习要点 ============

"""
✅ 这个示例展示了什么:

1. 定义 Pydantic Schema
   - 只需要定义一个 BaseModel
   - 包含字段和验证规则

2. 创建 CRUDRouter
   - 只需一行代码: router = CRUDRouter(schema=Item)
   - 自动生成所有 CRUD 操作

3. 自动生成的 API:
   - GET /items - 获取所有物品 (支持分页)
   - GET /items/{id} - 获取单个物品
   - POST /items - 创建新物品
   - PUT /items/{id} - 更新物品
   - DELETE /items/{id} - 删除物品

4. 自动生成的文档
   - OpenAPI/Swagger 文档
   - 参数验证和示例
   - 错误响应说明

❓ 常见问题:

Q: 为什么没有看到数据持久化?
A: 这个示例使用内存存储 (没有数据库)。
   要使用真实数据库，查看示例 2: 02_with_database.py

Q: 如何添加更多字段?
A: 在 Item 类中添加新字段即可，API 会自动更新。

Q: 如何启用过滤、排序、分页?
A: 使用 CRUDConfig 配置，查看示例 3: 03_with_queries.py

Q: 如何添加软删除、权限、审计日志?
A: 使用 CRUDConfig 的高级选项，查看示例 4: 04_advanced_features.py

🔗 相关文档:
- 快速开始: docs/usage/01-quick-start.md
- CRUDRouter 配置: docs/usage/14-configuration.md
- 最佳实践: docs/usage/16-best-practices.md

📚 下一步:
1. 运行此示例: python examples/01_hello_world.py
2. 访问 http://localhost:8001/docs 查看自动生成的 API
3. 尝试创建、读取、更新、删除物品
4. 查看示例 2 学习如何与数据库集成
"""
