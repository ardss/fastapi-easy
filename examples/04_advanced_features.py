"""
FastAPI-Easy 示例 4: 高级功能 (软删除、审计日志、Hook)

这个示例展示如何启用企业级功能。

功能:
    - 软删除 (Soft Delete) - enable_soft_delete
    - 审计日志 (Audit Logging) - enable_audit
    - Hook 系统 (Hooks) - before/after hooks

运行方式:
    python examples/04_advanced_features.py

访问 API 文档:
    http://localhost:8001/docs

学习内容:
    - 如何启用软删除
    - 如何启用审计日志
    - 如何使用 Hook 系统

预计学习时间: 10 分钟
代码行数: ~50 行 (不包括注释)
复杂度: ⭐⭐⭐⭐ 复杂
"""

from fastapi import FastAPI
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from fastapi_easy import CRUDRouter, SQLAlchemyAdapter, CRUDConfig

# ============ 1. 数据库配置 ============

DATABASE_URL = "sqlite:///./example_advanced.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============ 2. ORM 模型 (支持软删除) ============

class ArticleDB(Base):
    """文章数据库模型 (支持软删除)"""
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    author = Column(String, index=True)
    is_deleted = Column(Boolean, default=False, index=True)  # 软删除标记
    deleted_at = Column(DateTime, nullable=True)  # 删除时间
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============ 3. Pydantic Schema ============

class Article(BaseModel):
    """文章 API Schema"""
    id: Optional[int] = None
    title: str
    content: str
    author: str
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 4. 创建应用 ============

app = FastAPI(
    title="FastAPI-Easy 示例 4",
    description="高级功能 - 软删除、审计日志、Hook",
    version="1.0.0",
)

# 创建数据库表
Base.metadata.create_all(bind=engine)


# ============ 5. 创建配置 (启用高级功能!) ============

config = CRUDConfig(
    enable_soft_delete=True,      # 启用软删除
    enable_audit=True,            # 启用审计日志
    deleted_at_field="deleted_at", # 软删除时间戳字段
)


# ============ 6. 创建适配器 ============

adapter = SQLAlchemyAdapter(model=ArticleDB, session_factory=SessionLocal)


# ============ 7. 创建 CRUDRouter (自动启用高级功能!) ============

router = CRUDRouter(schema=Article, adapter=adapter, config=config)

# 注册路由
app.include_router(router)


# ============ 8. Hook 系统 (可选) ============

@router.hooks.on("before_create")
async def before_create_hook(context):
    """创建前的 Hook"""
    print(f"[HOOK] 即将创建文章: {context.data.get('title')}")


@router.hooks.on("after_create")
async def after_create_hook(context):
    """创建后的 Hook"""
    print(f"[HOOK] 创建了文章: {context.result.title}")


@router.hooks.on("before_delete")
async def before_delete_hook(context):
    """删除前的 Hook"""
    print(f"[HOOK] 即将删除文章 ID: {context.id}")


@router.hooks.on("after_delete")
async def after_delete_hook(context):
    """删除后的 Hook"""
    print(f"[HOOK] 删除了文章 ID: {context.id}")


# ============ 9. 根路由 (可选) ============

@app.get("/", tags=["root"])
async def root():
    """欢迎页面"""
    return {
        "message": "欢迎使用 FastAPI-Easy 示例 4",
        "docs": "/docs",
        "features": [
            "软删除 (Soft Delete)",
            "审计日志 (Audit Logging)",
            "Hook 系统 (Hooks)",
        ],
        "notes": [
            "DELETE /articles/{id} 执行软删除 (不真正删除)",
            "所有操作自动记录审计日志",
            "Hook 在操作前后自动触发",
        ]
    }


# ============ 10. 如何运行此示例 ============

if __name__ == "__main__":
    from utils import run_app
    
    # 自动处理端口占用，自动打开浏览器
    run_app(app, start_port=8000, open_browser=True)


# ============ 学习要点 ============

"""
✅ 这个示例展示了什么:

1. 定义支持软删除的 ORM 模型
   - 添加 is_deleted 字段 (Boolean)
   - 添加 deleted_at 字段 (DateTime)

2. 定义 CRUDConfig 启用高级功能
   - enable_soft_delete=True: 启用软删除
   - enable_audit=True: 启用审计日志
   - deleted_at_field: 指定软删除时间戳字段

3. 创建 CRUDRouter 并传入 config
   - 只需一行代码: router = CRUDRouter(..., config=config)
   - 所有高级功能自动启用！

4. 使用 Hook 系统 (可选)
   - @router.hooks.on("before_create"): 创建前执行
   - @router.hooks.on("after_create"): 创建后执行
   - @router.hooks.on("before_delete"): 删除前执行
   - @router.hooks.on("after_delete"): 删除后执行

5. 自动启用的功能:
   - DELETE /articles/{id} 执行软删除 (不真正删除)
   - 所有操作自动记录审计日志
   - Hook 在操作前后自动触发

对比传统 FastAPI:
  传统 FastAPI: 300+ 行代码手动实现软删除、审计、Hook
  fastapi-easy: 50 行代码配置启用！

节省 85% 的代码！

❓ 常见问题:

Q: 软删除和真正删除有什么区别?
A: 软删除标记为已删除但保留数据，真正删除从数据库移除。

Q: 如何恢复已删除的文章?
A: 添加一个更新端点，将 is_deleted 设置为 False。

Q: 审计日志存储在哪里?
A: 由适配器处理，通常存储在数据库中。

Q: 如何自定义 Hook 逻辑?
A: 使用 @router.hooks.on() 装饰器定义自己的 Hook。

🔗 相关文档:
- 软删除: docs/usage/10-soft-delete.md
- 审计日志: docs/usage/13-audit-logging.md
- Hook 系统: docs/usage/15-hooks.md

📚 下一步:
1. 运行此示例: python examples/04_advanced_features.py
2. 访问 http://localhost:8001/docs 查看 API
3. 创建、更新、删除文章，观察 Hook 输出
4. 查看示例 5 学习完整项目
"""
