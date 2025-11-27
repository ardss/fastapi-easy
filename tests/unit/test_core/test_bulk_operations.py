"""Unit tests for bulk operations"""

import pytest
from fastapi_easy.core.bulk_operations import (
    BulkOperationResult,
    BulkOperationAdapter,
    BulkOperationConfig,
)


class TestBulkOperationResult:
    """Test BulkOperationResult"""
    
    def test_result_initialization(self):
        """Test result initialization"""
        result = BulkOperationResult(success_count=5, failure_count=2)
        
        assert result.success_count == 5
        assert result.failure_count == 2
        assert result.errors == []
    
    def test_result_with_errors(self):
        """Test result with errors"""
        errors = [{"index": 0, "error": "Invalid data"}]
        result = BulkOperationResult(
            success_count=4,
            failure_count=1,
            errors=errors,
        )
        
        assert result.success_count == 4
        assert result.failure_count == 1
        assert result.errors == errors
    
    def test_result_to_dict(self):
        """Test converting result to dictionary"""
        result = BulkOperationResult(success_count=5, failure_count=2)
        
        result_dict = result.to_dict()
        
        assert result_dict["success_count"] == 5
        assert result_dict["failure_count"] == 2
        assert result_dict["total_count"] == 7
        assert result_dict["errors"] == []
    
    def test_result_to_dict_with_errors(self):
        """Test converting result with errors to dictionary"""
        errors = [{"index": 0, "error": "Invalid data"}]
        result = BulkOperationResult(
            success_count=4,
            failure_count=1,
            errors=errors,
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success_count"] == 4
        assert result_dict["failure_count"] == 1
        assert result_dict["total_count"] == 5
        assert result_dict["errors"] == errors


class MockModel:
    """Mock model for testing"""
    
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockSession:
    """Mock session"""
    
    def __init__(self):
        self.items = []
    
    async def add(self, item):
        self.items.append(item)
    
    async def delete(self, item):
        if item in self.items:
            self.items.remove(item)
    
    async def get(self, model, item_id):
        for item in self.items:
            if hasattr(item, 'id') and item.id == item_id:
                return item
        return None
    
    async def commit(self):
        pass
    
    async def rollback(self):
        pass


class MockSessionFactory:
    """Mock session factory"""
    
    def __init__(self):
        self.session = MockSession()
    
    def __call__(self):
        return self
    
    async def __aenter__(self):
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class TestBulkOperationAdapter:
    """Test BulkOperationAdapter"""
    
    def test_adapter_initialization(self):
        """Test adapter initialization"""
        session_factory = MockSessionFactory()
        adapter = BulkOperationAdapter(MockModel, session_factory)
        
        assert adapter.model == MockModel
        assert adapter.session_factory == session_factory
    
    @pytest.mark.asyncio
    async def test_bulk_create_success(self):
        """Test successful bulk create"""
        session_factory = MockSessionFactory()
        adapter = BulkOperationAdapter(MockModel, session_factory)
        
        items_data = [
            {"id": 1, "name": "item1"},
            {"id": 2, "name": "item2"},
            {"id": 3, "name": "item3"},
        ]
        
        result = await adapter.bulk_create(items_data)
        
        assert result.success_count == 3
        assert result.failure_count == 0
        assert result.errors == []
    
    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(self):
        """Test bulk create with empty list"""
        session_factory = MockSessionFactory()
        adapter = BulkOperationAdapter(MockModel, session_factory)
        
        result = await adapter.bulk_create([])
        
        assert result.success_count == 0
        assert result.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_bulk_update_success(self):
        """Test successful bulk update"""
        session_factory = MockSessionFactory()
        adapter = BulkOperationAdapter(MockModel, session_factory)
        
        # Add some items first
        item1 = MockModel(id=1, name="item1")
        item2 = MockModel(id=2, name="item2")
        session_factory.session.items = [item1, item2]
        
        updates = [
            {"id": 1, "name": "updated1"},
            {"id": 2, "name": "updated2"},
        ]
        
        result = await adapter.bulk_update(updates)
        
        assert result.success_count == 2
        assert result.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_bulk_update_missing_id(self):
        """Test bulk update with missing ID"""
        session_factory = MockSessionFactory()
        adapter = BulkOperationAdapter(MockModel, session_factory)
        
        updates = [
            {"name": "updated1"},  # Missing id
        ]
        
        result = await adapter.bulk_update(updates)
        
        assert result.success_count == 0
        assert result.failure_count == 1
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_bulk_delete_success(self):
        """Test successful bulk delete"""
        session_factory = MockSessionFactory()
        adapter = BulkOperationAdapter(MockModel, session_factory)
        
        # Add some items first
        item1 = MockModel(id=1, name="item1")
        item2 = MockModel(id=2, name="item2")
        session_factory.session.items = [item1, item2]
        
        ids = [1, 2]
        
        result = await adapter.bulk_delete(ids)
        
        assert result.success_count == 2
        assert result.failure_count == 0


class TestBulkOperationConfig:
    """Test BulkOperationConfig"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = BulkOperationConfig()
        
        assert config.enabled is True
        assert config.max_batch_size == 1000
        assert config.transaction_mode == "all_or_nothing"
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = BulkOperationConfig(
            enabled=False,
            max_batch_size=500,
            transaction_mode="partial",
        )
        
        assert config.enabled is False
        assert config.max_batch_size == 500
        assert config.transaction_mode == "partial"
    
    def test_config_with_partial_args(self):
        """Test configuration with partial arguments"""
        config = BulkOperationConfig(max_batch_size=100)
        
        assert config.enabled is True
        assert config.max_batch_size == 100
        assert config.transaction_mode == "all_or_nothing"
