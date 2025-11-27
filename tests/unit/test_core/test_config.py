"""Tests for configuration system"""

import pytest
from fastapi_easy.core.config import CRUDConfig


class TestCRUDConfig:
    """Test CRUD configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = CRUDConfig()
        
        assert config.enable_filters is True
        assert config.enable_sorters is True
        assert config.enable_pagination is True
        assert config.enable_soft_delete is False
        assert config.enable_audit is False
        assert config.enable_bulk_operations is False
        assert config.default_limit == 10
        assert config.max_limit == 100
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = CRUDConfig(
            enable_filters=False,
            default_limit=20,
            max_limit=200,
        )
        
        assert config.enable_filters is False
        assert config.default_limit == 20
        assert config.max_limit == 200
    
    def test_config_validation_invalid_default_limit(self):
        """Test validation with invalid default_limit"""
        config = CRUDConfig(default_limit=-1)
        
        with pytest.raises(ValueError, match="default_limit must be greater than 0"):
            config.validate()
    
    def test_config_validation_invalid_max_limit(self):
        """Test validation with invalid max_limit"""
        config = CRUDConfig(max_limit=0)
        
        with pytest.raises(ValueError, match="max_limit must be greater than 0"):
            config.validate()
    
    def test_config_validation_default_greater_than_max(self):
        """Test validation when default_limit > max_limit"""
        config = CRUDConfig(default_limit=200, max_limit=100)
        
        with pytest.raises(ValueError, match="default_limit cannot be greater than max_limit"):
            config.validate()
    
    def test_config_validation_success(self):
        """Test successful validation"""
        config = CRUDConfig(
            default_limit=10,
            max_limit=100,
        )
        
        # Should not raise
        config.validate()
    
    def test_config_metadata(self):
        """Test metadata storage"""
        config = CRUDConfig(metadata={"version": "1.0"})
        
        assert config.metadata["version"] == "1.0"
    
    def test_config_soft_delete_field(self):
        """Test soft delete field configuration"""
        config = CRUDConfig(
            enable_soft_delete=True,
            deleted_at_field="removed_at",
        )
        
        assert config.enable_soft_delete is True
        assert config.deleted_at_field == "removed_at"
    
    def test_config_filter_fields(self):
        """Test filter fields configuration"""
        config = CRUDConfig(
            filter_fields=["name", "price", "status"],
        )
        
        assert config.filter_fields == ["name", "price", "status"]
    
    def test_config_sort_fields(self):
        """Test sort fields configuration"""
        config = CRUDConfig(
            sort_fields=["created_at", "name"],
            default_sort="created_at",
        )
        
        assert config.sort_fields == ["created_at", "name"]
        assert config.default_sort == "created_at"
