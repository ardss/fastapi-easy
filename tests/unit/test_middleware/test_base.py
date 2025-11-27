"""Unit tests for middleware"""

import pytest
from fastapi_easy.middleware import (
    BaseMiddleware,
    ErrorHandlingMiddleware,
    LoggingMiddleware,
    MonitoringMiddleware,
    MiddlewareChain,
)


class MockMiddleware(BaseMiddleware):
    """Mock middleware for testing"""
    
    async def process_request(self, context):
        context["processed_request"] = True
        return context
    
    async def process_response(self, context, response):
        response["processed_response"] = True
        return response


class TestBaseMiddleware:
    """Test BaseMiddleware"""
    
    def test_middleware_initialization(self):
        """Test middleware initialization"""
        middleware = MockMiddleware(name="test")
        
        assert middleware.name == "test"
        assert middleware.enabled is True
    
    def test_middleware_enable_disable(self):
        """Test enabling and disabling middleware"""
        middleware = MockMiddleware()
        
        assert middleware.enabled is True
        
        middleware.disable()
        assert middleware.enabled is False
        
        middleware.enable()
        assert middleware.enabled is True
    
    @pytest.mark.asyncio
    async def test_process_request(self):
        """Test processing request"""
        middleware = MockMiddleware()
        context = {}
        
        result = await middleware.process_request(context)
        
        assert result["processed_request"] is True
    
    @pytest.mark.asyncio
    async def test_process_response(self):
        """Test processing response"""
        middleware = MockMiddleware()
        context = {}
        response = {}
        
        result = await middleware.process_response(context, response)
        
        assert result["processed_response"] is True


class TestErrorHandlingMiddleware:
    """Test ErrorHandlingMiddleware"""
    
    def test_initialization(self):
        """Test error handling middleware initialization"""
        middleware = ErrorHandlingMiddleware()
        
        assert middleware.name == "ErrorHandling"
        assert middleware.error_handlers == {}
    
    @pytest.mark.asyncio
    async def test_process_request(self):
        """Test processing request"""
        middleware = ErrorHandlingMiddleware()
        context = {}
        
        result = await middleware.process_request(context)
        
        assert "errors" in result
        assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_register_handler(self):
        """Test registering error handler"""
        middleware = ErrorHandlingMiddleware()
        
        def handler(error):
            return ValueError("Handled")
        
        middleware.register_handler(ValueError, handler)
        
        assert ValueError in middleware.error_handlers
    
    @pytest.mark.asyncio
    async def test_process_error(self):
        """Test processing error"""
        middleware = ErrorHandlingMiddleware()
        context = {}
        error = ValueError("Test error")
        
        result = await middleware.process_error(context, error)
        
        assert isinstance(result, ValueError)


class TestLoggingMiddleware:
    """Test LoggingMiddleware"""
    
    def test_initialization(self):
        """Test logging middleware initialization"""
        middleware = LoggingMiddleware()
        
        assert middleware.name == "Logging"
        assert middleware.logger is None
    
    @pytest.mark.asyncio
    async def test_process_request(self):
        """Test processing request"""
        middleware = LoggingMiddleware()
        context = {
            "method": "GET",
            "path": "/api/items",
            "params": {},
        }
        
        result = await middleware.process_request(context)
        
        assert result == context
    
    @pytest.mark.asyncio
    async def test_process_response(self):
        """Test processing response"""
        middleware = LoggingMiddleware()
        context = {
            "method": "GET",
            "path": "/api/items",
            "status": 200,
        }
        response = {"data": []}
        
        result = await middleware.process_response(context, response)
        
        assert result == response
    
    @pytest.mark.asyncio
    async def test_process_error(self):
        """Test processing error"""
        middleware = LoggingMiddleware()
        context = {
            "method": "GET",
            "path": "/api/items",
        }
        error = ValueError("Test error")
        
        result = await middleware.process_error(context, error)
        
        assert isinstance(result, ValueError)


