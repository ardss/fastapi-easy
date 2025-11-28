"""
FastAPI-Easy 示例 4: 高级功能 (软删除、权限、审计日志、Hook)

这个示例展示如何实现企业级功能。

功能:
    - 软删除 (Soft Delete)
    - 权限控制 (Permissions)
    - 审计日志 (Audit Logging)
    - Hook 系统 (Hooks)

运行方式:
    uvicorn examples.04_advanced_features:app --reload

访问 API 文档:
    http://localhost:8000/docs

学习内容:
    - 如何实现软删除
    - 如何实现权限控制
    - 如何记录审计日志
    - 如何使用 Hook 系统

预计学习时间: 30 分钟
代码行数: ~200 行
复杂度: ⭐⭐⭐⭐ 复杂
"""

from fastapi import FastAPI, Query, HTTPException, Header
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json

# ============ 1. 数据库配置 ============

DATABASE_URL = "sqlite:///./example_advanced.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============ 2. 用户角色枚举 ============

class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


# ============ 3. ORM 模型 ============

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


class AuditLogDB(Base):
    """审计日志数据库模型"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, index=True)
    action = Column(String, index=True)  # create, read, update, delete
    resource = Column(String, index=True)  # article, user, etc.
    resource_id = Column(Integer, index=True)
    details = Column(String)  # JSON 格式的详细信息
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


# ============ 4. Pydantic Schema ============

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


class AuditLog(BaseModel):
    """审计日志 API Schema"""
    id: Optional[int] = None
    user: str
    action: str
    resource: str
    resource_id: int
    details: str
    timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============ 5. 创建应用 ============

app = FastAPI(
    title="FastAPI-Easy 示例 4",
    description="高级功能 (软删除、权限、审计日志、Hook)",
    version="1.0.0",
)


# ============ 6. 权限检查函数 ============

def check_permission(user_role: str, required_role: str) -> bool:
    """
    检查用户权限
    
    权限等级: admin > editor > viewer
    """
    role_levels = {
        UserRole.ADMIN.value: 3,
        UserRole.EDITOR.value: 2,
        UserRole.VIEWER.value: 1,
    }
    
    user_level = role_levels.get(user_role, 0)
    required_level = role_levels.get(required_role, 0)
    
    return user_level >= required_level


def verify_user_role(authorization: Optional[str] = Header(None)) -> str:
    """
    验证用户角色
    
    Header 格式: Authorization: Bearer {role}
    例如: Authorization: Bearer admin
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少授权信息")
    
    try:
        scheme, role = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="无效的授权方案")
        
        if role not in [r.value for r in UserRole]:
            raise HTTPException(status_code=401, detail="无效的用户角色")
        
        return role
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的授权格式")


# ============ 7. 审计日志函数 ============

def log_audit(
    user: str,
    action: str,
    resource: str,
    resource_id: int,
    details: Dict[str, Any] = None
):
    """记录审计日志"""
    db = SessionLocal()
    try:
        audit_log = AuditLogDB(
            user=user,
            action=action,
            resource=resource,
            resource_id=resource_id,
            details=json.dumps(details or {}),
        )
        db.add(audit_log)
        db.commit()
    finally:
        db.close()


# ============ 8. Hook 函数 ============

def before_create_hook(data: Dict[str, Any], user: str):
    """创建前的 Hook"""
    print(f"[HOOK] 用户 {user} 即将创建文章: {data.get('title')}")


def after_create_hook(article: Article, user: str):
    """创建后的 Hook"""
    print(f"[HOOK] 用户 {user} 创建了文章: {article.title} (ID: {article.id})")
    log_audit(user, "create", "article", article.id, {"title": article.title})


def before_update_hook(article_id: int, data: Dict[str, Any], user: str):
    """更新前的 Hook"""
    print(f"[HOOK] 用户 {user} 即将更新文章 {article_id}")


def after_update_hook(article: Article, user: str):
    """更新后的 Hook"""
    print(f"[HOOK] 用户 {user} 更新了文章: {article.title}")
    log_audit(user, "update", "article", article.id, {"title": article.title})


