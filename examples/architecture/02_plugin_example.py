"""
插件系统示例

演示如何创建和使用插件。
"""

from typing import Dict, Any, List
from abc import ABC

from src.fastapi_easy.core.interfaces import IPlugin
from src.fastapi_easy.core.plugins import PluginMetadata, PluginManager
from src.fastapi_easy.core.container import DIContainer
from src.fastapi_easy.core.settings import AppSettings


# 1. 创建示例插件
class AuditPlugin(IPlugin):
    """审计插件示例"""

    def __init__(self):
        self.audit_logs: List[Dict[str, Any]] = []

    def get_name(self) -> str:
        return "audit-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    async def initialize(self, context: Dict[str, Any]):
        """初始化插件"""
        container = context["container"]
        config = context.get("config", {})

        # 注册审计服务
        container.register_singleton(AuditService, instance=AuditService(self))

        print(f"Audit plugin initialized with config: {config}")

    async def dispose(self):
        """释放资源"""
        print("Audit plugin disposed")

    def get_dependencies(self) -> List[str]:
        return []

    def log_audit(self, action: str, resource: str, user_id: str = None):
        """记录审计日志"""
        self.audit_logs.append({
            "action": action,
            "resource": resource,
            "user_id": user_id,
            "timestamp": self._get_timestamp()
        })

    def _get_timestamp(self) -> str:
        import datetime
        return datetime.datetime.now().isoformat()


@injectable
class AuditService:
    """审计服务"""

    def __init__(self, plugin: AuditPlugin):
        self.plugin = plugin

    async def log(self, action: str, resource: str, user_id: str = None):
        """记录审计"""
        self.plugin.log_audit(action, resource, user_id)

    async def get_logs(self) -> List[Dict[str, Any]]:
        """获取审计日志"""
        return self.plugin.audit_logs


class CachePlugin(IPlugin):
    """缓存插件示例"""

    def __init__(self):
        self.cache: Dict[str, Any] = {}

    def get_name(self) -> str:
        return "cache-plugin"

    def get_version(self) -> str:
        return "1.0.0"

    async def initialize(self, context: Dict[str, Any]):
        container = context["container"]
        config = context.get("config", {})

        # 注册缓存服务
        container.register_singleton(CacheService, instance=CacheService(self))

        print(f"Cache plugin initialized with config: {config}")

    async def dispose(self):
        """释放资源"""
        print("Cache plugin disposed")

    def get_dependencies(self) -> List[str]:
        return []  # 可选：依赖audit-plugin


@injectable
class CacheService:
    """缓存服务"""

    def __init__(self, plugin: CachePlugin):
        self.plugin = plugin

    async def get(self, key: str) -> Any:
        """获取缓存值"""
        return self.plugin.cache.get(key)

    async def set(self, key: str, value: Any, ttl: int = None) -> None:
        """设置缓存值"""
        self.plugin.cache[key] = value

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self.plugin.cache:
            del self.plugin.cache[key]
            return True
        return False

    async def clear(self) -> None:
        """清空缓存"""
        self.plugin.cache.clear()


# 2. 插件管理示例
async def plugin_demo():
    """插件管理演示"""
    # 创建容器和设置
    container = DIContainer()
    settings = AppSettings.create()

    # 创建插件管理器
    plugin_manager = PluginManager(
        container=container,
        settings=settings
    )

    # 模拟插件目录结构
    # 在实际使用中，插件应该放在单独的目录中

    # 直接加载插件（示例）
    audit_plugin = AuditPlugin()
    cache_plugin = CachePlugin()

    # 手动注册插件（在实际使用中，这应该通过文件系统自动发现）
    await plugin_manager._initialize_plugin(
        plugin_manager._import_plugin_module,
        audit_plugin,
        PluginMetadata(
            name="audit-plugin",
            version="1.0.0",
            description="Audit logging plugin"
        )
    )

    await plugin_manager._initialize_plugin(
        plugin_manager._import_plugin_module,
        cache_plugin,
        PluginMetadata(
            name="cache-plugin",
            version="1.0.0",
            description="Caching plugin"
        )
    )

    print("Plugins loaded successfully")

    # 使用插件服务
    audit_service = container.resolve(AuditService)
    cache_service = container.resolve(CacheService)

    # 测试审计功能
    await audit_service.log("create", "user", user_id="123")
    await audit_service.log("update", "user", user_id="123")
    await audit_service.log("delete", "user", user_id="123")

    logs = await audit_service.get_logs()
    print(f"Audit logs: {len(logs)} entries")
    for log in logs:
        print(f"  - {log}")

    # 测试缓存功能
    await cache_service.set("user:123", {"name": "John", "age": 30})
    cached_user = await cache_service.get("user:123")
    print(f"Cached user: {cached_user}")

    await cache_service.delete("user:123")
    deleted_user = await cache_service.get("user:123")
    print(f"User after deletion: {deleted_user}")


# 3. 创建FastAPI应用与插件集成
def create_app_with_plugins():
    """创建带插件支持的应用"""
    from fastapi import FastAPI, Depends
    from src.fastapi_easy.core.factory import ApplicationFactory
    from src.fastapi_easy.core.settings import init_settings

    # 初始化设置
    settings = AppSettings.create(app_name="Plugin Demo App")
    init_settings(settings)

    # 创建应用工厂
    factory = ApplicationFactory(settings)

    # 加载插件
    plugin_manager = PluginManager(
        container=factory.container,
        settings=settings
    )

    # 在实际使用中，这里应该扫描插件目录
    # await plugin_manager.load_all_plugins(["plugins/"])

    # 创建FastAPI应用
    app = factory.create_app()

    # 使用插件服务的API端点
    @app.get("/audit-logs")
    async def get_audit_logs(audit_service: AuditService = Depends()):
        logs = await audit_service.get_logs()
        return {"logs": logs, "count": len(logs)}

    @app.post("/cache/{key}")
    async def set_cache(key: str, value: Any, cache_service: CacheService = Depends()):
        await cache_service.set(key, value)
        return {"message": f"Cache set for key: {key}"}

    @app.get("/cache/{key}")
    async def get_cache(key: str, cache_service: CacheService = Depends()):
        value = await cache_service.get(key)
        if value is None:
            return {"key": key, "value": None, "found": False}
        return {"key": key, "value": value, "found": True}

    return app


if __name__ == "__main__":
    import uvicorn

    # 运行插件演示
    import asyncio
    asyncio.run(plugin_demo())

    # 运行Web应用
    app = create_app_with_plugins()
    uvicorn.run(app, host="0.0.0.0", port=8001)