class TestMonitoringMiddleware:
    """Test MonitoringMiddleware"""
    
    def test_initialization(self):
        """Test monitoring middleware initialization"""
        middleware = MonitoringMiddleware()
        
        assert middleware.name == "Monitoring"
        assert middleware.request_count == 0
        assert middleware.error_count == 0
        assert middleware.total_time == 0.0
    
    @pytest.mark.asyncio
    async def test_process_request(self):
        """Test processing request"""
        middleware = MonitoringMiddleware()
        context = {}
        
        result = await middleware.process_request(context)
        
        assert middleware.request_count == 1
        assert "start_time" in result
    
    @pytest.mark.asyncio
    async def test_process_response(self):
        """Test processing response"""
        middleware = MonitoringMiddleware()
        context = {"start_time": 0}
        response = {"data": []}
        
        result = await middleware.process_response(context, response)
        
        assert result == response
    
    @pytest.mark.asyncio
    async def test_process_error(self):
        """Test processing error"""
        middleware = MonitoringMiddleware()
        context = {}
        error = ValueError("Test error")
        
        result = await middleware.process_error(context, error)
        
        assert middleware.error_count == 1
        assert isinstance(result, ValueError)
    
    def test_get_stats(self):
        """Test getting statistics"""
        middleware = MonitoringMiddleware()
        middleware.request_count = 10
        middleware.error_count = 2
        middleware.total_time = 5.0
        
        stats = middleware.get_stats()
        
        assert stats["request_count"] == 10
        assert stats["error_count"] == 2
        assert stats["total_time"] == 5.0
        assert stats["avg_time"] == 0.5


class TestMiddlewareChain:
    """Test MiddlewareChain"""
    
    def test_chain_initialization(self):
        """Test middleware chain initialization"""
        chain = MiddlewareChain()
        
        assert chain.middlewares == []
    
    def test_add_middleware(self):
        """Test adding middleware"""
        chain = MiddlewareChain()
        middleware = MockMiddleware()
        
        chain.add(middleware)
        
        assert len(chain.middlewares) == 1
        assert middleware in chain.middlewares
    
    def test_remove_middleware(self):
        """Test removing middleware"""
        chain = MiddlewareChain()
        middleware = MockMiddleware()
        
        chain.add(middleware)
        chain.remove(middleware)
        
        assert len(chain.middlewares) == 0
    
    @pytest.mark.asyncio
    async def test_process_request_chain(self):
        """Test processing request through chain"""
        chain = MiddlewareChain()
        middleware1 = MockMiddleware()
        middleware2 = MockMiddleware()
        
        chain.add(middleware1)
        chain.add(middleware2)
        
        context = {}
        result = await chain.process_request(context)
        
        assert result["processed_request"] is True
    
    @pytest.mark.asyncio
    async def test_process_response_chain(self):
        """Test processing response through chain"""
        chain = MiddlewareChain()
        middleware1 = MockMiddleware()
        middleware2 = MockMiddleware()
        
        chain.add(middleware1)
        chain.add(middleware2)
        
        context = {}
        response = {}
        result = await chain.process_response(context, response)
        
        assert result["processed_response"] is True
    
    @pytest.mark.asyncio
    async def test_process_error_chain(self):
        """Test processing error through chain"""
        chain = MiddlewareChain()
        middleware = ErrorHandlingMiddleware()
        
        chain.add(middleware)
        
        context = {}
        error = ValueError("Test error")
        
        result = await chain.process_error(context, error)
        
        assert isinstance(result, ValueError)
    
    @pytest.mark.asyncio
    async def test_disabled_middleware_skipped(self):
        """Test disabled middleware is skipped"""
        chain = MiddlewareChain()
        middleware = MockMiddleware()
        middleware.disable()
        
        chain.add(middleware)
        
        context = {}
        result = await chain.process_request(context)
        
        assert "processed_request" not in result
