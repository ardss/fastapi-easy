# FastAPI-Easy

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-green)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-2.0%2B-orange)](https://docs.pydantic.dev/)
[![License](https://img.shields.io/badge/License-AGPL3.0-red)](LICENSE)

**FastAPI-Easy** 是一个生产级的 FastAPI 开发框架，旨在通过自动化 CRUD 路由、内置安全特性和强大的数据库迁移工具，显著提升开发效率。

它不仅是一个 CRUD 生成器，更是一个集成了认证、权限、审计、多租户和数据库管理的完整解决方案。

---

## 📚 文档

👉 **[阅读完整文档](docs/README.md)** | [快速开始](docs/tutorial/01-quick-start.md) | [API 参考](docs/reference/api.md)

### 文档导航

- **[快速开始](docs/tutorial/01-quick-start.md)** (5 分钟) - 运行你的第一个 CRUD API
- **[功能指南](docs/guides/)** - Hook 系统、缓存、GraphQL、WebSocket 等
- **[API 参考](docs/reference/api.md)** - 完整的 API 文档
- **[安全指南](docs/security/)** - 认证、权限、速率限制
- **[ORM 适配器](docs/adapters/)** - SQLAlchemy、Tortoise、MongoDB、SQLModel

---

## ✨ 核心特性

*   **自动化 CRUD**: 基于 Pydantic 模型自动生成包含搜索、排序、分页和软删除功能的标准 API。
*   **企业级安全**: 内置 JWT 认证、RBAC/ABAC 权限控制、审计日志、速率限制和登录保护。
*   **多租户架构**: 原生支持多租户数据隔离和权限管理。
*   **数据库迁移**: 智能 Schema 检测、自动生成迁移脚本、分布式锁和回滚支持。
*   **多 ORM 支持**: 统一适配 SQLAlchemy, Tortoise, MongoDB (Motor) 和 SQLModel。
*   **扩展能力**: 开箱即用的 GraphQL 和 WebSocket 支持。

## 📦 安装

```bash
pip install fastapi-easy
```

安装特定数据库支持：

```bash
pip install "fastapi-easy[sqlalchemy]"  # 或 tortoise, mongo, sqlmodel
```

## 🚀 快速开始

这是一个**可以直接运行**的完整示例。保存为 `main.py` 并运行即可。

```python
import uvicorn
from fastapi import FastAPI
from fastapi_easy import CRUDRouter, SQLAlchemyAdapter
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. 配置数据库 (使用 SQLite 内存模式)
DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# 2. 定义模型
Base = declarative_base()
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)

class UserCreate(BaseModel):
    name: str

# 3. 创建应用
app = FastAPI()

# 4. 一行代码注册 CRUD 路由
app.include_router(
    CRUDRouter(
        schema=UserCreate,
        adapter=SQLAlchemyAdapter(UserDB, get_db),
        prefix="/users"
    )
)

# 启动: uvicorn main:app --reload
if __name__ == "__main__":
    uvicorn.run(app)
```

**运行后，你将立即获得以下 API：**

| 方法 | 路径 | 描述 | 功能 |
|------|------|------|------|
| `GET` | `/users` | 获取列表 | 支持分页、排序 (`?sort=-id`)、过滤 (`?name__like=John`) |
| `GET` | `/users/{id}` | 获取详情 | 获取单条记录 |
| `POST` | `/users` | 创建 | 创建新记录 |
| `PUT` | `/users/{id}` | 更新 | 全量或部分更新 |
| `DELETE` | `/users/{id}` | 删除 | 软删除或物理删除 |
| `DELETE` | `/users` | 批量删除 | (可选) 批量删除接口 |

---

## 🧩 功能模块

### 🛡️ 安全与权限
无需手动编写中间件，直接使用装饰器保护路由：

```python
from fastapi_easy.security import require_role, JWTAuth

# 1. 保护路由
@app.get("/admin")
@require_role("admin")  # 仅管理员可访问
async def admin_dashboard():
    return {"msg": "Welcome Admin"}
```

### 🏗️ 数据库迁移
内置生产级迁移引擎，支持自动检测和安全模式：

```bash
# 自动检测模型变更并生成迁移脚本
fastapi-easy migrate plan --message "add_user_table"

# 应用迁移 (支持分布式锁，防止并发冲突)
fastapi-easy migrate apply
```

### 🏢 多租户支持
专为 SaaS 设计，自动处理数据隔离：

```python
from fastapi_easy.security import TenantIsolationMiddleware

# 自动从 Header (X-Tenant-ID) 隔离数据
app.add_middleware(TenantIsolationMiddleware)
```

## 🤝 贡献

欢迎提交 Pull Requests 或 Issues。在提交代码前，请确保通过所有测试并遵循代码规范。

## 📄 许可证

本项目采用 [AGPL-3.0](LICENSE) 许可证。
