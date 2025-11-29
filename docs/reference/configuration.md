# 配置参考手册

本文档详细介绍了 `CRUDConfig` 类的所有可用配置项。

## 基础用法

配置可以通过 `CRUDRouter` 的 `config` 参数传递，或者直接作为关键字参数传递（部分支持，建议使用 `CRUDConfig` 对象）。

```python
from fastapi_easy import CRUDRouter, CRUDConfig

config = CRUDConfig(
    enable_filters=True,
    default_limit=20
)

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    config=config
)
```

---

## CRUDConfig 参数详解

### 功能开关 (Feature Toggles)

| 参数名 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `enable_filters` | `bool` | `True` | 是否启用搜索和过滤功能 |
| `enable_sorters` | `bool` | `True` | 是否启用排序功能 |
| `enable_pagination` | `bool` | `True` | 是否启用分页功能 |
| `enable_soft_delete` | `bool` | `False` | 是否启用软删除（逻辑删除） |
| `enable_audit` | `bool` | `False` | 是否启用审计日志（需配合 Adapter 支持） |
| `enable_bulk_operations` | `bool` | `False` | 是否启用批量操作 API |
| `enable_delete_all` | `bool` | `False` | 是否启用"删除所有" API (危险操作) |

### 过滤与排序 (Filtering & Sorting)

| 参数名 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `filter_fields` | `List[str]` | `None` | 允许过滤的字段列表。如果为 `None`，则不限制（不推荐）。 |
| `sort_fields` | `List[str]` | `None` | 允许排序的字段列表。如果为 `None`，则不限制。 |
| `default_sort` | `str` | `None` | 默认排序字段（如 `"-created_at"`）。 |

### 分页 (Pagination)

| 参数名 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `default_limit` | `int` | `10` | 默认每页显示的记录数。 |
| `max_limit` | `int` | `100` | 允许的最大每页记录数（防止恶意请求）。 |

### 软删除 (Soft Delete)

| 参数名 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `deleted_at_field` | `str` | `"deleted_at"` | 数据库中用于标记删除时间的字段名。 |

### 错误处理与日志 (Error Handling & Logging)

| 参数名 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `include_error_details` | `bool` | `True` | 是否在 API 错误响应中包含详细调试信息。 |
| `log_errors` | `bool` | `True` | 是否将错误记录到系统日志。 |

### 其他

| 参数名 | 类型 | 默认值 | 描述 |
| :--- | :--- | :--- | :--- |
| `metadata` | `Dict` | `{}` | 用于存储自定义元数据的字典，可在钩子中访问。 |

---

## 动态更新配置

你可以在运行时更新配置：

```python
router.update_config(default_limit=50, enable_delete_all=True)
```

或者获取当前配置：

```python
current_config = router.get_config()
print(current_config.default_limit)
```