def before_delete_hook(article_id: int, user: str):
    """删除前的 Hook"""
    print(f"[HOOK] 用户 {user} 即将删除文章 {article_id}")


def after_delete_hook(article_id: int, user: str):
    """删除后的 Hook"""
    print(f"[HOOK] 用户 {user} 删除了文章 {article_id}")
    log_audit(user, "delete", "article", article_id, {})


# ============ 9. 定义路由 ============

@app.get("/", tags=["root"])
async def root():
    """根路由"""
    return {
        "message": "欢迎使用 FastAPI-Easy 示例 4",
        "docs": "/docs",
        "features": [
            "软删除 (Soft Delete)",
            "权限控制 (Permissions)",
            "审计日志 (Audit Logging)",
            "Hook 系统 (Hooks)",
        ],
        "usage": {
            "authorization": "使用 Authorization header: Bearer {role}",
            "roles": ["admin", "editor", "viewer"],
            "permissions": {
                "create": "editor, admin",
                "update": "editor, admin",
                "delete": "admin",
                "read": "viewer, editor, admin",
            }
        }
    }


@app.get("/articles", tags=["articles"], summary="获取文章列表")
async def get_articles(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    include_deleted: bool = Query(False, description="是否包含已删除的文章"),
    user_role: str = None,
):
    """
    获取文章列表
    
    参数:
        skip: 跳过的记录数
        limit: 返回的记录数
        include_deleted: 是否包含已删除的文章 (仅 admin 可用)
    """
    # 注意: 在实际应用中，user_role 会由 verify_user_role() 提供
    if user_role is None:
        user_role = UserRole.VIEWER.value
    
    db = SessionLocal()
    try:
        query = db.query(ArticleDB)
        
        # 软删除过滤
        if not include_deleted or not check_permission(user_role, UserRole.ADMIN.value):
            query = query.filter(ArticleDB.is_deleted == False)
        
        total = query.count()
        articles = query.offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [Article.model_validate(a) for a in articles]
        }
    finally:
        db.close()


@app.get("/articles/{article_id}", tags=["articles"], summary="获取单个文章")
async def get_article(article_id: int, user_role: str = None):
    """获取单个文章"""
    if user_role is None:
        user_role = UserRole.VIEWER.value
    
    db = SessionLocal()
    try:
        article = db.query(ArticleDB).filter(
            ArticleDB.id == article_id,
            ArticleDB.is_deleted == False
        ).first()
        
        if article:
            return Article.model_validate(article)
        return {"error": "文章不存在"}
    finally:
        db.close()


@app.post("/articles", tags=["articles"], summary="创建文章", status_code=201)
async def create_article(
    article: Article,
    user_role: str = None,
    user: str = "anonymous"
):
    """
    创建新文章
    
    权限: editor, admin
    """
    if user_role is None:
        user_role = UserRole.VIEWER.value
    
    if not check_permission(user_role, UserRole.EDITOR.value):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # Hook: 创建前
    before_create_hook(article.model_dump(), user)
    
    db = SessionLocal()
    try:
        db_article = ArticleDB(
            title=article.title,
            content=article.content,
            author=user,
        )
        db.add(db_article)
        db.commit()
        db.refresh(db_article)
        
        result = Article.model_validate(db_article)
        
        # Hook: 创建后
        after_create_hook(result, user)
        
        return result
    finally:
        db.close()


