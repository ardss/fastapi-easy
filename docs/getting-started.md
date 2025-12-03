# 快速开始

**预计时间**: 5 分钟 ⏱️

---

## 📦 安装

### 最小安装

```bash
pip install fastapi-easy fastapi uvicorn
```

### 完整安装（含数据库支持）

```bash
# SQLAlchemy 支持
pip install fastapi-easy fastapi uvicorn sqlalchemy aiosqlite

# PostgreSQL 支持
pip install fastapi-easy fastapi uvicorn sqlalchemy asyncpg

# MongoDB 支持
pip install fastapi-easy fastapi uvicorn motor pymongo
```

---

## 🚀 最简单的例子（10 行代码）

创建文件 `main.py`:

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from pydantic import BaseModel

class Item(BaseModel):
    id: int
    name: str
    price: float

app = FastAPI()
router = CRUDRouter(schema=Item)
app.include_router(router)
```

**就这样！** 你已经有了完整的 CRUD API。

---

## 💾 与数据库集成

如果你想使用真实数据库，这是完整的例子：

```python
from fastapi import FastAPI
from fastapi_easy import CRUDRouter
from fastapi_easy.backends import SQLAlchemyAdapter
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float
from pydantic import BaseModel

# 1️⃣ 定义 ORM 模型
Base = declarative_base()

class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    price = Column(Float)

# 2️⃣ 定义 Pydantic Schema
class Item(BaseModel):
    id: int
    name: str
    price: float
    
    class Config:
        from_attributes = True

# 3️⃣ 配置数据库
engine = create_async_engine("sqlite+aiosqlite:///./test.db")
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 4️⃣ 创建应用
app = FastAPI(title="FastAPI-Easy 示例")

# 5️⃣ 初始化数据库表
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 6️⃣ 生成 CRUD API
router = CRUDRouter(
    schema=Item,
    adapter=SQLAlchemyAdapter(ItemDB, get_db)
)
app.include_router(router)
```

---

## ▶️ 运行应用

```bash
uvicorn main:app --reload
```

### 测试 API

打开浏览器访问：

- **API 文档**: http://localhost:8000/docs
- **备用文档**: http://localhost:8000/redoc

### 尝试 API

```bash
# 创建
curl -X POST http://localhost:8000/items \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "name": "Apple", "price": 1.5}'

# 获取所有
curl http://localhost:8000/items

# 获取单个
curl http://localhost:8000/items/1

# 更新
curl -X PUT http://localhost:8000/items/1 \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "name": "Apple", "price": 2.0}'

# 删除
curl -X DELETE http://localhost:8000/items/1
```

---

## 🎯 自动生成的 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/items` | 获取所有项目 |
| GET | `/items/{id}` | 获取单个项目 |
| POST | `/items` | 创建新项目 |
| PUT | `/items/{id}` | 更新项目 |
| DELETE | `/items/{id}` | 删除项目 |

---

## 🔍 启用高级功能

### 启用过滤、排序、分页

```python
router = CRUDRouter(
    schema=Item,
    adapter=SQLAlchemyAdapter(ItemDB, get_db),
    enable_filters=True,           # 启用过滤
    enable_sorters=True,           # 启用排序
    enable_pagination=True,        # 启用分页
    filter_fields=["name", "price"],
    sort_fields=["name", "price"],
    default_limit=10,
    max_limit=100,
)
```

### 使用高级功能

```bash
# 过滤
curl "http://localhost:8000/items?name=Apple&price__gt=1"

# 排序
curl "http://localhost:8000/items?sort=-price"

# 分页
curl "http://localhost:8000/items?skip=0&limit=10"

# 组合
curl "http://localhost:8000/items?name=Apple&sort=-price&skip=0&limit=10"
```

---

## 📚 下一步

- **[用户指南](guides/index.md)** - 深入学习各项功能
- **[数据库集成](tutorial/02-database-integration.md)** - 学习如何集成不同的数据库
- **[查询和过滤](guides/querying.md)** - 学习高级查询功能
- **[API 参考](reference/api.md)** - 查看完整的 API 文档
- **[完整示例](tutorial/03-complete-example.md)** - 查看完整的项目示例

---

## ❓ 常见问题

### Q: 我可以不使用数据库吗？

**A**: 可以！FastAPI-Easy 支持内存存储。只需使用 `CRUDRouter(schema=Item)` 而不指定 adapter。

### Q: 支持哪些数据库？

**A**: SQLAlchemy、Tortoise ORM、MongoDB、SQLModel。详见[数据库适配器](adapters/index.md)。

### Q: 如何添加自定义验证？

**A**: 使用 Pydantic 的验证器。详见[错误处理](guides/error-handling.md)。

### Q: 如何添加权限控制？

**A**: 使用 `enable_permissions=True` 和权限检查函数。详见[权限控制](guides/permissions-basic.md)。

---

## 🆘 需要帮助？

- 📖 [完整文档](index.md)
- 💬 [GitHub 讨论](https://github.com/ardss/fastapi-easy/discussions)
- 🐛 [报告问题](https://github.com/ardss/fastapi-easy/issues)
