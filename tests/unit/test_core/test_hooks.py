"""Tests for hook system"""

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi_easy.core.hooks import HookRegistry, ExecutionContext


class TestExecutionContext:
    """Test execution context"""
    
    def test_context_creation(self):
        """Test creating execution context"""
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
        )
        
        assert context.schema == "ItemSchema"
        assert context.adapter == "MockAdapter"
        assert context.request == "MockRequest"
        assert context.user is None
        assert context.filters == {}
        assert context.sorts == {}
        assert context.pagination == {}
        assert context.data is None
        assert context.result is None
    
    def test_context_with_user(self):
        """Test context with user"""
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
            user={"id": 1, "username": "admin"},
        )
        
        assert context.user["id"] == 1
        assert context.user["username"] == "admin"
    
    def test_context_with_filters_and_sorts(self):
        """Test context with filters and sorts"""
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
            filters={"name": "apple"},
            sorts={"price": "desc"},
            pagination={"skip": 0, "limit": 10},
        )
        
        assert context.filters["name"] == "apple"
        assert context.sorts["price"] == "desc"
        assert context.pagination["limit"] == 10


class TestHookRegistry:
    """Test hook registry"""
    
    def test_hook_registry_creation(self):
        """Test creating hook registry"""
        registry = HookRegistry()
        
        assert registry.hooks == {}
    
    def test_register_hook(self):
        """Test registering a hook"""
        registry = HookRegistry()
        callback = Mock()
        
        registry.register("before_create", callback)
        
        assert "before_create" in registry.hooks
        assert callback in registry.hooks["before_create"]
    
    def test_register_multiple_hooks(self):
        """Test registering multiple hooks for same event"""
        registry = HookRegistry()
        callback1 = Mock()
        callback2 = Mock()
        
        registry.register("before_create", callback1)
        registry.register("before_create", callback2)
        
        assert len(registry.hooks["before_create"]) == 2
        assert callback1 in registry.hooks["before_create"]
        assert callback2 in registry.hooks["before_create"]
    
    def test_register_invalid_event(self):
        """Test registering hook with invalid event"""
        registry = HookRegistry()
        callback = Mock()
        
        with pytest.raises(ValueError, match="Unsupported hook event"):
            registry.register("invalid_event", callback)
    
    def test_unregister_hook(self):
        """Test unregistering a hook"""
        registry = HookRegistry()
        callback = Mock()
        
        registry.register("before_create", callback)
        registry.unregister("before_create", callback)
        
        assert callback not in registry.hooks.get("before_create", [])
    
    def test_get_hooks(self):
        """Test getting hooks for an event"""
        registry = HookRegistry()
        callback1 = Mock()
        callback2 = Mock()
        
        registry.register("before_create", callback1)
        registry.register("before_create", callback2)
        
        hooks = registry.get_hooks("before_create")
        
        assert len(hooks) == 2
        assert callback1 in hooks
        assert callback2 in hooks
    
    def test_get_hooks_empty(self):
        """Test getting hooks for non-existent event"""
        registry = HookRegistry()
        
        hooks = registry.get_hooks("before_create")
        
        assert hooks == []
    
    def test_get_all_hooks(self):
        """Test getting all hooks"""
        registry = HookRegistry()
        callback1 = Mock()
        callback2 = Mock()
        
        registry.register("before_create", callback1)
        registry.register("after_create", callback2)
        
        all_hooks = registry.get_all()
        
        assert "before_create" in all_hooks
        assert "after_create" in all_hooks
    
    @pytest.mark.asyncio
    async def test_trigger_sync_hook(self):
        """Test triggering synchronous hook"""
        registry = HookRegistry()
        callback = Mock()
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
        )
        
        registry.register("before_create", callback)
        await registry.trigger("before_create", context)
        
        callback.assert_called_once_with(context)
    
    @pytest.mark.asyncio
    async def test_trigger_async_hook(self):
        """Test triggering asynchronous hook"""
        registry = HookRegistry()
        callback = AsyncMock()
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
        )
        
        registry.register("before_create", callback)
        await registry.trigger("before_create", context)
        
        callback.assert_called_once_with(context)
    
    @pytest.mark.asyncio
    async def test_trigger_multiple_hooks(self):
        """Test triggering multiple hooks"""
        registry = HookRegistry()
        callback1 = Mock()
        callback2 = AsyncMock()
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
        )
        
        registry.register("before_create", callback1)
        registry.register("before_create", callback2)
        await registry.trigger("before_create", context)
        
        callback1.assert_called_once()
        callback2.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trigger_non_existent_event(self):
        """Test triggering non-existent event"""
        registry = HookRegistry()
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
        )
        
        # Should not raise
        await registry.trigger("non_existent_event", context)
    
    def test_clear_specific_event(self):
        """Test clearing hooks for specific event"""
        registry = HookRegistry()
        callback1 = Mock()
        callback2 = Mock()
        
        registry.register("before_create", callback1)
        registry.register("after_create", callback2)
        registry.clear("before_create")
        
        assert registry.get_hooks("before_create") == []
        assert callback2 in registry.get_hooks("after_create")
    
    def test_clear_all_hooks(self):
        """Test clearing all hooks"""
        registry = HookRegistry()
        callback1 = Mock()
        callback2 = Mock()
        
        registry.register("before_create", callback1)
        registry.register("after_create", callback2)
        registry.clear()
        
        assert registry.hooks == {}
