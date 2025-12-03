"""
迁移 Hook 系统测试
"""

import asyncio

import pytest

from fastapi_easy.migrations.hooks import (
    HookRegistry,
    HookTrigger,
    get_hook_registry,
    migration_hook,
    register_migration_hook,
)


class TestHookRegistry:
    """Hook 注册表测试"""

    def test_register_hook(self):
        """测试注册 Hook"""
        registry = HookRegistry()

        def my_hook(context):
            return {"status": "ok"}

        hook = registry.register(
            name="test_hook",
            version="1.0.0",
            trigger=HookTrigger.BEFORE_DDL,
            callback=my_hook,
            priority=10,
        )

        assert hook.name == "test_hook"
        assert hook.version == "1.0.0"
        assert hook.priority == 10
        assert not hook.is_async

    def test_get_hooks(self):
        """测试获取 Hook"""
        registry = HookRegistry()

        def hook1(context):
            return "hook1"

        def hook2(context):
            return "hook2"

        registry.register("hook1", "1.0.0", HookTrigger.BEFORE_DDL, hook1, priority=10)
        registry.register("hook2", "1.0.0", HookTrigger.BEFORE_DDL, hook2, priority=5)

        hooks = registry.get_hooks(HookTrigger.BEFORE_DDL)
        assert len(hooks) == 2
        # 优先级高的在前
        assert hooks[0].name == "hook1"
        assert hooks[1].name == "hook2"

    def test_get_hooks_for_version(self):
        """测试获取特定版本的 Hook"""
        registry = HookRegistry()

        def hook1(context):
            return "hook1"

        def hook2(context):
            return "hook2"

        registry.register("hook1", "1.0.0", HookTrigger.BEFORE_DDL, hook1)
        registry.register("hook2", "2.0.0", HookTrigger.BEFORE_DDL, hook2)

        hooks = registry.get_hooks_for_version("1.0.0", HookTrigger.BEFORE_DDL)
        assert len(hooks) == 1
        assert hooks[0].name == "hook1"

    @pytest.mark.asyncio
    async def test_execute_hooks_sync(self):
        """测试执行同步 Hook"""
        registry = HookRegistry()

        def my_hook(context):
            context["executed"] = True
            return {"status": "ok"}

        registry.register(
            "test_hook",
            "1.0.0",
            HookTrigger.BEFORE_DDL,
            my_hook,
        )

        context = {}
        results = await registry.execute_hooks(HookTrigger.BEFORE_DDL, context=context)

        assert context["executed"] is True
        assert results["test_hook"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_execute_hooks_async(self):
        """测试执行异步 Hook"""
        registry = HookRegistry()

        async def my_hook(context):
            await asyncio.sleep(0.01)
            context["executed"] = True
            return {"status": "ok"}

        registry.register(
            "test_hook",
            "1.0.0",
            HookTrigger.BEFORE_DDL,
            my_hook,
        )

        context = {}
        results = await registry.execute_hooks(HookTrigger.BEFORE_DDL, context=context)

        assert context["executed"] is True
        assert results["test_hook"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_execute_hooks_with_error(self):
        """测试 Hook 错误隔离"""
        registry = HookRegistry()

        def hook1(context):
            raise ValueError("Hook 1 error")

        def hook2(context):
            return {"status": "ok"}

        registry.register("hook1", "1.0.0", HookTrigger.BEFORE_DDL, hook1, priority=10)
        registry.register("hook2", "1.0.0", HookTrigger.BEFORE_DDL, hook2, priority=5)

        results = await registry.execute_hooks(HookTrigger.BEFORE_DDL)

        # Hook 1 失败
        assert "error" in results["hook1"]
        # Hook 2 成功
        assert results["hook2"]["status"] == "ok"

    @pytest.mark.asyncio
    async def test_execute_hooks_for_version(self):
        """测试执行特定版本的 Hook"""
        registry = HookRegistry()

        def hook1(context):
            return "hook1"

        def hook2(context):
            return "hook2"

        registry.register("hook1", "1.0.0", HookTrigger.BEFORE_DDL, hook1)
        registry.register("hook2", "2.0.0", HookTrigger.BEFORE_DDL, hook2)

        results = await registry.execute_hooks(HookTrigger.BEFORE_DDL, version="1.0.0")

        assert "hook1" in results
        assert "hook2" not in results

    def test_get_results(self):
        """测试获取 Hook 执行结果"""
        registry = HookRegistry()

        def my_hook(context):
            return {"status": "ok"}

        registry.register(
            "test_hook",
            "1.0.0",
            HookTrigger.BEFORE_DDL,
            my_hook,
        )

        # 设置结果
        registry._hook_results["before_ddl"] = {"test_hook": {"status": "ok"}}

        results = registry.get_results(HookTrigger.BEFORE_DDL)
        assert results["test_hook"]["status"] == "ok"

    def test_clear_hooks(self):
        """测试清空 Hook"""
        registry = HookRegistry()

        def my_hook(context):
            return "ok"

        registry.register(
            "test_hook",
            "1.0.0",
            HookTrigger.BEFORE_DDL,
            my_hook,
        )

        assert len(registry.get_hooks(HookTrigger.BEFORE_DDL)) == 1

        registry.clear_hooks(HookTrigger.BEFORE_DDL)

        assert len(registry.get_hooks(HookTrigger.BEFORE_DDL)) == 0


class TestMigrationHookDecorator:
    """@migration_hook 装饰器测试"""

    def test_decorator_registration(self):
        """测试装饰器注册"""
        # 创建新的注册表实例
        test_registry = HookRegistry()
        migration_hook.set_registry(test_registry)

        @migration_hook(
            version="1.0.0",
            trigger=HookTrigger.BEFORE_DDL,
            priority=10,
            description="Test hook",
        )
        def my_hook(context):
            return "ok"

        registry = migration_hook.get_registry()
        hooks = registry.get_hooks(HookTrigger.BEFORE_DDL)

        assert len(hooks) > 0
        assert any(h.name == "my_hook" for h in hooks)

    def test_decorator_with_async(self):
        """测试异步装饰器"""

        @migration_hook(
            version="1.0.0",
            trigger=HookTrigger.AFTER_DDL,
        )
        async def my_async_hook(context):
            return "ok"

        registry = migration_hook.get_registry()
        hooks = registry.get_hooks(HookTrigger.AFTER_DDL)

        async_hooks = [h for h in hooks if h.name == "my_async_hook"]
        assert len(async_hooks) > 0
        assert async_hooks[0].is_async


class TestRegisterMigrationHook:
    """register_migration_hook 函数测试"""

    def test_register_function(self):
        """测试直接注册函数"""

        def my_hook(context):
            return "ok"

        hook = register_migration_hook(
            version="1.0.0",
            trigger=HookTrigger.BEFORE_DML,
            callback=my_hook,
            priority=5,
        )

        assert hook.name == "my_hook"
        assert hook.version == "1.0.0"
        assert hook.priority == 5

        registry = get_hook_registry()
        hooks = registry.get_hooks(HookTrigger.BEFORE_DML)
        assert any(h.name == "my_hook" for h in hooks)
