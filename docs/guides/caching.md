# 缓存系统 - 完整指南

**难度**: ⭐⭐ 初级  
**预计时间**: 15 分钟  
**前置知识**: [快速开始](../tutorial/01-quick-start.md)

---

## 概述

FastAPI-Easy 提供了多层缓存系统，可以显著提高应用性能。缓存系统支持内存缓存和可选的外部缓存（如 Redis）。

---

## 缓存架构

### 两层缓存设计

```
请求
  ↓
L1 缓存 (内存) ← 快速，本地
  ↓ (未命中)
L2 缓存 (Redis) ← 中等速度，共享
  ↓ (未命中)
数据库 ← 慢，真实数据源
```

### 缓存流程

1. **查询 L1 缓存** - 检查内存中的缓存
2. **查询 L2 缓存** - 如果 L1 未命中，检查 Redis
3. **查询数据库** - 如果都未命中，从数据库获取
4. **更新缓存** - 将结果存储到 L1 和 L2

---

## L1 缓存 (内存缓存)

### 启用 L1 缓存

```python
from fastapi_easy import CRUDRouter, CRUDConfig

config = CRUDConfig(
    enable_cache=True,  # 启用缓存
    cache_ttl=3600,     # 缓存过期时间 (秒)
    cache_max_size=1000, # 最大缓存项数
)

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    config=config,
)
```

### L1 缓存特点

- ✅ 极快 (内存访问)
- ✅ 无需配置
- ✅ 自动过期
- ❌ 不共享 (每个进程独立)
- ❌ 重启后丢失

### 缓存键格式

```
item:1              # 单个项目
items:all           # 所有项目
items:filter:name=apple  # 过滤结果
```

---

## L2 缓存 (Redis)

### 启用 L2 缓存

```python
import redis.asyncio as redis
from fastapi_easy import CRUDRouter, CRUDConfig

# 连接 Redis
redis_client = redis.from_url("redis://localhost:6379")

config = CRUDConfig(
    enable_cache=True,
    cache_ttl=3600,
    l2_cache=redis_client,  # 启用 L2 缓存
)

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    config=config,
)
```

### L2 缓存特点

- ✅ 中等速度
- ✅ 进程间共享
- ✅ 持久化
- ✅ 支持分布式
- ❌ 需要 Redis 服务器
- ❌ 网络延迟

### Redis 配置

```python
# 本地 Redis
redis_client = redis.from_url("redis://localhost:6379")

# 远程 Redis
redis_client = redis.from_url("redis://redis-server:6379")

# 带密码的 Redis
redis_client = redis.from_url("redis://:password@localhost:6379")

# Redis 集群
redis_client = redis.from_url("rediss://localhost:6379")  # SSL
```

---

## 缓存失效管理

### 自动失效

缓存在以下情况自动失效：

1. **TTL 过期** - 到达过期时间
2. **数据修改** - 创建、更新、删除操作
3. **手动清除** - 显式调用清除方法

### 手动清除缓存

```python
# 清除单个项目缓存
await cache.delete("item:1")

# 清除列表缓存
await cache.delete("items:all")

# 清除所有缓存
await cache.clear()

# 清除特定前缀的缓存
await cache.delete_pattern("items:*")
```

### 使用 Hook 管理缓存

```python
async def invalidate_cache_hook(context):
    """在修改时清除缓存"""
    # 清除列表缓存
    await cache.delete("items:all")
    
    # 清除单个项目缓存
    if context.result:
        await cache.delete(f"item:{context.result.id}")

# 注册 Hook
router.hooks.register("after_create", invalidate_cache_hook)
router.hooks.register("after_update", invalidate_cache_hook)
router.hooks.register("after_delete", invalidate_cache_hook)
```

---

## 缓存监控

### 获取缓存统计

```python
# 获取缓存统计信息
stats = await cache.get_stats()

print(f"缓存命中: {stats['hits']}")
print(f"缓存未命中: {stats['misses']}")
print(f"命中率: {stats['hit_rate']:.2%}")
print(f"缓存大小: {stats['size']}")
```

### 监控缓存性能

```python
import logging

logger = logging.getLogger(__name__)

async def monitor_cache_hook(context):
    """监控缓存性能"""
    stats = await cache.get_stats()
    
    if stats['hit_rate'] < 0.5:
        logger.warning(f"缓存命中率低: {stats['hit_rate']:.2%}")
    
    logger.info(f"缓存统计: {stats}")

router.hooks.register("after_get_all", monitor_cache_hook)
```

---

## 配置示例

### 基础配置

```python
from fastapi_easy import CRUDConfig

config = CRUDConfig(
    enable_cache=True,
    cache_ttl=3600,  # 1 小时
)
```

