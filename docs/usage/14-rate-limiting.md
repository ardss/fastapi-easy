# 速率限制

速率限制保护 API 免受滥用。本指南介绍如何使用速率限制功能。

---

## 启用速率限制

```python
from fastapi_easy.core.rate_limit import RateLimitConfig

config = RateLimitConfig(
    enabled=True,
    backend="memory",
    default_limit=100,
    default_window=60,
)

router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    rate_limit_config=config,
)
```

---

## 使用速率限制

```python
# 自动限制：每分钟 100 个请求
# GET /items
# 响应头：X-RateLimit-Limit: 100, X-RateLimit-Remaining: 99
```

---

## 最佳实践

1. ✅ 为不同端点设置不同的限制
2. ✅ 监控限制被触发的频率
3. ✅ 为 VIP 用户提高限制

---

**下一步**: [GraphQL 支持](15-graphql.md) →
