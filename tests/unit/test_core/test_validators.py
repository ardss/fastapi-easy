"""Unit tests for input validators"""

import pytest
from fastapi_easy.core.validators import (
    ValidationError,
    InputValidator,
    FilterValidator,
)


class TestInputValidator:
    """Test InputValidator"""
    
    def test_validate_field_name_valid(self):
        """Test validating valid field names"""
        assert InputValidator.validate_field_name("name") == "name"
        assert InputValidator.validate_field_name("user_id") == "user_id"
        assert InputValidator.validate_field_name("user.name") == "user.name"
    
    def test_validate_field_name_invalid(self):
        """Test validating invalid field names"""
        with pytest.raises(ValidationError):
            InputValidator.validate_field_name("")
        
        with pytest.raises(ValidationError):
            InputValidator.validate_field_name("123field")
        
        with pytest.raises(ValidationError):
            InputValidator.validate_field_name("field-name")
        
        with pytest.raises(ValidationError):
            InputValidator.validate_field_name("field name")
    
    def test_validate_field_name_not_string(self):
        """Test validating non-string field names"""
        with pytest.raises(ValidationError):
            InputValidator.validate_field_name(123)
    
    def test_validate_filter_value_valid(self):
        """Test validating valid filter values"""
        assert InputValidator.validate_filter_value("test") == "test"
        assert InputValidator.validate_filter_value(123) == 123
        assert InputValidator.validate_filter_value(45.67) == 45.67
        assert InputValidator.validate_filter_value(True) is True
    
    def test_validate_filter_value_sql_injection(self):
        """Test detecting SQL injection attempts"""
        with pytest.raises(ValidationError):
            InputValidator.validate_filter_value("'; DROP TABLE users; --")
        
        with pytest.raises(ValidationError):
            InputValidator.validate_filter_value("1' OR '1'='1")
        
        with pytest.raises(ValidationError):
            InputValidator.validate_filter_value("admin' UNION SELECT * FROM users")
    
    def test_validate_filter_value_sql_keywords(self):
        """Test detecting SQL keywords"""
        with pytest.raises(ValidationError):
            InputValidator.validate_filter_value("SELECT * FROM users")
        
        with pytest.raises(ValidationError):
            InputValidator.validate_filter_value("DELETE FROM products")
    
    def test_validate_filter_value_list(self):
        """Test validating list values"""
        result = InputValidator.validate_filter_value(["a", "b", "c"])
        assert result == ["a", "b", "c"]
    
    def test_validate_filter_value_list_with_injection(self):
        """Test detecting SQL injection in list values"""
        with pytest.raises(ValidationError):
            InputValidator.validate_filter_value(["a", "'; DROP TABLE;", "c"])
    
    def test_validate_sort_field(self):
        """Test validating sort field"""
        assert InputValidator.validate_sort_field("name") == "name"
        assert InputValidator.validate_sort_field("-name") == "name"
    
    def test_validate_pagination_params_valid(self):
        """Test validating valid pagination parameters"""
        skip, limit = InputValidator.validate_pagination_params(10, 20)
        assert skip == 10
        assert limit == 20
    
    def test_validate_pagination_params_defaults(self):
        """Test default pagination parameters"""
        skip, limit = InputValidator.validate_pagination_params()
        assert skip == 0
        assert limit == 10
    
    def test_validate_pagination_params_invalid_skip(self):
        """Test invalid skip parameter"""
        with pytest.raises(ValidationError):
            InputValidator.validate_pagination_params(-1, 10)
        
        with pytest.raises(ValidationError):
            InputValidator.validate_pagination_params("10", 10)
    
    def test_validate_pagination_params_invalid_limit(self):
        """Test invalid limit parameter"""
        with pytest.raises(ValidationError):
            InputValidator.validate_pagination_params(0, 0)
        
        with pytest.raises(ValidationError):
            InputValidator.validate_pagination_params(0, 2000)
    
    def test_sanitize_string_valid(self):
        """Test sanitizing valid strings"""
        assert InputValidator.sanitize_string("hello") == "hello"
        assert InputValidator.sanitize_string("hello world") == "hello world"
    
    def test_sanitize_string_with_null_bytes(self):
        """Test removing null bytes"""
        result = InputValidator.sanitize_string("hello\x00world")
        assert result == "helloworld"
    
    def test_sanitize_string_too_long(self):
        """Test string exceeding max length"""
        with pytest.raises(ValidationError):
            InputValidator.sanitize_string("a" * 1001, max_length=1000)


class TestFilterValidator:
    """Test FilterValidator"""
    
    def test_filter_validator_initialization(self):
        """Test filter validator initialization"""
        validator = FilterValidator(allowed_fields=["name", "email"])
        
        assert validator.allowed_fields == ["name", "email"]
    
    def test_validate_filters_valid(self):
        """Test validating valid filters"""
        validator = FilterValidator(allowed_fields=["name", "email"])
        
        filters = {
            "name": {
                "field": "name",
                "operator": "exact",
                "value": "John",
            }
        }
        
        result = validator.validate_filters(filters)
        
        assert result["name"]["field"] == "name"
        assert result["name"]["value"] == "John"
    
    def test_validate_filters_invalid_field(self):
        """Test validating filters with invalid field"""
        validator = FilterValidator(allowed_fields=["name"])
        
        filters = {
            "email": {
                "field": "email",
                "operator": "exact",
                "value": "test@example.com",
            }
        }
        
        with pytest.raises(ValidationError):
            validator.validate_filters(filters)
    
    def test_validate_filters_missing_field(self):
        """Test validating filters with missing field"""
        validator = FilterValidator()
        
        filters = {
            "filter1": {
                "operator": "exact",
                "value": "test",
            }
        }
        
        with pytest.raises(ValidationError):
            validator.validate_filters(filters)
    
    def test_validate_filters_sql_injection(self):
        """Test detecting SQL injection in filters"""
        validator = FilterValidator()
        
        filters = {
            "name": {
                "field": "name",
                "operator": "exact",
                "value": "'; DROP TABLE users; --",
            }
        }
        
        with pytest.raises(ValidationError):
            validator.validate_filters(filters)
    
    def test_validate_filters_no_allowed_fields(self):
        """Test validating filters without field restrictions"""
        validator = FilterValidator()
        
        filters = {
            "name": {
                "field": "name",
                "operator": "exact",
                "value": "John",
            },
            "email": {
                "field": "email",
                "operator": "exact",
                "value": "john@example.com",
            }
        }
        
        result = validator.validate_filters(filters)
        
        assert len(result) == 2
