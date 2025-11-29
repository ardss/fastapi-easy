# 钩子系统 (Hooks) 参考

钩子系统允许你在 CRUD 操作的生命周期中插入自定义逻辑。

## 注册钩子

使用 `router.hooks.register` 方法注册钩子函数。钩子函数必须是异步的 (`async def`)，并接收一个 `ExecutionContext` 参数。

```python
async def my_hook(context):
    print(f"Action: {context.action}")

router.hooks.register("before_create", my_hook)
```

---

## 可用钩子事件

| 事件名称 | 触发时机 | 典型用途 |
| :--- | :--- | :--- |
| `before_get_all` | 查询列表之前 | 修改过滤条件、权限检查 |
| `after_get_all` | 查询列表之后 | 修改返回结果、日志记录 |
| `before_get_one` | 查询单条之前 | 权限检查 |
| `after_get_one` | 查询单条之后 | 数据脱敏、关联加载 |
| `before_create` | 创建之前 | 数据验证、填充默认值 |
| `after_create` | 创建之后 | 发送通知、触发后续任务 |
| `before_update` | 更新之前 | 数据验证、权限检查 |
| `after_update` | 更新之后 | 审计日志、缓存失效 |
| `before_delete` | 删除之前 | 关联检查、权限检查 |
| `after_delete` | 删除之后 | 清理资源、审计日志 |

---

## ExecutionContext 对象

钩子函数接收的上下文对象包含以下属性：

| 属性名 | 类型 | 描述 |
| :--- | :--- | :--- |
| `request` | `fastapi.Request` | 原始 HTTP 请求对象 |
| `schema` | `Type[BaseModel]` | 当前操作的 Pydantic 模型类 |
| `adapter` | `ORMAdapter` | 当前使用的数据库适配器 |
| `data` | `Dict` | (仅写操作) 提交的数据字典 |
| `result` | `Any` | (仅 `after_` 钩子) 操作返回的结果 |
| `filters` | `Dict` | (仅 `get_all`) 解析后的过滤条件 |
| `sorts` | `Dict` | (仅 `get_all`) 解析后的排序条件 |
| `pagination` | `Dict` | (仅 `get_all`) 分页参数 |
| `metadata` | `Dict` | 其他元数据（如 `id`） |

---

## 示例

### 1. 自动填充创建者 ID

```python
async def set_creator(context):
    # 假设已通过中间件将 user_id 放入 request.state
    user_id = context.request.state.user.id
    context.data["creator_id"] = user_id

router.hooks.register("before_create", set_creator)
```

### 2. 数据脱敏

```python
async def hide_sensitive_data(context):
    if context.result:
        # 假设 result 是 Pydantic 模型或字典
        if hasattr(context.result, "secret_key"):
            context.result.secret_key = "***"

router.hooks.register("after_get_one", hide_sensitive_data)
```

### 3. 权限检查

```python
from fastapi import HTTPException

async def check_admin(context):
    user = context.request.state.user
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Need admin permission")

router.hooks.register("before_delete", check_admin)
```
