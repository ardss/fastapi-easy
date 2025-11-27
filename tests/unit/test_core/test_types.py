"""Unit tests for type definitions"""

import pytest
from typing import Any, Dict, List, Optional
from fastapi_easy.core.types import (
    FilterDict,
    SortDict,
    PaginationDict,
    ResponseData,
    ErrorResponse,
    CreateData,
    UpdateData,
    FilterValue,
    SortValue,
    SkipLimit,
)


class TestTypeAliases:
    """Test type aliases"""
    
    def test_filter_dict_type(self):
        """Test FilterDict type alias"""
        filter_dict: FilterDict = {
            "name": "test",
            "price__gt": 100,
        }
        
        assert isinstance(filter_dict, dict)
        assert "name" in filter_dict
    
    def test_sort_dict_type(self):
        """Test SortDict type alias"""
        sort_dict: SortDict = {
            "name": "asc",
            "price": "desc",
        }
        
        assert isinstance(sort_dict, dict)
        assert sort_dict["name"] == "asc"
    
    def test_pagination_dict_type(self):
        """Test PaginationDict type alias"""
        pagination: PaginationDict = {
            "skip": 0,
            "limit": 10,
        }
        
        assert isinstance(pagination, dict)
        assert pagination["skip"] == 0
        assert pagination["limit"] == 10
    
    def test_response_data_type(self):
        """Test ResponseData type alias"""
        response1: ResponseData = {"id": 1, "name": "test"}
        response2: ResponseData = [{"id": 1}, {"id": 2}]
        response3: ResponseData = "success"
        
        assert isinstance(response1, dict)
        assert isinstance(response2, list)
        assert isinstance(response3, str)
    
    def test_error_response_type(self):
        """Test ErrorResponse type alias"""
        error: ErrorResponse = {
            "error": "Not found",
            "code": 404,
            "details": {"reason": "Resource not found"},
        }
        
        assert isinstance(error, dict)
        assert error["code"] == 404
    
    def test_create_data_type(self):
        """Test CreateData type alias"""
        data: CreateData = {
            "name": "test",
            "email": "test@example.com",
        }
        
        assert isinstance(data, dict)
        assert data["name"] == "test"
    
    def test_update_data_type(self):
        """Test UpdateData type alias"""
        data: UpdateData = {
            "name": "updated",
        }
        
        assert isinstance(data, dict)
        assert data["name"] == "updated"
    
    def test_filter_value_type(self):
        """Test FilterValue type alias"""
        value1: FilterValue = "test"
        value2: FilterValue = 100
        value3: FilterValue = 45.67
        value4: FilterValue = True
        value5: FilterValue = ["a", "b", "c"]
        value6: FilterValue = None
        
        assert isinstance(value1, str)
        assert isinstance(value2, int)
        assert isinstance(value3, float)
        assert isinstance(value4, bool)
        assert isinstance(value5, list)
        assert value6 is None
    
    def test_sort_value_type(self):
        """Test SortValue type alias"""
        sort1: SortValue = "name"
        sort2: SortValue = "-price"
        
        assert isinstance(sort1, str)
        assert isinstance(sort2, str)
    
    def test_skip_limit_type(self):
        """Test SkipLimit type alias"""
        skip_limit: SkipLimit = (0, 10)
        
        assert isinstance(skip_limit, tuple)
        assert len(skip_limit) == 2
        assert skip_limit[0] == 0
        assert skip_limit[1] == 10


class TestProtocols:
    """Test protocol definitions"""
    
    def test_orm_protocol(self):
        """Test ORM protocol"""
        from fastapi_easy.core.types import ORM
        
        class MockORM:
            id: int
            
            def __init__(self, id: int = 1):
                self.id = id
        
        orm = MockORM()
        assert hasattr(orm, "id")
    
    def test_adapter_protocol(self):
        """Test Adapter protocol"""
        from fastapi_easy.core.types import Adapter
        
        class MockAdapter:
            async def create(self, data):
                return {"id": 1, **data}
            
            async def get_one(self, pk):
                return {"id": pk}
            
            async def get_all(self, filters=None, sorts=None, pagination=None):
                return [{"id": 1}]
            
            async def update(self, pk, data):
                return {"id": pk, **data}
            
            async def delete_one(self, pk):
                return {"id": pk}
            
            async def delete_all(self, filters=None):
                return 1
            
            async def count(self, filters=None):
                return 1
        
        adapter = MockAdapter()
        assert hasattr(adapter, "create")
        assert hasattr(adapter, "get_one")
        assert hasattr(adapter, "get_all")
    
    def test_operation_protocol(self):
        """Test Operation protocol"""
        from fastapi_easy.core.types import Operation
        
        class MockOperation:
            async def execute(self, *args, **kwargs):
                return {"result": "success"}
        
        op = MockOperation()
        assert hasattr(op, "execute")
    
    def test_hook_protocol(self):
        """Test Hook protocol"""
        from fastapi_easy.core.types import Hook
        
        class MockHook:
            async def execute(self, context):
                return context
        
        hook = MockHook()
        assert hasattr(hook, "execute")
    
    def test_validator_protocol(self):
        """Test Validator protocol"""
        from fastapi_easy.core.types import Validator
        
        class MockValidator:
            def validate(self, value):
                return value
        
        validator = MockValidator()
        assert hasattr(validator, "validate")
    
    def test_formatter_protocol(self):
        """Test Formatter protocol"""
        from fastapi_easy.core.types import Formatter
        
        class MockFormatter:
            def format(self, data):
                return data
        
        formatter = MockFormatter()
        assert hasattr(formatter, "format")
    
    def test_cache_protocol(self):
        """Test Cache protocol"""
        from fastapi_easy.core.types import Cache
        
        class MockCache:
            async def get(self, key):
                return None
            
            async def set(self, key, value, ttl=None):
                pass
            
            async def delete(self, key):
                pass
            
            async def clear(self):
                pass
        
        cache = MockCache()
        assert hasattr(cache, "get")
        assert hasattr(cache, "set")
        assert hasattr(cache, "delete")
        assert hasattr(cache, "clear")
    
    def test_logger_protocol(self):
        """Test Logger protocol"""
        from fastapi_easy.core.types import Logger
        
        class MockLogger:
            def debug(self, message, extra_fields=None):
                pass
            
            def info(self, message, extra_fields=None):
                pass
            
            def warning(self, message, extra_fields=None):
                pass
            
            def error(self, message, extra_fields=None, exception=None):
                pass
        
        logger = MockLogger()
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
    
    def test_permission_checker_protocol(self):
        """Test PermissionChecker protocol"""
        from fastapi_easy.core.types import PermissionChecker
        
        class MockPermissionChecker:
            def check_permission(self, context, permission):
                pass
        
        checker = MockPermissionChecker()
        assert hasattr(checker, "check_permission")
    
    def test_audit_logger_protocol(self):
        """Test AuditLogger protocol"""
        from fastapi_easy.core.types import AuditLogger
        
        class MockAuditLogger:
            def log(self, entity_type, entity_id, action, user_id=None, changes=None):
                pass
        
        audit_logger = MockAuditLogger()
        assert hasattr(audit_logger, "log")
