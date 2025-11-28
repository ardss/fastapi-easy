# 示例重构计划

**目标**: 确保每个示例都真正展示 fastapi-easy 的核心特性，而不是手动实现功能。

**原则**:
1. ✅ 突出自动生成的价值
2. ✅ 对比传统 FastAPI 的代码量差异
3. ✅ 清晰展示如何使用库的特性
4. ✅ 循序渐进，从简单到复杂
5. ✅ 每个示例都是可运行的、完整的

---

## 示例 1: 最简单的 CRUD ✅ (已完成)

**文件**: `01_hello_world.py`

**展示内容**:
- 定义 Pydantic Schema
- 创建 CRUDRouter
- 自动生成 CRUD API

**代码结构**:
```python
# 1. 定义 Schema
class Item(BaseModel):
    name: str
    price: float

# 2. 创建 CRUDRouter (自动生成所有 API!)
router = CRUDRouter(schema=Item)

# 3. 注册路由
app.include_router(router)
```

**自动生成的 API**:
- GET /items - 获取所有
- GET /items/{id} - 获取单个
- POST /items - 创建
- PUT /items/{id} - 更新
- DELETE /items/{id} - 删除

**代码行数**: ~10 行

**关键点**: 展示"只需 10 行代码就能生成完整 CRUD API"

---

## 示例 2: 与数据库集成 (待重写)

**文件**: `02_with_database.py`

**展示内容**:
- 定义 SQLAlchemy ORM 模型
- 创建 SQLAlchemyAdapter
- 将 adapter 传入 CRUDRouter
- 自动连接到数据库

**代码结构**:
```python
# 1. 定义 ORM 模型
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)

# 2. 定义 Pydantic Schema
class Item(BaseModel):
    name: str
    price: float

# 3. 创建适配器
adapter = SQLAlchemyAdapter(model=ItemDB, session_factory=SessionLocal)

# 4. 创建 CRUDRouter (自动连接到数据库!)
router = CRUDRouter(schema=Item, adapter=adapter)

# 5. 注册路由
app.include_router(router)
```

**对比传统 FastAPI**:
```
传统 FastAPI:
- 定义 ORM 模型
- 定义 Pydantic Schema
- 手动写 GET /items 端点 (查询数据库)
- 手动写 GET /items/{id} 端点
- 手动写 POST /items 端点
- 手动写 PUT /items/{id} 端点
- 手动写 DELETE /items/{id} 端点
= 150+ 行代码

fastapi-easy:
- 定义 ORM 模型
- 定义 Pydantic Schema
- 创建适配器
- 创建 CRUDRouter
= 30 行代码

节省 80% 的代码！
```

**代码行数**: ~30 行

**关键点**: 展示"适配器如何自动连接数据库操作"

---

## 示例 3: 启用查询功能 (待重写)

**文件**: `03_with_queries.py`

**展示内容**:
- 启用过滤功能 (enable_filters)
- 启用排序功能 (enable_sorters)
- 启用分页功能 (enable_pagination)
- 配置可过滤/可排序字段

**代码结构**:
```python
# 1. 定义 Schema 和 ORM 模型 (同示例 2)

# 2. 创建适配器 (同示例 2)

# 3. 创建配置
config = CRUDConfig(
    enable_filters=True,
    enable_sorters=True,
    enable_pagination=True,
    filter_fields=["name", "price"],
    sort_fields=["name", "price", "created_at"],
    default_limit=10,
    max_limit=100,
)

# 4. 创建 CRUDRouter (自动启用查询功能!)
router = CRUDRouter(
    schema=Item,
    adapter=adapter,
    config=config,
)

# 5. 注册路由
app.include_router(router)
```

**自动生成的查询能力**:
- GET /items?name__like=apple - 过滤
- GET /items?sort=-price - 排序
- GET /items?skip=0&limit=10 - 分页
- GET /items?name__like=apple&sort=-price&skip=0&limit=10 - 组合查询

**代码行数**: ~40 行

**关键点**: 展示"配置就能启用高级查询功能，无需手动实现"

---

## 示例 4: 高级功能 (待重写)

**文件**: `04_advanced_features.py`

