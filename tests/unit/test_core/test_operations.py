"""Tests for operation system"""

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi_easy.core.operations import Operation, OperationRegistry
from fastapi_easy.core.hooks import ExecutionContext


class MockOperation(Operation):
    """Mock operation for testing"""
    
    name = "test_operation"
    method = "GET"
    path = "/test"
    
    async def before_execute(self, context: ExecutionContext) -> None:
        """Before execute hook"""
        pass
    
    async def execute(self, context: ExecutionContext):
        """Execute operation"""
        return {"result": "success"}
    
    async def after_execute(self, context: ExecutionContext):
        """After execute hook"""
        return context.result


class TestOperationRegistry:
    """Test operation registry"""
    
    def test_registry_creation(self):
        """Test creating operation registry"""
        registry = OperationRegistry()
        
        assert registry.operations == {}
    
    def test_register_operation(self):
        """Test registering an operation"""
        registry = OperationRegistry()
        operation = MockOperation()
        
        registry.register(operation)
        
        assert "test_operation" in registry.operations
        assert registry.operations["test_operation"] == operation
    
    def test_register_multiple_operations(self):
        """Test registering multiple operations"""
        registry = OperationRegistry()
        op1 = MockOperation()
        op2 = MockOperation()
        op2.name = "test_operation_2"
        
        registry.register(op1)
        registry.register(op2)
        
        assert len(registry.operations) == 2
    
    def test_unregister_operation(self):
        """Test unregistering an operation"""
        registry = OperationRegistry()
        operation = MockOperation()
        
        registry.register(operation)
        registry.unregister("test_operation")
        
        assert "test_operation" not in registry.operations
    
    def test_get_operation(self):
        """Test getting operation by name"""
        registry = OperationRegistry()
        operation = MockOperation()
        
        registry.register(operation)
        retrieved = registry.get("test_operation")
        
        assert retrieved == operation
    
    def test_get_non_existent_operation(self):
        """Test getting non-existent operation"""
        registry = OperationRegistry()
        
        result = registry.get("non_existent")
        
        assert result is None
    
    def test_get_all_operations(self):
        """Test getting all operations"""
        registry = OperationRegistry()
        op1 = MockOperation()
        op2 = MockOperation()
        op2.name = "test_operation_2"
        
        registry.register(op1)
        registry.register(op2)
        
        all_ops = registry.get_all()
        
        assert len(all_ops) == 2
        assert "test_operation" in all_ops
        assert "test_operation_2" in all_ops
    
    @pytest.mark.asyncio
    async def test_execute_operation(self):
        """Test executing an operation"""
        registry = OperationRegistry()
        operation = MockOperation()
        registry.register(operation)
        
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
        )
        
        result = await registry.execute("test_operation", context)
        
        assert result == {"result": "success"}
        assert context.result == {"result": "success"}
    
    @pytest.mark.asyncio
    async def test_execute_non_existent_operation(self):
        """Test executing non-existent operation"""
        registry = OperationRegistry()
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
        )
        
        with pytest.raises(ValueError, match="Operation 'non_existent' not found"):
            await registry.execute("non_existent", context)
    
    @pytest.mark.asyncio
    async def test_operation_lifecycle(self):
        """Test operation lifecycle (before, execute, after)"""
        
        class TrackingOperation(Operation):
            name = "tracking"
            method = "POST"
            path = "/track"
            
            def __init__(self):
                self.before_called = False
                self.execute_called = False
                self.after_called = False
            
            async def before_execute(self, context: ExecutionContext) -> None:
                self.before_called = True
            
            async def execute(self, context: ExecutionContext):
                self.execute_called = True
                return {"data": "result"}
            
            async def after_execute(self, context: ExecutionContext):
                self.after_called = True
                return context.result
        
        registry = OperationRegistry()
        operation = TrackingOperation()
        registry.register(operation)
        
        context = ExecutionContext(
            schema="ItemSchema",
            adapter="MockAdapter",
            request="MockRequest",
        )
        
        result = await registry.execute("tracking", context)
        
        assert operation.before_called is True
        assert operation.execute_called is True
        assert operation.after_called is True
        assert result == {"data": "result"}
