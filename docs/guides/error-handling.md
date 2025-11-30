# 错误处理

本指南介绍如何在 fastapi-easy 中进行错误处理。

---

## 内置错误类型

```python
from fastapi_easy.core.errors import (
    AppError,
    ValidationError,
    NotFoundError,
    ConflictError,
    PermissionDeniedError,
    InternalServerError,
)
```

---

## 使用错误

### 基础错误

```python
# 验证错误
raise ValidationError("Invalid input", details={"field": "name"})

# 未找到错误
raise NotFoundError("Item not found")

# 冲突错误
raise ConflictError("Item already exists")

# 权限错误
raise PermissionDeniedError("No permission")

# 服务器错误
raise InternalServerError("Database connection failed")
```

### 自定义错误

```python
from fastapi_easy.core.errors import AppError

class ItemNotFoundError(AppError):
    code = "ITEM_NOT_FOUND"
    message = "Item not found"
    status_code = 404
```

---

## 错误响应

```python
# 响应格式
{
    "success": false,
    "error": "Item not found",
    "code": "ITEM_NOT_FOUND",
    "details": {
        "item_id": 1
    }
}
```

---

## 错误处理中间件

```python
from fastapi_easy.middleware import ErrorHandlingMiddleware

middleware = ErrorHandlingMiddleware()

# 注册自定义错误处理器
async def handle_validation_error(error):
    logger.warning(f"Validation error: {error}")
    return error

middleware.register_handler(ValidationError, handle_validation_error)
```

---

## 最佳实践

1. ✅ 使用适当的错误类型
2. ✅ 提供详细的错误信息
3. ✅ 记录所有错误
4. ✅ 不暴露敏感信息

---

**下一步**: [软删除](soft-delete.md) →
