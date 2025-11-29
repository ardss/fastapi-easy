"""
基础迁移示例

展示如何使用 FastAPIEasy 的自动迁移功能
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

from fastapi_easy import FastAPIEasy

# 定义 ORM 模型
Base = declarative_base()


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Product(Base):
    """产品模型"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer)  # 价格（分）
    description = Column(String(500))


# 创建应用
# 这会自动：
# 1. 检测 Schema 变更
# 2. 生成迁移脚本
# 3. 应用迁移
# 4. 记录迁移历史
app = FastAPIEasy(
    database_url="sqlite:///example.db",
    models=[User, Product],
    migration_mode="safe",  # 仅执行安全迁移
    auto_migrate=True  # 应用启动时自动迁移
)


# 定义 API 端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "FastAPIEasy 迁移示例",
        "features": [
            "自动 Schema 检测",
            "自动迁移生成",
            "自动迁移应用",
            "迁移历史记录"
        ]
    }


@app.get("/migrations/history")
async def get_migration_history():
    """获取迁移历史"""
    history = app.get_migration_history(limit=10)
    return {
        "total": len(history),
        "migrations": history
    }


@app.get("/migrations/status")
async def get_migration_status():
    """获取迁移状态"""
    if not app.migration_engine:
        return {"status": "未初始化"}
    
    history = app.get_migration_history()
    return {
        "status": "就绪",
        "applied_migrations": len(history),
        "database_url": app.database_url,
        "migration_mode": app.migration_mode
    }


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("FastAPIEasy 迁移示例")
    print("=" * 60)
    print()
    print("启动应用...")
    print()
    print("API 端点:")
    print("  GET /                    - 根端点")
    print("  GET /migrations/history  - 迁移历史")
    print("  GET /migrations/status   - 迁移状态")
    print()
    print("访问 http://localhost:8000/docs 查看 API 文档")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
