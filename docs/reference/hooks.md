# Hook 系统

Hook 系统允许在 CRUD 操作的关键点插入自定义逻辑。

---

## 支持的 Hook 事件

FastAPI-Easy 支持 10 种 Hook 事件：

- **before_get_all** - 获取所有记录前
- **after_get_all** - 获取所有记录后
- **before_get_one** - 获取单个记录前
- **after_get_one** - 获取单个记录后
- **before_create** - 创建记录前
- **after_create** - 创建记录后
- **before_update** - 更新记录前
- **after_update** - 更新记录后
- **before_delete** - 删除记录前
- **after_delete** - 删除记录后

---

## 基础使用

### 注册 Hook

```python
from fastapi_easy.core import migration_hook

@migration_hook("before_create")
async def validate_before_create(data):
    # 验证数据
    if not data.get("name"):
        raise ValueError("Name is required")
    return data
```

### 使用 Hook 注册表

```python
from fastapi_easy.core import HookRegistry

registry = HookRegistry()

async def log_after_create(data):
    print(f"Created: {data}")

registry.register("after_create", log_after_create)
```

---

## Hook 优先级

Hook 支持优先级控制，优先级高的 Hook 先执行：

```python
@migration_hook("before_create", priority=10)
async def high_priority_hook(data):
    pass

@migration_hook("before_create", priority=5)
async def low_priority_hook(data):
    pass
```

---

## 异步和同步 Hook

支持异步和同步 Hook：

```python
# 异步 Hook
@migration_hook("before_create")
async def async_hook(data):
    await some_async_operation()
    return data

# 同步 Hook
@migration_hook("before_create")
def sync_hook(data):
    some_sync_operation()
    return data
```

---

## 错误处理

Hook 中的错误会被隔离，不会影响其他 Hook：

```python
@migration_hook("after_create")
async def hook_with_error(data):
    try:
        await risky_operation()
    except Exception as e:
        logger.error(f"Hook error: {e}")
        # 错误被捕获，不会中断其他 Hook
```

---

## 实际应用

### 1. 数据验证

```python
@migration_hook("before_create")
async def validate_email(data):
    if not is_valid_email(data.get("email")):
        raise ValueError("Invalid email")
    return data
```

### 2. 数据转换

```python
@migration_hook("before_create")
async def normalize_data(data):
    data["name"] = data["name"].strip().lower()
    return data
```

### 3. 审计日志

```python
@migration_hook("after_create")
async def log_creation(data):
    await audit_log.create(
        action="create",
        resource="Item",
        resource_id=data["id"]
    )
```

### 4. 缓存更新

```python
@migration_hook("after_update")
async def update_cache(data):
    await cache.set(f"item:{data['id']}", data)
```

### 5. 外部系统集成

```python
@migration_hook("after_create")
async def send_notification(data):
    await notification_service.send(
        f"New item created: {data['name']}"
    )
```

---

## Hook 上下文

Hook 可以访问上下文信息：

```python
from fastapi_easy.core import HookContext

@migration_hook("before_create")
async def hook_with_context(data, context: HookContext):
    # 访问当前用户
    user = context.current_user
    # 访问请求对象
    request = context.request
    # 访问其他上下文信息
    return data
```

---

## 最佳实践

### 1. 保持 Hook 轻量

```python
# 不好：在 Hook 中进行重操作
@migration_hook("after_create")
async def heavy_hook(data):
    for i in range(1000000):
        await some_operation()

# 好：使用后台任务
@migration_hook("after_create")
async def light_hook(data):
    background_tasks.add_task(heavy_operation, data)
```

### 2. 错误处理

```python
@migration_hook("before_create")
async def safe_hook(data):
    try:
        return await validate(data)
    except ValidationError as e:
        raise ValueError(f"Validation failed: {e}")
```

### 3. 日志记录

```python
@migration_hook("after_create")
async def logged_hook(data):
    logger.info(f"Item created: {data['id']}")
    return data
```

---

## 常见问题

### Q: Hook 的执行顺序是什么？
A: 按优先级从高到低执行，优先级相同时按注册顺序执行。

### Q: Hook 中的异常会怎样？
A: 异常会被捕获并记录，不会中断其他 Hook 的执行。

### Q: 如何禁用某个 Hook？
A: 使用 `registry.unregister(event, callback)` 方法。
