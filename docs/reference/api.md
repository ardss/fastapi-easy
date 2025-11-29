# API 参考

FastAPI-Easy 自动生成的 CRUD API 完整参考。

---

## 基础 CRUD 端点

### 获取所有记录

```http
GET /items
```

**参数**:
- `skip` (int, optional) - 跳过的记录数，默认 0
- `limit` (int, optional) - 返回的记录数，默认 10，最大 100
- `sort` (str, optional) - 排序字段，格式: `field` 或 `-field`（降序）

**响应** (200):
```json
{
  "items": [
    {"id": 1, "name": "Item 1", "price": 10.0},
    {"id": 2, "name": "Item 2", "price": 20.0}
  ],
  "total": 100,
  "skip": 0,
  "limit": 10
}
```

---

### 获取单个记录

```http
GET /items/{id}
```

**参数**:
- `id` (int, required) - 记录 ID

**响应** (200):
```json
{
  "id": 1,
  "name": "Item 1",
  "price": 10.0
}
```

**错误** (404):
```json
{
  "detail": "Item not found"
}
```

---

### 创建记录

```http
POST /items
Content-Type: application/json
```

**请求体**:
```json
{
  "name": "New Item",
  "price": 15.0
}
```

**响应** (201):
```json
{
  "id": 3,
  "name": "New Item",
  "price": 15.0
}
```

**错误** (422):
```json
{
  "detail": [
    {
      "loc": ["body", "price"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

---

### 更新记录

```http
PUT /items/{id}
Content-Type: application/json
```

**参数**:
- `id` (int, required) - 记录 ID

**请求体**:
```json
{
  "name": "Updated Item",
  "price": 25.0
}
```

**响应** (200):
```json
{
  "id": 1,
  "name": "Updated Item",
  "price": 25.0
}
```

---

### 删除单个记录

```http
DELETE /items/{id}
```

**参数**:
- `id` (int, required) - 记录 ID

**响应** (204):
无内容

---

### 删除所有记录

```http
DELETE /items
```

**响应** (204):
无内容

---

## 过滤 API

### 过滤操作符

| 操作符 | 说明 | 示例 |
|--------|------|------|
| 无 | 精确匹配 | `?name=apple` |
| `__gt` | 大于 | `?price__gt=10` |
| `__gte` | 大于等于 | `?price__gte=10` |
| `__lt` | 小于 | `?price__lt=20` |
| `__lte` | 小于等于 | `?price__lte=20` |
| `__ne` | 不等于 | `?status__ne=inactive` |
| `__in` | 包含在列表中 | `?category__in=fruit,vegetable` |
| `__contains` | 包含字符串 | `?name__contains=app` |
| `__icontains` | 不区分大小写包含 | `?name__icontains=APPLE` |

### 过滤示例

```http
GET /items?name=apple&price__gt=10&price__lt=20
```

---

## 排序 API

### 排序语法

```http
GET /items?sort=name,-price
```

- `sort=field` - 升序
- `sort=-field` - 降序
- 多字段排序用逗号分隔

### 排序示例

```http
GET /items?sort=created_at,-price
```

---

## 分页 API

### 分页参数

```http
GET /items?skip=0&limit=10
```

- `skip` - 跳过的记录数
- `limit` - 返回的记录数

### 分页示例

```http
# 第 1 页
GET /items?skip=0&limit=10

# 第 2 页
GET /items?skip=10&limit=10

