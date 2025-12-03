# Hook 系统 - 高级指南

**难度**: ⭐⭐⭐ 中级  
**预计时间**: 20 分钟  
**前置知识**: [快速开始](../01-basics/quick-start.md)

---

## 概述

Hook 系统允许你在 CRUD 操作的关键点插入自定义逻辑。这是一个强大的扩展机制，无需修改核心代码即可添加功能。

---

## 10 个 Hook 事件

### 创建操作

#### 1. `before_create`
在创建项目之前触发。

**用途**: 验证、预处理数据、记录日志

```python
async def before_create_hook(context):
    print(f"Creating item with data: {context.data}")
    # 验证数据
    if context.data.get("price", 0) < 0:
        raise ValueError("Price cannot be negative")

router.hooks.register("before_create", before_create_hook)
```

#### 2. `after_create`
在创建项目之后触发。

**用途**: 发送通知、更新缓存、记录审计日志

```python
async def after_create_hook(context):
    print(f"Item created: {context.result}")
    # 发送邮件通知
    await send_email(f"New item created: {context.result.name}")

router.hooks.register("after_create", after_create_hook)
```

---

### 更新操作

#### 3. `before_update`
在更新项目之前触发。

**用途**: 验证更新、检查权限、记录原始值

```python
async def before_update_hook(context):
    item_id = context.metadata.get("id")
    print(f"Updating item {item_id}")
    # 检查权限
    if not await check_permission(context.request.user, "update"):
        raise PermissionError("No permission to update")

router.hooks.register("before_update", before_update_hook)
```

#### 4. `after_update`
在更新项目之后触发。

**用途**: 发送通知、更新相关数据、记录变更

```python
async def after_update_hook(context):
    print(f"Item updated: {context.result}")
    # 更新缓存
    await cache.invalidate(f"item:{context.result.id}")

router.hooks.register("after_update", after_update_hook)
```

---

### 删除操作

#### 5. `before_delete`
在删除项目之前触发。

**用途**: 验证删除、检查依赖、备份数据

```python
async def before_delete_hook(context):
    item_id = context.metadata.get("id")
    print(f"Deleting item {item_id}")
    # 检查是否有依赖
    if await has_dependencies(item_id):
        raise ValueError("Cannot delete item with dependencies")

router.hooks.register("before_delete", before_delete_hook)
```

#### 6. `after_delete`
在删除项目之后触发。

**用途**: 清理相关数据、发送通知、记录删除

```python
async def after_delete_hook(context):
    print(f"Item deleted: {context.result}")
    # 清理相关数据
    await cleanup_related_data(context.result.id)

router.hooks.register("after_delete", after_delete_hook)
```

---

### 查询操作

#### 7. `before_get_all`
在获取所有项目之前触发。

**用途**: 应用额外过滤、检查权限、记录查询

```python
async def before_get_all_hook(context):
    print(f"Getting all items with filters: {context.filters}")
    # 应用用户特定的过滤
    if context.request.user:
        context.filters["owner_id"] = context.request.user.id

router.hooks.register("before_get_all", before_get_all_hook)
```

#### 8. `after_get_all`
在获取所有项目之后触发。

**用途**: 后处理结果、记录查询统计、缓存结果

```python
async def after_get_all_hook(context):
    print(f"Retrieved {len(context.result)} items")
    # 缓存结果
    await cache.set(f"items:all", context.result, ttl=3600)

router.hooks.register("after_get_all", after_get_all_hook)
```

#### 9. `before_get_one`
在获取单个项目之前触发。

**用途**: 检查权限、应用缓存、记录访问

```python
async def before_get_one_hook(context):
    item_id = context.metadata.get("id")
    print(f"Getting item {item_id}")
    # 检查缓存
    cached = await cache.get(f"item:{item_id}")
    if cached:
        context.result = cached

router.hooks.register("before_get_one", before_get_one_hook)
```

#### 10. `after_get_one`
在获取单个项目之后触发。

**用途**: 缓存结果、记录访问、应用后处理

```python
async def after_get_one_hook(context):
    print(f"Retrieved item: {context.result}")
    # 缓存结果
    await cache.set(f"item:{context.result.id}", context.result, ttl=3600)

router.hooks.register("after_get_one", after_get_one_hook)
```

---

## Hook 执行顺序

```
请求到达
    ↓
before_* Hook (可修改请求)
    ↓
执行数据库操作
    ↓
after_* Hook (可修改响应)
    ↓
返回响应
```

---

## 错误处理和隔离

### 错误隔离

如果一个 Hook 失败，其他 Hook 不会受到影响：

```python
async def hook1(context):
    raise Exception("Hook 1 failed")

async def hook2(context):
    print("Hook 2 executed")  # 仍然会执行

router.hooks.register("before_create", hook1)
router.hooks.register("before_create", hook2)
```