@app.put("/articles/{article_id}", tags=["articles"], summary="更新文章")
async def update_article(
    article_id: int,
    article: Article,
    user_role: str = None,
    user: str = "anonymous"
):
    """
    更新文章
    
    权限: editor (自己的文章), admin (所有文章)
    """
    if user_role is None:
        user_role = UserRole.VIEWER.value
    
    if not check_permission(user_role, UserRole.EDITOR.value):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # Hook: 更新前
    before_update_hook(article_id, article.model_dump(), user)
    
    db = SessionLocal()
    try:
        db_article = db.query(ArticleDB).filter(ArticleDB.id == article_id).first()
        if not db_article:
            return {"error": "文章不存在"}
        
        # 权限检查: editor 只能更新自己的文章
        if user_role == UserRole.EDITOR.value and db_article.author != user:
            raise HTTPException(status_code=403, detail="只能更新自己的文章")
        
        db_article.title = article.title
        db_article.content = article.content
        db_article.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_article)
        
        result = Article.model_validate(db_article)
        
        # Hook: 更新后
        after_update_hook(result, user)
        
        return result
    finally:
        db.close()


@app.delete("/articles/{article_id}", tags=["articles"], summary="删除文章 (软删除)")
async def delete_article(
    article_id: int,
    user_role: str = None,
    user: str = "anonymous"
):
    """
    删除文章 (软删除)
    
    权限: admin
    """
    if user_role is None:
        user_role = UserRole.VIEWER.value
    
    if not check_permission(user_role, UserRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="权限不足")
    
    # Hook: 删除前
    before_delete_hook(article_id, user)
    
    db = SessionLocal()
    try:
        db_article = db.query(ArticleDB).filter(ArticleDB.id == article_id).first()
        if not db_article:
            return {"error": "文章不存在"}
        
        # 软删除: 标记为已删除，而不是真正删除
        db_article.is_deleted = True
        db_article.deleted_at = datetime.utcnow()
        
        db.commit()
        
        # Hook: 删除后
        after_delete_hook(article_id, user)
        
        return {"message": "文章已删除"}
    finally:
        db.close()


@app.get("/audit-logs", tags=["audit"], summary="获取审计日志")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    user_role: str = None,
):
    """
    获取审计日志
    
    权限: admin
    """
    if user_role is None:
        user_role = UserRole.VIEWER.value
    
    if not check_permission(user_role, UserRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="权限不足")
    
    db = SessionLocal()
    try:
        total = db.query(AuditLogDB).count()
        logs = db.query(AuditLogDB).order_by(
            AuditLogDB.timestamp.desc()
        ).offset(skip).limit(limit).all()
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [AuditLog.model_validate(log) for log in logs]
        }
    finally:
        db.close()


# ============ 10. 初始化数据库 ============

@app.on_event("startup")
async def startup_event():
    """应用启动时创建表"""
    Base.metadata.create_all(bind=engine)


# ============ 11. 如何运行此示例 ============

if __name__ == "__main__":
    from utils import run_app
    
    # 使用 run_app 自动处理端口占用问题
    run_app(app, start_port=8000, open_browser=True)


# ============ 学习要点 ============

"""
✅ 学到的内容:

1. 软删除 (Soft Delete)
   - 添加 is_deleted 标记
   - 添加 deleted_at 时间戳
   - 查询时过滤已删除的记录

2. 权限控制 (Permissions)
   - 定义用户角色
   - 检查权限
   - 基于角色的访问控制 (RBAC)

3. 审计日志 (Audit Logging)
   - 记录所有操作
   - 记录操作者、操作类型、资源
   - 记录详细信息

4. Hook 系统 (Hooks)
   - 在操作前执行逻辑
   - 在操作后执行逻辑
   - 用于扩展功能

❓ 常见问题:

Q: 为什么使用软删除而不是真正删除?
A: 软删除可以保留数据历史，便于审计和恢复。

Q: 如何恢复已删除的文章?
A: 添加一个恢复端点，将 is_deleted 设置为 False。

Q: 如何实现更复杂的权限?
A: 使用权限矩阵或 ACL (访问控制列表)。

Q: 如何优化审计日志查询?
A: 添加索引、分区、或归档旧日志。

🔗 相关文档:
- 软删除: docs/usage/10-soft-delete.md
- 权限控制: docs/usage/12-permissions.md
- 审计日志: docs/usage/13-audit-logging.md

📚 下一步:
- 测试不同角色的权限
- 查看审计日志
- 查看 05_complete_ecommerce.py 学习完整项目
"""