**展示内容**:
- 启用软删除 (enable_soft_delete)
- 启用审计日志 (enable_audit)
- 使用 Hook 系统 (before/after hooks)
- 不同的 create_schema 和 update_schema

**代码结构**:
```python
# 1. 定义 ORM 模型 (包含 deleted_at 字段)
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)
    deleted_at = Column(DateTime, nullable=True)  # 软删除

# 2. 定义 Schema
class ItemCreate(BaseModel):
    name: str
    price: float

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted_at: Optional[datetime] = None

# 3. 创建配置
config = CRUDConfig(
    enable_soft_delete=True,
    enable_audit=True,
    deleted_at_field="deleted_at",
)

# 4. 创建适配器和 CRUDRouter
adapter = SQLAlchemyAdapter(model=ItemDB, session_factory=SessionLocal)
router = CRUDRouter(
    schema=Item,
    create_schema=ItemCreate,
    update_schema=ItemUpdate,
    adapter=adapter,
    config=config,
)

# 5. 添加 Hook (可选)
@router.hooks.on("before_create")
async def before_create(context):
    print(f"Creating item: {context.data}")

@router.hooks.on("after_create")
async def after_create(context):
    print(f"Created item: {context.result}")

# 6. 注册路由
app.include_router(router)
```

**自动启用的功能**:
- DELETE /items/{id} 执行软删除 (不真正删除)
- 所有操作自动记录审计日志
- Hook 在操作前后自动触发

**代码行数**: ~50 行

**关键点**: 展示"配置和 Hook 如何实现企业级功能"

---

## 示例 5: 完整项目 (待重写)

**文件**: `05_complete_ecommerce.py`

**展示内容**:
- 多个资源 (Category, Product, Order)
- 不同的配置
- 综合应用所有特性

**代码结构**:
```python
# 1. 定义多个 ORM 模型
class CategoryDB(Base): ...
class ProductDB(Base): ...
class OrderDB(Base): ...

# 2. 定义多个 Schema
class Category(BaseModel): ...
class Product(BaseModel): ...
class Order(BaseModel): ...

# 3. 为每个资源创建 CRUDRouter
category_router = CRUDRouter(
    schema=Category,
    adapter=SQLAlchemyAdapter(CategoryDB, SessionLocal),
    config=CRUDConfig(enable_filters=True, enable_sorters=True),
)

product_router = CRUDRouter(
    schema=Product,
    adapter=SQLAlchemyAdapter(ProductDB, SessionLocal),
    config=CRUDConfig(
        enable_filters=True,
        enable_sorters=True,
        filter_fields=["category_id", "price"],
    ),
)

order_router = CRUDRouter(
    schema=Order,
    adapter=SQLAlchemyAdapter(OrderDB, SessionLocal),
    config=CRUDConfig(
        enable_soft_delete=True,
        enable_audit=True,
    ),
)

# 4. 注册所有路由
app.include_router(category_router)
app.include_router(product_router)
app.include_router(order_router)
```

**自动生成的 API**:
- /categories - 完整 CRUD
- /products - 完整 CRUD + 过滤 + 排序
- /orders - 完整 CRUD + 软删除 + 审计

**代码行数**: ~100 行

**关键点**: 展示"如何在实际项目中使用 fastapi-easy"

---

## 改进总结

| 示例 | 特性 | 代码行数 | 对比传统 FastAPI |
|------|------|---------|-----------------|
| 1 | 基础 CRUD | ~10 | 节省 90% |
| 2 | 数据库集成 | ~30 | 节省 80% |
| 3 | 查询功能 | ~40 | 节省 85% |
| 4 | 高级功能 | ~50 | 节省 90% |
| 5 | 完整项目 | ~100 | 节省 85% |

**总体价值**: 用 fastapi-easy 开发 API 的代码量比传统 FastAPI 减少 80-90%！

---

## 实施计划

1. ✅ 示例 1 已完成 - 展示基础 CRUD 自动生成
2. ⏳ 示例 2 - 展示数据库集成
3. ⏳ 示例 3 - 展示查询功能
4. ⏳ 示例 4 - 展示高级功能
5. ⏳ 示例 5 - 展示完整项目

**下一步**: 按照上述规划重写示例 2-5，确保每个都真正展示库的特性。
