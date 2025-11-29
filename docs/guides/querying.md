# 查询指南：搜索、过滤与排序

## 概述

fastapi-easy 提供了强大的查询功能，允许客户端通过 URL 参数对数据进行搜索、过滤和排序。这些功能是自动生成的，无需编写额外的 SQL 或逻辑代码。

---

## 1. 过滤 (Filtering)

### 启用过滤

在 `CRUDRouter` 中设置 `enable_filters=True` 并指定 `filter_fields`：

```python
from fastapi_easy import CRUDRouter

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    enable_filters=True,
    filter_fields=["name", "price", "category"],  # 指定允许过滤的字段
)
```

### 支持的操作符

fastapi-easy 使用 `字段名__操作符` 的格式（双下划线）来指定过滤条件。默认情况下（不加操作符）为精确匹配。

| 操作符 | 描述 | URL 示例 | SQL 等价 |
| :--- | :--- | :--- | :--- |
| (无) | 精确匹配 | `?name=apple` | `name = 'apple'` |
| `ne` | 不等于 | `?name__ne=apple` | `name != 'apple'` |
| `gt` | 大于 | `?price__gt=10` | `price > 10` |
| `gte` | 大于等于 | `?price__gte=10` | `price >= 10` |
| `lt` | 小于 | `?price__lt=50` | `price < 50` |
| `lte` | 小于等于 | `?price__lte=50` | `price <= 50` |
| `in` | 包含于 | `?category__in=fruit,meat` | `category IN ('fruit', 'meat')` |
| `like` | 模糊匹配 | `?name__like=%app%` | `name LIKE '%app%'` |
| `ilike` | 不区分大小写模糊 | `?name__ilike=%app%` | `name ILIKE '%app%'` (PostgreSQL) |

### 组合过滤

多个参数之间是 **AND** 关系：

```bash
GET /items?name__like=%apple%&price__gt=5&category=fruit
```

**SQL**:
```sql
WHERE name LIKE '%apple%' 
  AND price > 5 
  AND category = 'fruit'
```

---

## 2. 排序 (Sorting)

### 启用排序

在 `CRUDRouter` 中设置 `enable_sorters=True` 并指定 `sort_fields`：

```python
router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    enable_sorters=True,
    sort_fields=["name", "price", "created_at"],
    default_sort="-created_at",  # 可选：默认排序
)
```

### 使用方法

使用 `sort` 参数指定排序字段。

- **升序**：直接使用字段名，如 `sort=price`
- **降序**：在字段名前加负号 `-`，如 `sort=-price`
- **多字段**：用逗号分隔，如 `sort=category,-price`

### 示例

| 描述 | URL 示例 | SQL 等价 |
| :--- | :--- | :--- |
| 按价格升序 | `?sort=price` | `ORDER BY price ASC` |
| 按价格降序 | `?sort=-price` | `ORDER BY price DESC` |
| 先分类升序，后价格降序 | `?sort=category,-price` | `ORDER BY category ASC, price DESC` |

---

## 3. 组合使用 (Filtering + Sorting + Pagination)

过滤、排序和分页可以完美结合使用。

```bash
GET /items?category=fruit&price__gt=10&sort=-price&skip=0&limit=20
```

**逻辑顺序**：
1.  **Filter**: 筛选 `category='fruit'` 且 `price > 10` 的记录
2.  **Sort**: 按 `price` 降序排列
3.  **Paginate**: 跳过前 0 条，取 20 条

---

## 4. 常见问题 (FAQ)

**Q: 如何查询空值 (NULL)？**
A: 目前暂不支持直接查询 NULL，建议在设计数据库时设置默认值。或者使用自定义过滤器（高级功能）。

**Q: `like` 和 `ilike` 的区别？**
A: `like` 通常区分大小写（取决于数据库排序规则），`ilike` 强制不区分大小写（主要用于 PostgreSQL）。

**Q: 为什么我的排序不起作用？**
A: 检查字段是否在 `sort_fields` 列表中。出于安全考虑，未列出的字段不允许排序。

---

## 5. 性能建议

1.  **索引**：务必为 `filter_fields` 和 `sort_fields` 中的高频字段添加数据库索引。
2.  **限制字段**：不要将所有字段都暴露给过滤和排序，只暴露业务需要的字段。
3.  **分页限制**：始终设置合理的 `max_limit` 防止单次查询大量数据。

```python
# 推荐配置
router = CRUDRouter(
    # ...
    pagination_config=PaginationConfig(default_limit=20, max_limit=100)
)
```
