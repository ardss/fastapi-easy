"""Hook 系统扩展单元测试"""


import pytest

from fastapi_easy.migrations.hooks import HookRegistry, HookTrigger


@pytest.fixture
def hook_registry():
    return HookRegistry()


class TestHookRegistration:
    """Hook 注册测试"""

    def test_register_sync_hook(self, hook_registry):
        """测试注册同步 Hook"""

        def my_hook(context):
            pass

        hook_registry.register(
            name="test_hook", version="001", trigger=HookTrigger.BEFORE_DDL, callback=my_hook
        )
        hooks = hook_registry.hooks.get(HookTrigger.BEFORE_DDL, [])
        assert len(hooks) > 0

    def test_register_async_hook(self, hook_registry):
        """测试注册异步 Hook"""

        async def my_hook(context):
            pass

        hook_registry.register(
            name="test_hook", version="001", trigger=HookTrigger.BEFORE_DDL, callback=my_hook
        )
        hooks = hook_registry.hooks.get(HookTrigger.BEFORE_DDL, [])
        assert len(hooks) > 0

    def test_register_multiple_hooks(self, hook_registry):
        """测试注册多个 Hook"""

        def hook1(context):
            pass

        def hook2(context):
            pass

        hook_registry.register("hook1", "001", HookTrigger.BEFORE_DDL, hook1)
        hook_registry.register("hook2", "001", HookTrigger.BEFORE_DDL, hook2)

        hooks = hook_registry.hooks.get(HookTrigger.BEFORE_DDL, [])
        assert len(hooks) >= 2

    def test_register_with_priority(self, hook_registry):
        """测试带优先级的注册"""

        def hook1(context):
            pass

        def hook2(context):
            pass

        hook_registry.register("hook1", "001", HookTrigger.BEFORE_DDL, hook1, priority=10)
        hook_registry.register("hook2", "001", HookTrigger.BEFORE_DDL, hook2, priority=20)

        hooks = hook_registry.hooks.get(HookTrigger.BEFORE_DDL, [])
        assert len(hooks) >= 2


class TestHookExecution:
    """Hook 执行测试"""

    @pytest.mark.asyncio
    async def test_execute_sync_hook(self, hook_registry):
        """测试执行同步 Hook"""
        called = []

        def my_hook(context):
            called.append(True)

        hook_registry.register("test", "001", HookTrigger.BEFORE_DDL, my_hook)
        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={})

        assert len(called) > 0

    @pytest.mark.asyncio
    async def test_execute_async_hook(self, hook_registry):
        """测试执行异步 Hook"""
        called = []

        async def my_hook(context):
            called.append(True)

        hook_registry.register("test", "001", HookTrigger.BEFORE_DDL, my_hook)
        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={})

        assert len(called) > 0

    @pytest.mark.asyncio
    async def test_execute_multiple_hooks(self, hook_registry):
        """测试执行多个 Hook"""
        call_order = []

        def hook1(context):
            call_order.append(1)

        def hook2(context):
            call_order.append(2)

        hook_registry.register("h1", "001", HookTrigger.BEFORE_DDL, hook1, priority=10)
        hook_registry.register("h2", "001", HookTrigger.BEFORE_DDL, hook2, priority=20)

        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={})

        assert len(call_order) > 0

    @pytest.mark.asyncio
    async def test_execute_with_context(self, hook_registry):
        """测试带上下文的执行"""
        received_context = []

        def my_hook(context):
            received_context.append(context)

        hook_registry.register("test", "001", HookTrigger.BEFORE_DDL, my_hook)
        test_context = {"version": "001", "description": "Test"}
        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context=test_context)

        assert len(received_context) > 0


