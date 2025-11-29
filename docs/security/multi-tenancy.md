# 多租户支持 (Multi-Tenancy)

FastAPI-Easy 提供了原生的多租户支持，专为 SaaS 应用设计。它能够自动隔离不同租户的数据、权限和资源，确保数据安全。

---

## 多租户架构

- **租户隔离中间件**: 通过自定义头 (`X-Tenant-ID`) 标识和隔离不同租户的请求。

- **租户数据隔离**: 在查询时自动添加租户过滤条件，通过 `TenantContext` 实现。

- **权限隔离**: 不同租户之间的权限完全隔离，防止越权访问。

- **资源隔离**: 确保每个租户只能访问自己的资源。

- **中间件集成**: 自动处理租户识别，无需在业务代码中手动处理。

---

## 快速开始

### 1. 启用租户中间件

使用 `TenantIsolationMiddleware` 启用租户隔离功能：

```python
from fastapi import FastAPI
from fastapi_easy.security import (
    TenantIsolationMiddleware,
    TenantContext
)

app = FastAPI()

# 添加租户隔离中间件
app.add_middleware(
    TenantIsolationMiddleware,
    tenant_header="X-Tenant-ID"
)
```

### 2. 定义租户感知的 Schema

```python
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    tenant_id: str  # 租户 ID
```

### 3. 配置 CRUDRouter

```python
from fastapi_easy import CRUDRouter

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    enable_tenant_isolation=True,
    tenant_field="tenant_id"
)

app.include_router(router)
```

---

## 租户隔离工作流程

### 请求处理

```
1. 客户端发送请求，包含 X-Tenant-ID 头
2. 中间件提取租户 ID，存储在 TenantContext
3. 路由处理器自动添加租户过滤条件
4. 数据库查询只返回该租户的数据
5. 响应返回给客户端
```

### 示例请求

```bash
# 请求
curl -H "X-Tenant-ID: tenant-123" http://localhost:8000/items

# 响应
{
    "items": [
        {"id": 1, "name": "Item 1", "tenant_id": "tenant-123"},
        {"id": 2, "name": "Item 2", "tenant_id": "tenant-123"}
    ]
}
```

---

## 高级配置

### 自定义租户识别

```python
from fastapi import Request
from fastapi_easy.security import TenantContext

async def get_tenant_id(request: Request) -> str:
    # 从 JWT token 中提取租户 ID
    token = request.headers.get("Authorization")
    tenant_id = extract_tenant_from_token(token)
    return tenant_id

app.add_middleware(
    TenantIsolationMiddleware,
    tenant_getter=get_tenant_id
)
```

### 租户级别的权限控制

```python
from fastapi_easy.security import PermissionConfig

config = PermissionConfig(
    enabled=True,
    tenant_aware=True,
    tenant_field="tenant_id"
)

router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    permission_config=config
)
```

### 跨租户查询（管理员）

```python
from fastapi import Depends
from fastapi_easy.security import TenantContext

@app.get("/admin/items")
async def get_all_items(
    current_user: User = Depends(get_current_user),
    tenant_context: TenantContext = Depends()
):
    # 管理员可以查看所有租户的数据
    if current_user.is_admin:
        tenant_context.bypass_isolation = True
    
    return items
```

---

## 最佳实践

### 1. 始终验证租户 ID

```python
@app.middleware("http")
async def validate_tenant(request: Request, call_next):
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        return JSONResponse(
            status_code=400,
            content={"detail": "X-Tenant-ID header is required"}
        )
    return await call_next(request)
```

### 2. 使用租户 ID 作为复合主键

```python
from sqlalchemy import Column, String, Integer, UniqueConstraint

class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, primary_key=True)
    name = Column(String)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'id', name='uq_tenant_item'),
    )
```

### 3. 审计租户操作

```python
from fastapi_easy.core import AuditLog

class TenantAuditLog(AuditLog):
    tenant_id: str
    
    class Config:
        table_name = "tenant_audit_logs"
```

### 4. 定期检查租户隔离

```python
# 测试租户隔离
def test_tenant_isolation():
    # 租户 A 的请求
    response_a = client.get(
        "/items",
        headers={"X-Tenant-ID": "tenant-a"}
    )
    
    # 租户 B 的请求
    response_b = client.get(
        "/items",
        headers={"X-Tenant-ID": "tenant-b"}
    )
    
    # 验证数据不重叠
    assert response_a.json() != response_b.json()
```

---

## 常见问题

### Q: 如何处理租户之间的数据共享？
A: 使用共享资源表，标记哪些数据可以跨租户访问。

### Q: 如何迁移现有应用到多租户？
A: 添加 `tenant_id` 字段，使用数据迁移脚本为现有数据分配租户。

### Q: 如何处理租户删除？
A: 实现软删除，保留租户的历史数据以供审计。

### Q: 性能会受到影响吗？
A: 租户隔离只添加一个简单的 WHERE 子句，性能影响极小。
