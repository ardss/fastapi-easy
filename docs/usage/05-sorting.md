# 排序功能

## 概述

fastapi-easy 支持灵活的排序功能，支持升序、降序和多字段排序。

---

## 启用排序功能

```python
from fastapi_easy import CRUDRouter

router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_sorters=True,
    sort_fields=["name", "price", "created_at"],  # 可排序的字段
    default_sort="-created_at",  # 默认排序字段
)
```

---

## 基本排序

### 升序排序

```bash
GET /items?sort=name
```

**SQL**: `ORDER BY name ASC`

按名称升序排列。

---

### 降序排序

```bash
GET /items?sort=-price
```

**SQL**: `ORDER BY price DESC`

按价格降序排列。

---

## 多字段排序

### 两个字段

```bash
GET /items?sort=category,name
```

**SQL**: `ORDER BY category ASC, name ASC`

先按分类升序，再按名称升序。

---

### 混合升降序

```bash
GET /items?sort=category,-price
```

**SQL**: `ORDER BY category ASC, price DESC`

先按分类升序，再按价格降序。

---

### 三个或更多字段

```bash
GET /items?sort=category,-price,name
```

**SQL**: `ORDER BY category ASC, price DESC, name ASC`

---

## 与其他功能组合

### 排序 + 过滤

```bash
GET /items?category=fruit&sort=-price
```

查询分类为 fruit 的商品，按价格降序排列。

---

### 排序 + 分页

```bash
GET /items?sort=name&skip=0&limit=10
```

按名称升序排列，分页显示。

---

### 排序 + 过滤 + 分页

```bash
GET /items?category=fruit&price__gt=5&sort=-created_at&skip=0&limit=10
```

查询分类为 fruit 且价格大于 5 的商品，按创建时间降序排列，分页显示。

---

## 完整示例

### 定义模型

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAsyncBackend
from pydantic import BaseModel
from datetime import datetime

class Item(BaseModel):
    id: int
    name: str
    price: float
    category: str
    created_at: datetime

app = FastAPI()

router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_sorters=True,
    sort_fields=["name", "price", "category", "created_at"],
    default_sort="-created_at",  # 默认按创建时间降序
)

app.include_router(router)
```

### API 查询示例

```bash
# 按名称升序
curl "http://localhost:8000/items?sort=name"

# 按价格降序
curl "http://localhost:8000/items?sort=-price"

# 按分类升序，再按价格降序
curl "http://localhost:8000/items?sort=category,-price"

# 按创建时间降序，再按名称升序
curl "http://localhost:8000/items?sort=-created_at,name"

# 排序 + 过滤：分类为 fruit，按价格降序
curl "http://localhost:8000/items?category=fruit&sort=-price"

# 排序 + 分页：按名称升序，每页 10 条
curl "http://localhost:8000/items?sort=name&skip=0&limit=10"

# 排序 + 过滤 + 分页
curl "http://localhost:8000/items?category=fruit&price__gt=5&sort=-price&skip=0&limit=10"
```

---

## 响应示例

### 查询请求

```bash
GET /items?sort=-price&skip=0&limit=5
```

### 响应

```json
{
    "data": [
        {
            "id": 3,
            "name": "apple pie",
            "price": 25.0,
            "category": "dessert",
            "created_at": "2024-01-03T10:00:00"
        },
        {
            "id": 1,
            "name": "apple",
            "price": 15.5,
            "category": "fruit",
            "created_at": "2024-01-01T10:00:00"
        },
        {
            "id": 2,
            "name": "banana",
            "price": 8.0,
            "category": "fruit",
            "created_at": "2024-01-02T10:00:00"
        }
    ],
    "total": 3,
    "page": 1,
    "pages": 1,
    "limit": 5,
    "skip": 0
}
```

---

## 高级用法

### 默认排序

```python
router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_sorters=True,
    sort_fields=["name", "price", "created_at"],
    default_sort="-created_at",  # 如果没有指定 sort 参数，使用此默认排序
)
```

当用户不指定排序参数时：

```bash
GET /items
```

等同于：

```bash
GET /items?sort=-created_at
```

---

### 排序字段限制

只能排序在 `sort_fields` 中指定的字段：

```python
router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_sorters=True,
    sort_fields=["name", "price"],  # 只能按这些字段排序
)
```

---

## 常见问题

### Q: 如何按降序排列？

**A**: 在字段名前加 `-` 符号

```bash
GET /items?sort=-price
```

---

### Q: 如何按多个字段排序？

**A**: 用逗号分隔字段名

```bash
GET /items?sort=category,-price,name
```

---

### Q: 如何设置默认排序？

**A**: 使用 `default_sort` 参数

```python
router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_sorters=True,
    sort_fields=["name", "price", "created_at"],
    default_sort="-created_at",
)
```

---

### Q: 可以排序哪些字段？

**A**: 只能排序在 `sort_fields` 中指定的字段

```python
router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_sorters=True,
    sort_fields=["name", "price", "category"],  # 只能排序这些字段
)
```

---

### Q: 如何禁用排序功能？

**A**: 设置 `enable_sorters=False`

```python
router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_sorters=False,  # 禁用排序
)
```

---

### Q: 排序和过滤可以一起使用吗？

**A**: 可以，它们是独立的功能

```bash
GET /items?category=fruit&price__gt=5&sort=-price
```

---

## 性能建议

### 1. 为排序字段添加数据库索引

```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)  # 添加索引
    price = Column(Float, index=True)  # 添加索引
    created_at = Column(DateTime, index=True)  # 添加索引
```

### 2. 限制排序字段数量

```python
# ✅ 好
sort_fields=["name", "price", "created_at"]

# ❌ 不好
sort_fields=["id", "name", "price", "category", "description", "created_at", ...]
```

### 3. 避免排序大文本字段

```python
# ❌ 不好
sort_fields=["name", "description", "content"]

# ✅ 好
sort_fields=["name", "created_at"]
```

---

## 下一步

- 学习[搜索和过滤](04-filters.md)
- 查看[完整示例](06-complete-example.md)