### 高性能配置

```python
import redis.asyncio as redis
from fastapi_easy import CRUDConfig

redis_client = redis.from_url("redis://localhost:6379")

config = CRUDConfig(
    enable_cache=True,
    cache_ttl=3600,
    cache_max_size=10000,  # 大缓存
    l2_cache=redis_client,  # 启用 L2
)
```

### 保守配置

```python
from fastapi_easy import CRUDConfig

config = CRUDConfig(
    enable_cache=True,
    cache_ttl=300,  # 5 分钟
    cache_max_size=100,  # 小缓存
)
```

---

## 性能优化建议

### 1. 选择合适的 TTL

```python
# ✅ 好的 - 根据数据变化频率选择
# 实时数据: 5-10 分钟
cache_ttl = 300

# 相对稳定的数据: 1 小时
cache_ttl = 3600

# 很少变化的数据: 24 小时
cache_ttl = 86400
```

### 2. 缓存热点数据

```python
# ✅ 好的 - 缓存常访问的数据
async def cache_popular_items_hook(context):
    """缓存热点数据"""
    if len(context.result) > 100:
        # 缓存前 10 个最受欢迎的项目
        popular = context.result[:10]
        await cache.set("items:popular", popular, ttl=3600)

router.hooks.register("after_get_all", cache_popular_items_hook)
```

### 3. 避免缓存大对象

```python
# ❌ 不好的 - 缓存太大的对象
async def bad_cache_hook(context):
    # 缓存整个数据库
    all_items = await db.query(Item).all()
    await cache.set("all_items", all_items)

# ✅ 好的 - 只缓存必要的数据
async def good_cache_hook(context):
    # 只缓存 ID 和名称
    items = [{"id": i.id, "name": i.name} for i in context.result]
    await cache.set("items:summary", items)
```

### 4. 使用缓存预热

```python
# ✅ 好的 - 应用启动时预热缓存
@app.on_event("startup")
async def warmup_cache():
    """预热缓存"""
    # 获取热点数据
    popular_items = await db.query(Item).limit(100).all()
    
    # 存储到缓存
    for item in popular_items:
        await cache.set(f"item:{item.id}", item, ttl=3600)
    
    logger.info("缓存预热完成")
```

---

## 常见问题

### Q: 缓存会导致数据不一致吗？

**A**: 不会。FastAPI-Easy 在修改数据时自动清除相关缓存。

### Q: 如何禁用缓存？

**A**: 设置 `enable_cache=False` 或不指定缓存配置。

### Q: L1 和 L2 缓存的区别？

**A**: 
- L1 (内存): 快速，本地，不共享
- L2 (Redis): 中等速度，共享，持久化

### Q: 缓存会占用多少内存？

**A**: 取决于 `cache_max_size` 和对象大小。默认 1000 个对象，每个对象 ~1KB，约 1MB。

### Q: 如何监控缓存性能？

**A**: 使用 `cache.get_stats()` 获取统计信息。

---

## 最佳实践

### 1. 根据数据特性选择 TTL

```python
# 用户数据: 较短 TTL
user_cache_ttl = 300  # 5 分钟

# 产品数据: 中等 TTL
product_cache_ttl = 3600  # 1 小时

# 配置数据: 长 TTL
config_cache_ttl = 86400  # 24 小时
```

### 2. 监控缓存命中率

```python
async def log_cache_stats_hook(context):
    """记录缓存统计"""
    stats = await cache.get_stats()
    logger.info(f"缓存命中率: {stats['hit_rate']:.2%}")

router.hooks.register("after_get_all", log_cache_stats_hook)
```

### 3. 处理缓存失败

```python
async def safe_cache_hook(context):
    """安全的缓存操作"""
    try:
        await cache.set(f"item:{context.result.id}", context.result)
    except Exception as e:
        logger.error(f"缓存操作失败: {e}")
        # 继续执行，不影响主流程

router.hooks.register("after_create", safe_cache_hook)
```

### 4. 使用缓存预热

```python
@app.on_event("startup")
async def warmup_cache():
    """应用启动时预热缓存"""
    # 预加载热点数据
    popular_items = await db.query(Item).order_by(Item.views.desc()).limit(100).all()
    for item in popular_items:
        await cache.set(f"item:{item.id}", item, ttl=3600)
```

---

## 总结

缓存系统提供了强大的性能优化能力：

- ✅ 两层缓存架构 (L1 内存 + L2 Redis)
- ✅ 自动失效管理
- ✅ 灵活的配置选项
- ✅ 性能监控
- ✅ Hook 集成

合理使用缓存可以显著提高应用性能，同时保证数据一致性。