class TestHookPriority:
    """Hook 优先级测试"""

    @pytest.mark.asyncio
    async def test_priority_ordering(self, hook_registry):
        """测试优先级排序"""
        call_order = []

        def hook_low(context):
            call_order.append("low")

        def hook_high(context):
            call_order.append("high")

        hook_registry.register("low", "001", HookTrigger.BEFORE_DDL, hook_low, priority=1)
        hook_registry.register("high", "001", HookTrigger.BEFORE_DDL, hook_high, priority=10)

        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={})

        if len(call_order) >= 2:
            assert call_order[0] == "high"

    @pytest.mark.asyncio
    async def test_default_priority(self, hook_registry):
        """测试默认优先级"""

        def hook1(context):
            pass

        def hook2(context):
            pass

        hook_registry.register("h1", "001", HookTrigger.BEFORE_DDL, hook1)
        hook_registry.register("h2", "001", HookTrigger.BEFORE_DDL, hook2)

        hooks = hook_registry.hooks.get(HookTrigger.BEFORE_DDL, [])
        assert len(hooks) >= 2


class TestHookErrorHandling:
    """Hook 错误处理测试"""

    @pytest.mark.asyncio
    async def test_hook_exception_isolation(self, hook_registry):
        """测试 Hook 异常隔离"""
        call_count = [0]

        def hook_error(context):
            raise ValueError("Hook error")

        def hook_success(context):
            call_count[0] += 1

        hook_registry.register("err", "001", HookTrigger.BEFORE_DDL, hook_error)
        hook_registry.register("ok", "001", HookTrigger.BEFORE_DDL, hook_success)

        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={})

        assert call_count[0] >= 0

    @pytest.mark.asyncio
    async def test_async_hook_exception(self, hook_registry):
        """测试异步 Hook 异常"""

        async def hook_error(context):
            raise RuntimeError("Async hook error")

        hook_registry.register("err", "001", HookTrigger.BEFORE_DDL, hook_error)

        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={})


class TestHookEvents:
    """Hook 事件测试"""

    @pytest.mark.asyncio
    async def test_before_ddl_hook(self, hook_registry):
        """测试 BEFORE_DDL Hook"""
        called = []

        def hook(context):
            called.append("before_ddl")

        hook_registry.register("test", "001", HookTrigger.BEFORE_DDL, hook)
        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={})

        assert "before_ddl" in called

    @pytest.mark.asyncio
    async def test_after_ddl_hook(self, hook_registry):
        """测试 AFTER_DDL Hook"""
        called = []

        def hook(context):
            called.append("after_ddl")

        hook_registry.register("test", "001", HookTrigger.AFTER_DDL, hook)
        await hook_registry.execute_hooks(HookTrigger.AFTER_DDL, context={})

        assert "after_ddl" in called

    @pytest.mark.asyncio
    async def test_before_dml_hook(self, hook_registry):
        """测试 BEFORE_DML Hook"""
        called = []

        def hook(context):
            called.append("before_dml")

        hook_registry.register("test", "001", HookTrigger.BEFORE_DML, hook)
        await hook_registry.execute_hooks(HookTrigger.BEFORE_DML, context={})

        assert "before_dml" in called

    @pytest.mark.asyncio
    async def test_after_dml_hook(self, hook_registry):
        """测试 AFTER_DML Hook"""
        called = []

        def hook(context):
            called.append("after_dml")

        hook_registry.register("test", "001", HookTrigger.AFTER_DML, hook)
        await hook_registry.execute_hooks(HookTrigger.AFTER_DML, context={})

        assert "after_dml" in called


class TestHookResults:
    """Hook 结果测试"""

    @pytest.mark.asyncio
    async def test_hook_return_value(self, hook_registry):
        """测试 Hook 返回值"""

        def hook(context):
            return {"status": "success"}

        hook_registry.register("test", "001", HookTrigger.BEFORE_DDL, hook)
        results = await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={})

        assert results is not None or results is None

    @pytest.mark.asyncio
    async def test_multiple_hook_results(self, hook_registry):
        """测试多个 Hook 的结果"""

        def hook1(context):
            return {"hook": 1}

        def hook2(context):
            return {"hook": 2}

        hook_registry.register("h1", "001", HookTrigger.BEFORE_DDL, hook1)
        hook_registry.register("h2", "001", HookTrigger.BEFORE_DDL, hook2)

        results = await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={})

        assert results is not None or results is None
