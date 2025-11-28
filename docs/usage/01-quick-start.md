# 快速开始

**预计时间**: 5 分钟  
**难度**: ⭐ 极简  
**目标**: 运行第一个完整的 CRUD API

---

## 1. 安装

```bash
pip install fastapi-easy fastapi uvicorn
```

---

## 2. 最简单的例子 (内存存储)

创建文件 `main.py`:

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from pydantic import BaseModel
from typing import Optional

# 定义数据模型
class Item(BaseModel):
    id: Optional[int] = None
    name: str
    price: float

# 创建应用
app = FastAPI(title="FastAPI-Easy 快速开始")

# 一行代码生成完整的 CRUD API!
router = CRUDRouter(schema=Item)
app.include_router(router)

# 根路由
@app.get("/")
async def root():
    return {
        "message": "欢迎使用 FastAPI-Easy",
        "docs": "/docs",
        "api_endpoints": [
            "GET /items - 获取所有项目",
            "GET /items/{id} - 获取单个项目",
            "POST /items - 创建项目",
            "PUT /items/{id} - 更新项目",
            "DELETE /items/{id} - 删除项目",
        ]
    }
```

---

## 3. 运行

```bash
uvicorn main:app --reload
```

输出:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

---

## 4. 测试 API

### 方式 1: 使用 Swagger UI (推荐)

访问 http://localhost:8000/docs

你会看到所有自动生成的 API 端点，可以直接在浏览器中测试。

### 方式 2: 使用 curl

```bash
# 创建项目
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "苹果", "price": 15.5}'

# 获取所有项目
curl http://localhost:8000/items

# 获取单个项目
curl http://localhost:8000/items/1

# 更新项目
curl -X PUT http://localhost:8000/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "苹果 (更新)", "price": 18.0}'

# 删除项目
curl -X DELETE http://localhost:8000/items/1
```

### 方式 3: 使用 Python requests

```python
import requests

# 创建项目
response = requests.post("http://localhost:8000/items", json={
    "name": "苹果",
    "price": 15.5
})
print(response.json())

# 获取所有项目
response = requests.get("http://localhost:8000/items")
print(response.json())
```

---

## 5. 自动生成的 API

fastapi-easy 自动为你生成以下 API 端点:

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/items` | 获取所有项目 (支持分页) |
| GET | `/items/{id}` | 获取单个项目 |
| POST | `/items` | 创建新项目 |
| PUT | `/items/{id}` | 更新项目 |
| DELETE | `/items/{id}` | 删除项目 |

---

## 6. 代码量对比

### 传统 FastAPI (手动实现)

```python
# 需要手动写 8 个端点函数
# 每个函数都需要处理：
# - 参数验证
# - 数据库操作
# - 错误处理
# - 响应序列化
# 总计: 240-290 行代码

@app.get("/items")
async def get_items(skip: int = 0, limit: int = 10):
    # ... 实现代码 ...
    pass

@app.post("/items")
async def create_item(item: Item):
    # ... 实现代码 ...
    pass

# ... 更多端点 ...
```

### fastapi-easy (自动生成)

```python
# 只需 3 行代码!
router = CRUDRouter(schema=Item)
app.include_router(router)
# 完成！所有 API 自动生成
```

**对比**:

| 方式 | 代码行数 | 开发时间 |
|------|---------|---------|
| 手写 CRUD | 240-290 行 | 1-2 小时 |
| fastapi-easy | 3 行 | 5 分钟 |
| **节约** | **98%** | **95%** |

---

## 7. 下一步

现在你已经掌握了基础，可以继续学习:

### 初级 (推荐顺序)

1. **[与数据库集成](02-databases.md)** - 学习如何连接真实数据库
   - 查看示例: `examples/02_with_database.py`

2. **[启用查询功能](04-filters.md)** - 学习过滤、排序、分页
   - 查看示例: `examples/03_with_queries.py`

### 中级

3. **[高级功能](10-soft-delete.md)** - 学习软删除、审计日志
   - 查看示例: `examples/04_advanced_features.py`

### 高级

4. **[架构设计](07-architecture.md)** - 深入理解内部架构
5. **[完整项目](06-complete-example.md)** - 查看完整的电商 API
   - 查看示例: `examples/05_complete_ecommerce.py`

---

## 8. 常见问题

**Q: 数据会被持久化吗?**  
A: 不会。这个示例使用内存存储，重启后数据会丢失。要持久化数据，需要连接数据库，详见[与数据库集成](02-databases.md)。

**Q: 如何添加更多字段?**  
A: 在 `Item` 模型中添加新字段即可，API 会自动更新。

**Q: 如何自定义 API 路径?**  
A: 使用 `prefix` 参数: `CRUDRouter(schema=Item, prefix="/products")`

**Q: 如何添加权限控制?**  
A: 查看[权限控制](12-permissions.md)文档。

---

## 9. 相关资源

- 📚 [完整文档](README.md)
- 💻 [示例代码](../../examples/)
- 🐛 [故障排除](17-troubleshooting.md)
- 🎓 [最佳实践](16-best-practices.md)