### 错误处理

在 Hook 中处理错误：

```python
async def safe_hook(context):
    try:
        # 执行操作
        result = await some_operation()
    except Exception as e:
        logger.error(f"Hook error: {e}")
        # 不要重新抛出异常，除非必要
        return

router.hooks.register("after_create", safe_hook)
```

---

## 异步和同步支持

### 异步 Hook

```python
async def async_hook(context):
    await asyncio.sleep(1)
    print("Async hook executed")

router.hooks.register("before_create", async_hook)
```

### 同步 Hook

```python
def sync_hook(context):
    print("Sync hook executed")

router.hooks.register("before_create", sync_hook)
```

### 混合使用

```python
async def async_hook(context):
    await asyncio.sleep(1)

def sync_hook(context):
    print("Sync")

router.hooks.register("before_create", async_hook)
router.hooks.register("before_create", sync_hook)
```

---

## 实际应用示例

### 示例 1: 审计日志

```python
async def audit_log_hook(context):
    """记录所有操作到审计日志"""
    log_entry = {
        "timestamp": datetime.now(),
        "operation": context.metadata.get("operation"),
        "user_id": context.request.user.id if context.request.user else None,
        "data": context.data or context.result,
    }
    await db.audit_logs.insert_one(log_entry)

# 为所有操作注册
for event in ["before_create", "before_update", "before_delete"]:
    router.hooks.register(event, audit_log_hook)
```

### 示例 2: 数据验证

```python
async def validate_item_hook(context):
    """验证项目数据"""
    data = context.data
    
    # 验证必需字段
    if not data.get("name"):
        raise ValueError("Name is required")
    
    # 验证字段长度
    if len(data["name"]) > 100:
        raise ValueError("Name is too long")
    
    # 验证价格
    if data.get("price", 0) < 0:
        raise ValueError("Price cannot be negative")

router.hooks.register("before_create", validate_item_hook)
router.hooks.register("before_update", validate_item_hook)
```

### 示例 3: 缓存管理

```python
async def invalidate_cache_hook(context):
    """在修改时清除缓存"""
    # 清除列表缓存
    await cache.delete("items:all")
    
    # 清除单个项目缓存
    if context.result:
        await cache.delete(f"item:{context.result.id}")

router.hooks.register("after_create", invalidate_cache_hook)
router.hooks.register("after_update", invalidate_cache_hook)
router.hooks.register("after_delete", invalidate_cache_hook)
```

---

## 最佳实践

### 1. 保持 Hook 简洁

```python
# ✅ 好的
async def simple_hook(context):
    await log_operation(context)

# ❌ 不好的
async def complex_hook(context):
    # 太多逻辑
    result = await db.query(...)
    for item in result:
        await process(item)
    # ... 更多代码
```

### 2. 使用适当的事件

```python
# ✅ 好的 - 在 after_create 中发送通知
async def send_notification_hook(context):
    await send_email(context.result)

router.hooks.register("after_create", send_notification_hook)

# ❌ 不好的 - 在 before_create 中发送通知
async def send_notification_hook(context):
    await send_email(context.data)  # 还没有创建！

router.hooks.register("before_create", send_notification_hook)
```

### 3. 处理异常

```python
# ✅ 好的
async def safe_hook(context):
    try:
        await risky_operation()
    except Exception as e:
        logger.error(f"Hook error: {e}")

# ❌ 不好的
async def unsafe_hook(context):
    await risky_operation()  # 可能失败
```

### 4. 避免循环依赖

```python
# ❌ 不好的 - 可能导致循环
async def update_hook(context):
    # 在 update hook 中再次更新
    await router.update(context.result.id, {"updated": True})

router.hooks.register("after_update", update_hook)
```

---

## Hook 上下文

`ExecutionContext` 包含以下信息：

```python
@dataclass
class ExecutionContext:
    schema: Any              # Pydantic schema
    adapter: Any            # ORM adapter
    request: Any            # FastAPI request
    user: Any = None        # 当前用户
    filters: Dict = {}      # 过滤条件
    sorts: Dict = {}        # 排序条件
    pagination: Dict = {}   # 分页信息
    data: Any = None        # 请求数据
    result: Any = None      # 操作结果
    metadata: Dict = {}     # 额外元数据
```

---

## 总结

Hook 系统提供了强大的扩展能力：

- ✅ 10 个关键点的 Hook
- ✅ 异步和同步支持
- ✅ 错误隔离
- ✅ 灵活的上下文信息
- ✅ 实际应用示例

使用 Hook 系统可以轻松实现审计日志、数据验证、缓存管理等功能。

