import pytest
import asyncio
from fastapi_easy.migrations.hooks import HookRegistry, HookTrigger

@pytest.fixture
def hook_registry():
    return HookRegistry()

class TestHookBasic:
    def test_register_hook(self, hook_registry):
        def my_hook(context):
            pass
        hook_registry.register('test', '001', HookTrigger.BEFORE_DDL, my_hook)
        hooks = hook_registry.get_hooks(HookTrigger.BEFORE_DDL)
        assert len(hooks) > 0
    
    @pytest.mark.asyncio
    async def test_execute_hook(self, hook_registry):
        called = []
        def my_hook(context):
            called.append(True)
        hook_registry.register('test', '001', HookTrigger.BEFORE_DDL, my_hook)
        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL)
        assert len(called) > 0
    
    @pytest.mark.asyncio
    async def test_async_hook(self, hook_registry):
        called = []
        async def my_hook(context):
            called.append(True)
        hook_registry.register('test', '001', HookTrigger.BEFORE_DDL, my_hook)
        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL)
        assert len(called) > 0
    
    def test_hook_priority(self, hook_registry):
        def h1(c): pass
        def h2(c): pass
        hook_registry.register('h1', '001', HookTrigger.BEFORE_DDL, h1, priority=10)
        hook_registry.register('h2', '001', HookTrigger.BEFORE_DDL, h2, priority=20)
        hooks = hook_registry.get_hooks(HookTrigger.BEFORE_DDL)
        assert len(hooks) >= 2
    
    @pytest.mark.asyncio
    async def test_hook_with_context(self, hook_registry):
        received = []
        def my_hook(context):
            received.append(context)
        hook_registry.register('test', '001', HookTrigger.BEFORE_DDL, my_hook)
        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL, context={'key': 'value'})
        assert len(received) > 0
    
    @pytest.mark.asyncio
    async def test_hook_exception_handling(self, hook_registry):
        def bad_hook(c):
            raise ValueError('test error')
        def good_hook(c):
            pass
        hook_registry.register('bad', '001', HookTrigger.BEFORE_DDL, bad_hook)
        hook_registry.register('good', '001', HookTrigger.BEFORE_DDL, good_hook)
        await hook_registry.execute_hooks(HookTrigger.BEFORE_DDL)
    
    @pytest.mark.asyncio
    async def test_multiple_triggers(self, hook_registry):
        def h1(c): pass
        def h2(c): pass
        hook_registry.register('h1', '001', HookTrigger.BEFORE_DDL, h1)
        hook_registry.register('h2', '001', HookTrigger.AFTER_DDL, h2)
        h1_hooks = hook_registry.get_hooks(HookTrigger.BEFORE_DDL)
        h2_hooks = hook_registry.get_hooks(HookTrigger.AFTER_DDL)
        assert len(h1_hooks) > 0
        assert len(h2_hooks) > 0
