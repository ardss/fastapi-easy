# 搜索和过滤

## 概述

fastapi-easy 支持灵活的搜索和过滤功能，无需手写任何过滤逻辑。

---

## 启用过滤功能

```python
from fastapi_easy import CRUDRouter

router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_filters=True,
    filter_fields=["name", "price", "category"],  # 可过滤的字段
)
```

---

## 支持的操作符

### 1. 精确匹配（默认）

```bash
GET /items?name=apple
```

**SQL**: `WHERE name = 'apple'`

---

### 2. 不等于 (ne)

```bash
GET /items?name__ne=apple
```

**SQL**: `WHERE name != 'apple'`

---

### 3. 大于 (gt)

```bash
GET /items?price__gt=10
```

**SQL**: `WHERE price > 10`

---

### 4. 大于等于 (gte)

```bash
GET /items?price__gte=10
```

**SQL**: `WHERE price >= 10`

---

### 5. 小于 (lt)

```bash
GET /items?price__lt=50
```

**SQL**: `WHERE price < 50`

---

### 6. 小于等于 (lte)

```bash
GET /items?price__lte=50
```

**SQL**: `WHERE price <= 50`

---

### 7. 包含 (in)

```bash
GET /items?category__in=fruit,vegetable,meat
```

**SQL**: `WHERE category IN ('fruit', 'vegetable', 'meat')`

---

### 8. 模糊查询 (like)

```bash
GET /items?name__like=%apple%
```

**SQL**: `WHERE name LIKE '%apple%'`

---

### 9. 不区分大小写模糊查询 (ilike)

```bash
GET /items?name__ilike=%apple%
```

**SQL**: `WHERE name ILIKE '%apple%'` (PostgreSQL)

---

## 组合过滤

### 多条件 AND

```bash
GET /items?name=apple&price__gt=10&category=fruit
```

**SQL**: 
```sql
WHERE name = 'apple' 
  AND price > 10 
  AND category = 'fruit'
```

---

### 范围查询

```bash
GET /items?price__gte=10&price__lte=50
```

**SQL**: 
```sql
WHERE price >= 10 
  AND price <= 50
```

---

### 模糊查询 + 范围

```bash
GET /items?name__like=%apple%&price__gt=5
```

**SQL**: 
```sql
WHERE name LIKE '%apple%' 
  AND price > 5
```

---

## 完整示例

### 定义模型

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAsyncBackend
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float
    category: str
    stock: int

app = FastAPI()

router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_filters=True,
    filter_fields=["name", "price", "category", "stock"],
)

app.include_router(router)
```

### API 查询示例

```bash
# 查询名称为 apple 的商品
curl "http://localhost:8000/items?name=apple"

# 查询价格大于 10 的商品
curl "http://localhost:8000/items?price__gt=10"

# 查询价格在 10-50 之间的商品
curl "http://localhost:8000/items?price__gte=10&price__lte=50"

# 查询名称包含 apple 的商品
curl "http://localhost:8000/items?name__like=%apple%"

# 查询分类为 fruit 或 vegetable 的商品
curl "http://localhost:8000/items?category__in=fruit,vegetable"

# 组合查询：名称包含 apple 且价格大于 5 的商品
curl "http://localhost:8000/items?name__like=%apple%&price__gt=5"

# 组合查询：分类为 fruit 且库存大于 0 的商品
curl "http://localhost:8000/items?category=fruit&stock__gt=0"
```

---

## 响应示例

### 查询请求

```bash
GET /items?name=apple&price__gt=10
```

### 响应

```json
{
    "data": [
        {
            "id": 1,
            "name": "apple",
            "price": 15.5,
            "category": "fruit",
            "stock": 100
        },
        {
            "id": 3,
            "name": "apple pie",
            "price": 25.0,
            "category": "dessert",
            "stock": 50
        }
    ],
    "total": 2,
    "page": 1,
    "pages": 1,
    "limit": 10,
    "skip": 0
}
```

---

## 高级用法

### 与排序组合

```bash
GET /items?category=fruit&sort=-price&skip=0&limit=10
```

查询分类为 fruit 的商品，按价格降序排列，分页显示。

---

### 与分页组合

```bash
GET /items?price__gt=10&skip=0&limit=20
```

查询价格大于 10 的商品，每页显示 20 条。

---

### 与排序和分页组合

```bash
GET /items?category=fruit&price__gte=5&price__lte=50&sort=name&skip=0&limit=10
```

查询分类为 fruit 且价格在 5-50 之间的商品，按名称升序排列，分页显示。

---

## 常见问题

### Q: 如何查询空值？

**A**: 使用 `__eq=null` 或 `__ne=null`

```bash
GET /items?description__eq=null
```

---

### Q: 如何进行不区分大小写的查询？

**A**: 使用 `__ilike` 操作符（仅 PostgreSQL 支持）

```bash
GET /items?name__ilike=%apple%
```

---

### Q: 如何查询多个值？

**A**: 使用 `__in` 操作符

```bash
GET /items?category__in=fruit,vegetable,meat
```

---

### Q: 可以过滤哪些字段？

**A**: 只能过滤在 `filter_fields` 中指定的字段

```python
router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_filters=True,
    filter_fields=["name", "price", "category"],  # 只能过滤这些字段
)
```

---

### Q: 如何禁用过滤功能？

**A**: 设置 `enable_filters=False`

```python
router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_filters=False,  # 禁用过滤
)
```

---

## 性能建议

### 1. 只暴露必要的字段

```python
# ✅ 好
filter_fields=["name", "price", "category"]

# ❌ 不好
filter_fields=["id", "name", "price", "category", "description", "created_at", ...]
```

### 2. 为过滤字段添加数据库索引

```python
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)  # 添加索引
    price = Column(Float, index=True)  # 添加索引
    category = Column(String, index=True)  # 添加索引
```

### 3. 限制分页大小

```python
router = CRUDRouter(
    schema=Item,
    backend=backend,
    enable_pagination=True,
    pagination_config=PaginationConfig(
        default_limit=10,
        max_limit=100,  # 限制最大分页大小
    ),
)
```

---

## 下一步

- 学习[排序功能](05-sorting.md)
- 查看[完整示例](06-complete-example.md)
