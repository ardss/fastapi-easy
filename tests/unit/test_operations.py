"""Unit tests for operations module"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi_easy.operations.get_all import GetAllOperation
from fastapi_easy.operations.get_one import GetOneOperation
from fastapi_easy.operations.create import CreateOperation
from fastapi_easy.operations.update import UpdateOperation
from fastapi_easy.operations.delete_one import DeleteOneOperation
from fastapi_easy.operations.delete_all import DeleteAllOperation


class TestGetAllOperation:
    """Test GetAllOperation operation"""
    
    @pytest.mark.asyncio
    async def test_operation_properties(self):
        """Test operation properties"""
        operation = GetAllOperation()
        
        assert operation.name == "get_all"
        assert operation.method == "GET"
    
    @pytest.mark.asyncio
    async def test_before_execute(self):
        """Test before execute hook"""
        operation = GetAllOperation()
        context = MagicMock()
        
        # Should not raise
        await operation.before_execute(context)


class TestGetOneOperation:
    """Test GetOneOperation operation"""
    
    @pytest.mark.asyncio
    async def test_operation_properties(self):
        """Test operation properties"""
        operation = GetOneOperation()
        
        assert operation.name == "get_one"
        assert operation.method == "GET"


class TestCreateOperation:
    """Test CreateOperation operation"""
    
    @pytest.mark.asyncio
    async def test_operation_properties(self):
        """Test operation properties"""
        operation = CreateOperation()
        
        assert operation.name == "create"
        assert operation.method == "POST"


class TestUpdateOperation:
    """Test UpdateOperation operation"""
    
    @pytest.mark.asyncio
    async def test_operation_properties(self):
        """Test operation properties"""
        operation = UpdateOperation()
        
        assert operation.name == "update"
        assert operation.method == "PUT"


class TestDeleteOneOperation:
    """Test DeleteOneOperation operation"""
    
    @pytest.mark.asyncio
    async def test_operation_properties(self):
        """Test operation properties"""
        operation = DeleteOneOperation()
        
        assert operation.name == "delete_one"
        assert operation.method == "DELETE"


class TestDeleteAllOperation:
    """Test DeleteAllOperation operation"""
    
    @pytest.mark.asyncio
    async def test_operation_properties(self):
        """Test operation properties"""
        operation = DeleteAllOperation()
        
        assert operation.name == "delete_all"
        assert operation.method == "DELETE"
