"""Unit tests for soft delete functionality"""

import pytest
from datetime import datetime
from fastapi_easy.core.soft_delete import (
    SoftDeleteMixin,
    SoftDeleteAdapter,
    SoftDeleteConfig,
)


class MockModel(SoftDeleteMixin):
    """Mock model with soft delete support"""
    
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self.is_deleted = False
        self.deleted_at = None


class TestSoftDeleteMixin:
    """Test SoftDeleteMixin functionality"""
    
    def test_soft_delete_marks_as_deleted(self):
        """Test that soft_delete marks record as deleted"""
        item = MockModel(1, "test")
        assert item.is_deleted is False
        assert item.deleted_at is None
        
        item.soft_delete()
        
        assert item.is_deleted is True
        assert item.deleted_at is not None
        assert isinstance(item.deleted_at, datetime)
    
    def test_restore_unmarks_deleted(self):
        """Test that restore unmarks deleted record"""
        item = MockModel(1, "test")
        item.soft_delete()
        
        assert item.is_deleted is True
        
        item.restore()
        
        assert item.is_deleted is False
        assert item.deleted_at is None
    
    def test_is_soft_deleted_returns_correct_status(self):
        """Test is_soft_deleted method"""
        item = MockModel(1, "test")
        
        assert item.is_soft_deleted() is False
        
        item.soft_delete()
        assert item.is_soft_deleted() is True
        
        item.restore()
        assert item.is_soft_deleted() is False
    
    def test_multiple_soft_deletes_and_restores(self):
        """Test multiple soft delete and restore cycles"""
        item = MockModel(1, "test")
        
        # First cycle
        item.soft_delete()
        assert item.is_soft_deleted() is True
        first_deleted_at = item.deleted_at
        
        item.restore()
        assert item.is_soft_deleted() is False
        
        # Second cycle
        item.soft_delete()
        assert item.is_soft_deleted() is True
        assert item.deleted_at > first_deleted_at


class TestSoftDeleteAdapter:
    """Test SoftDeleteAdapter functionality"""
    
    def test_adapter_initialization(self):
        """Test adapter initialization"""
        adapter = SoftDeleteAdapter(MockModel, include_deleted=False)
        
        assert adapter.model == MockModel
        assert adapter.include_deleted is False
    
    def test_adapter_with_include_deleted(self):
        """Test adapter with include_deleted=True"""
        adapter = SoftDeleteAdapter(MockModel, include_deleted=True)
        
        assert adapter.include_deleted is True
    
    def test_get_query_filter_excludes_deleted(self):
        """Test get_query_filter excludes deleted records"""
        adapter = SoftDeleteAdapter(MockModel, include_deleted=False)
        
        filter_expr = adapter.get_query_filter()
        
        assert filter_expr is not None
    
    def test_get_query_filter_includes_deleted(self):
        """Test get_query_filter includes deleted records"""
        adapter = SoftDeleteAdapter(MockModel, include_deleted=True)
        
        filter_expr = adapter.get_query_filter()
        
        assert filter_expr is None
    
    @pytest.mark.asyncio
    async def test_soft_delete_item(self):
        """Test soft deleting an item"""
        adapter = SoftDeleteAdapter(MockModel)
        item = MockModel(1, "test")
        
        result = await adapter.soft_delete(item)
        
        assert result.is_deleted is True
        assert result.deleted_at is not None
    
    @pytest.mark.asyncio
    async def test_restore_item(self):
        """Test restoring a soft-deleted item"""
        adapter = SoftDeleteAdapter(MockModel)
        item = MockModel(1, "test")
        item.soft_delete()
        
        result = await adapter.restore(item)
        
        assert result.is_deleted is False
        assert result.deleted_at is None
    
    @pytest.mark.asyncio
    async def test_permanently_delete_item(self):
        """Test permanently deleting an item"""
        adapter = SoftDeleteAdapter(MockModel)
        item = MockModel(1, "test")
        
        result = await adapter.permanently_delete(item)
        
        assert result == item


class TestSoftDeleteConfig:
    """Test SoftDeleteConfig functionality"""
    
    def test_default_config(self):
        """Test default configuration"""
        config = SoftDeleteConfig()
        
        assert config.enabled is True
        assert config.include_deleted_by_default is False
        assert config.auto_restore_on_update is False
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = SoftDeleteConfig(
            enabled=False,
            include_deleted_by_default=True,
            auto_restore_on_update=True,
        )
        
        assert config.enabled is False
        assert config.include_deleted_by_default is True
        assert config.auto_restore_on_update is True
    
    def test_config_with_partial_args(self):
        """Test configuration with partial arguments"""
        config = SoftDeleteConfig(enabled=False)
        
        assert config.enabled is False
        assert config.include_deleted_by_default is False
        assert config.auto_restore_on_update is False
