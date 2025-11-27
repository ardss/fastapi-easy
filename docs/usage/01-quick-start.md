# 快速开始

## 安装

```bash
pip install fastapi-easy
```

## 最简单的例子

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float

app = FastAPI()

# 一行代码生成完整的 CRUD API
router = CRUDRouter(schema=Item)
app.include_router(router)
```

## 自动生成的 API

```
GET    /item              - 获取所有项目
GET    /item/{item_id}    - 获取单个项目
POST   /item              - 创建项目
PUT    /item/{item_id}    - 更新项目
DELETE /item/{item_id}    - 删除项目
DELETE /item              - 删除所有项目
```

## 运行

```bash
uvicorn main:app --reload
```

访问 http://localhost:8000/docs 查看 API 文档

---

## 代码量对比

| 方式 | 代码行数 |
|------|--------|
| 手写 CRUD | 240-290 行 |
| fastapi-easy | 10 行 |
| **节约** | **96.5%** |

---

## 下一步

- 了解[支持的数据库](02-databases.md)
- 学习[搜索和过滤](04-filters.md)
- 查看[完整示例](06-complete-example.md)
