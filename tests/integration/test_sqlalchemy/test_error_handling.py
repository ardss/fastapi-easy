"""SQLAlchemy adapter error handling tests"""

import pytest
from fastapi_easy.core.errors import AppError, ErrorCode


@pytest.mark.asyncio
class TestSQLAlchemyFilterValidation:
    """Test SQLAlchemy filter validation"""
    
    async def test_filter_invalid_field_name(self, sqlalchemy_adapter):
        """Test filter with invalid field name"""
        filters = {
            "invalid": {"field": None, "operator": "exact", "value": "test"}
        }
        
        with pytest.raises(AppError) as exc_info:
            await sqlalchemy_adapter.get_all(filters, {}, {"skip": 0, "limit": 10})
        
        assert "Invalid field name" in str(exc_info.value)
    
    async def test_filter_invalid_operator(self, sqlalchemy_adapter):
        """Test filter with invalid operator"""
        filters = {
            "test": {"field": "name", "operator": "invalid_op", "value": "test"}
        }
        
        with pytest.raises(AppError) as exc_info:
            await sqlalchemy_adapter.get_all(filters, {}, {"skip": 0, "limit": 10})
        
        assert "Unsupported operator" in str(exc_info.value)
    
    async def test_filter_none_value(self, sqlalchemy_adapter):
        """Test filter with None value"""
        filters = {
            "test": {"field": "name", "operator": "exact", "value": None}
        }
        
        with pytest.raises(AppError) as exc_info:
            await sqlalchemy_adapter.get_all(filters, {}, {"skip": 0, "limit": 10})
        
        assert "Filter value cannot be None" in str(exc_info.value)
    
    async def test_filter_field_not_found(self, sqlalchemy_adapter):
        """Test filter with non-existent field"""
        filters = {
            "test": {"field": "nonexistent_field", "operator": "exact", "value": "test"}
        }
        
        with pytest.raises(AppError) as exc_info:
            await sqlalchemy_adapter.get_all(filters, {}, {"skip": 0, "limit": 10})
        
        assert "Field not found" in str(exc_info.value)
    
    async def test_filter_non_dict_value(self, sqlalchemy_adapter):
        """Test filter with non-dict value (should be skipped)"""
        filters = {
            "test": "not a dict"
        }
        
        # Should not raise, just skip the invalid filter
        items = await sqlalchemy_adapter.get_all(filters, {}, {"skip": 0, "limit": 10})
        assert isinstance(items, list)
    
    async def test_count_with_invalid_filter(self, sqlalchemy_adapter):
        """Test count with invalid filter"""
        filters = {
            "test": {"field": "nonexistent_field", "operator": "exact", "value": "test"}
        }
        
        with pytest.raises(AppError) as exc_info:
            await sqlalchemy_adapter.count(filters)
        
        assert "Field not found" in str(exc_info.value)