# 第 3 页
GET /items?skip=20&limit=10
```

---

## 批量操作 API

### 批量创建

```http
POST /items/batch
Content-Type: application/json
```

**请求体**:
```json
{
  "items": [
    {"name": "Item 1", "price": 10.0},
    {"name": "Item 2", "price": 20.0},
    {"name": "Item 3", "price": 30.0}
  ]
}
```

**响应** (200):
```json
{
  "created": 3,
  "items": [
    {"id": 1, "name": "Item 1", "price": 10.0},
    {"id": 2, "name": "Item 2", "price": 20.0},
    {"id": 3, "name": "Item 3", "price": 30.0}
  ]
}
```

---

### 批量更新

```http
PUT /items/batch
Content-Type: application/json
```

**请求体**:
```json
{
  "items": [
    {"id": 1, "name": "Updated 1", "price": 15.0},
    {"id": 2, "name": "Updated 2", "price": 25.0}
  ]
}
```

**响应** (200):
```json
{
  "updated": 2,
  "items": [
    {"id": 1, "name": "Updated 1", "price": 15.0},
    {"id": 2, "name": "Updated 2", "price": 25.0}
  ]
}
```

---

### 批量删除

```http
DELETE /items/batch
Content-Type: application/json
```

**请求体**:
```json
{
  "ids": [1, 2, 3]
}
```

**响应** (200):
```json
{
  "deleted": 3
}
```

---

## 软删除 API

### 获取所有记录（不包括已删除）

```http
GET /items
```

自动过滤已删除的记录。

### 获取所有记录（包括已删除）

```http
GET /items?include_deleted=true
```

### 恢复已删除的记录

```http
PATCH /items/{id}/restore
```

**响应** (200):
```json
{
  "id": 1,
  "name": "Item 1",
  "price": 10.0,
  "deleted_at": null
}
```

### 永久删除

```http
DELETE /items/{id}?permanent=true
```

---

## 权限 API

### 获取当前用户

```http
GET /auth/me
Authorization: Bearer {token}
```

**响应** (200):
```json
{
  "id": 1,
  "username": "user",
  "email": "user@example.com",
  "permissions": ["read", "create"]
}
```

### 登录

```http
POST /auth/login
Content-Type: application/json
```

**请求体**:
```json
{
  "username": "user",
  "password": "password"
}
```

**响应** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 审计日志 API

### 获取审计日志

```http
GET /audit-logs
```

**参数**:
- `user_id` (int, optional) - 用户 ID
- `action` (str, optional) - 操作类型（CREATE, READ, UPDATE, DELETE）
- `resource` (str, optional) - 资源类型
- `skip` (int, optional) - 跳过的记录数
- `limit` (int, optional) - 返回的记录数

**响应** (200):
```json
{
  "logs": [
    {
      "id": 1,
      "user_id": 1,
      "action": "CREATE",
      "resource": "Item",
      "resource_id": 1,
      "old_values": null,
      "new_values": {"name": "Item 1", "price": 10.0},
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 100
}
```

---

## 错误响应

### 常见错误码

| 状态码 | 说明 | 示例 |
|--------|------|------|
| 200 | 成功 | GET, PUT, POST, DELETE 成功 |
| 201 | 创建成功 | POST 创建新资源 |
| 204 | 无内容 | DELETE 成功 |
| 400 | 请求错误 | 参数验证失败 |
| 401 | 未认证 | 需要登录 |
| 403 | 无权限 | 权限不足 |
| 404 | 未找到 | 资源不存在 |
| 409 | 冲突 | 数据冲突 |
| 422 | 无法处理 | 数据验证失败 |
| 500 | 服务器错误 | 数据库错误 |

### 错误响应格式

```json
{
  "detail": "Error message"
}
```

---

## 请求头

### 认证

```http
Authorization: Bearer {token}
```

### 内容类型

```http
Content-Type: application/json
```

### 自定义头

```http
X-Tenant-ID: tenant-123
```

---

## 响应头

### 常见响应头

```http
Content-Type: application/json
X-Total-Count: 100
X-Page: 1
X-Per-Page: 10
```

---

## 完整请求示例

### 创建、查询、更新、删除流程

```bash
# 1. 创建记录
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Apple", "price": 10.0}'

# 响应: {"id": 1, "name": "Apple", "price": 10.0}

# 2. 查询记录
curl http://localhost:8000/items/1

# 响应: {"id": 1, "name": "Apple", "price": 10.0}

# 3. 更新记录
curl -X PUT http://localhost:8000/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Apple", "price": 15.0}'

# 响应: {"id": 1, "name": "Apple", "price": 15.0}

# 4. 删除记录
curl -X DELETE http://localhost:8000/items/1

# 响应: 204 No Content
```

---

## 常见问题

### Q: 如何进行复杂查询？
A: 组合使用过滤、排序和分页参数。

```http
GET /items?name__contains=app&price__gte=10&sort=-created_at&skip=0&limit=20
```

### Q: 如何处理大数据量？
A: 使用分页和批量操作。

```http
GET /items?skip=0&limit=1000
POST /items/batch
```

### Q: 如何获取总记录数？
A: 响应中包含 `total` 字段。

```json
{
  "items": [...],
  "total": 1000,
  "skip": 0,
  "limit": 10
}
```

### Q: 如何处理时间戳？
A: 使用 ISO 8601 格式。

```json
{
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T13:00:00Z"
}
```
