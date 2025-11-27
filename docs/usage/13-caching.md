# 缓存支持

缓存可以显著提高性能。本指南介绍如何使用缓存功能。

---

## 启用缓存

```python
from fastapi_easy.core.cache import CacheConfig

config = CacheConfig(
    enabled=True,
    backend="memory",
    ttl=3600,
    max_size=1000,
)

router = CRUDRouter(
    schema=ItemSchema,
    backend=backend,
    cache_config=config,
)
```

---

## 缓存操作

```python
from fastapi_easy.core.cache import CachedOperation

@CachedOperation(cache, ttl=3600)
async def get_popular_items():
    return await adapter.get_all(filters={"popular": True})
```

---

## 最佳实践

1. ✅ 缓存频繁访问的数据
2. ✅ 设置合理的 TTL
3. ✅ 监控缓存命中率
4. ✅ 定期清理过期数据

---

**下一步**: [速率限制](14-rate-limiting.md) →
