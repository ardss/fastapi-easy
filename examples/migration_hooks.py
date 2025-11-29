"""
Hook 系统示例

展示如何使用迁移 Hook 来自定义迁移流程
"""

import logging

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from fastapi_easy import FastAPIEasy
from fastapi_easy.migrations.hooks import HookTrigger, migration_hook

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义 ORM 模型
Base = declarative_base()


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True)


class Product(Base):
    """产品模型"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Integer)


# 创建应用
app = FastAPIEasy(
    database_url="sqlite:///example_hooks.db",
    models=[User, Product],
    migration_mode="safe"
)

# 获取 Hook 注册表
hook_registry = app.migration_engine.hook_registry if app.migration_engine else None


# ============ Hook 示例 ============

# 1. 在迁移前执行备份
@migration_hook(HookTrigger.BEFORE_DDL, priority=100)
async def backup_before_migration(context):
    """在 DDL 执行前进行备份"""
    logger.info("🔄 执行迁移前备份...")
    # 这里可以添加备份逻辑
    logger.info("✅ 备份完成")
    return {"backup_status": "completed"}


# 2. 在迁移后验证
@migration_hook(HookTrigger.AFTER_DDL, priority=50)
async def verify_after_migration(context):
    """在 DDL 执行后进行验证"""
    logger.info("🔍 验证迁移结果...")
    # 这里可以添加验证逻辑
    logger.info("✅ 验证完成")
    return {"verification_status": "passed"}


# 3. 在 DML 前记录日志
@migration_hook(HookTrigger.BEFORE_DML, priority=10)
async def log_before_dml(context):
    """在 DML 执行前记录日志"""
    logger.info(f"📝 执行 DML 操作: {context}")
    return {"log_status": "recorded"}


# 4. 在 DML 后清理
@migration_hook(HookTrigger.AFTER_DML, priority=10)
async def cleanup_after_dml(context):
    """在 DML 执行后进行清理"""
    logger.info("🧹 清理临时数据...")
    # 这里可以添加清理逻辑
    logger.info("✅ 清理完成")
    return {"cleanup_status": "completed"}


# ============ API 端点 ============

@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "FastAPIEasy Hook 系统示例",
        "features": [
            "迁移前备份",
            "迁移后验证",
            "DML 前日志",
            "DML 后清理"
        ]
    }


@app.get("/hooks/info")
async def get_hooks_info():
    """获取 Hook 信息"""
    if not hook_registry:
        return {"error": "Hook 注册表未初始化"}
    
    info = {
        "before_ddl": len(hook_registry.get_hooks(HookTrigger.BEFORE_DDL)),
        "after_ddl": len(hook_registry.get_hooks(HookTrigger.AFTER_DDL)),
        "before_dml": len(hook_registry.get_hooks(HookTrigger.BEFORE_DML)),
        "after_dml": len(hook_registry.get_hooks(HookTrigger.AFTER_DML)),
    }
    return info


@app.get("/hooks/execute")
async def execute_hooks():
    """手动执行 Hook"""
    if not hook_registry:
        return {"error": "Hook 注册表未初始化"}
    
    results = {}
    
    # 执行各个阶段的 Hook
    for trigger in HookTrigger:
        result = await hook_registry.execute_hooks(trigger, context={"test": True})
        results[trigger.value] = result
    
    return {
        "message": "Hook 执行完成",
        "results": results
    }


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("FastAPIEasy Hook 系统示例")
    print("=" * 60)
    print()
    print("启动应用...")
    print()
    print("API 端点:")
    print("  GET /                - 根端点")
    print("  GET /hooks/info      - 获取 Hook 信息")
    print("  GET /hooks/execute   - 手动执行 Hook")
    print()
    print("访问 http://localhost:8000/docs 查看 API 文档")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
