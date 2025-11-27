"""Unit tests for response formatters"""

import pytest
from datetime import datetime
from fastapi_easy.core.formatters import (
    JSONFormatter,
    PaginatedFormatter,
    EnvelopeFormatter,
    FormatterRegistry,
    get_formatter_registry,
)


class TestJSONFormatter:
    """Test JSONFormatter"""
    
    def test_format_dict(self):
        """Test formatting dictionary"""
        formatter = JSONFormatter()
        data = {"id": 1, "name": "test"}
        
        result = formatter.format(data)
        
        assert result["success"] is True
        assert result["data"] == data
    
    def test_format_list(self):
        """Test formatting list"""
        formatter = JSONFormatter()
        items = [{"id": 1}, {"id": 2}]
        
        result = formatter.format(items)
        
        assert result["success"] is True
        assert result["data"] == items
        assert result["count"] == 2
    
    def test_format_list_method(self):
        """Test format_list method"""
        formatter = JSONFormatter()
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        result = formatter.format_list(items)
        
        assert result["success"] is True
        assert result["data"] == items
        assert result["count"] == 3
    
    def test_format_error(self):
        """Test formatting error"""
        formatter = JSONFormatter()
        error = {
            "message": "Not found",
            "code": "NOT_FOUND",
            "details": {"reason": "Resource not found"},
        }
        
        result = formatter.format_error(error)
        
        assert result["success"] is False
        assert result["error"] == "Not found"
        assert result["code"] == "NOT_FOUND"


class TestPaginatedFormatter:
    """Test PaginatedFormatter"""
    
    def test_format_with_pagination(self):
        """Test formatting with pagination"""
        formatter = PaginatedFormatter()
        items = [{"id": 1}, {"id": 2}]
        
        result = formatter.format(items, total=100, skip=0, limit=10)
        
        assert result["success"] is True
        assert result["data"] == items
        assert result["pagination"]["total"] == 100
        assert result["pagination"]["skip"] == 0
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["count"] == 2
        assert result["pagination"]["pages"] == 10
    
    def test_format_list_with_pagination(self):
        """Test format_list with pagination"""
        formatter = PaginatedFormatter()
        items = [{"id": 1}, {"id": 2}, {"id": 3}]
        
        result = formatter.format_list(items, total=50, skip=10, limit=10)
        
        assert result["success"] is True
        assert result["data"] == items
        assert result["pagination"]["total"] == 50
        assert result["pagination"]["skip"] == 10
        assert result["pagination"]["count"] == 3
    
    def test_format_error(self):
        """Test formatting error"""
        formatter = PaginatedFormatter()
        error = {"message": "Bad request", "code": "BAD_REQUEST"}
        
        result = formatter.format_error(error)
        
        assert result["success"] is False
        assert result["error"] == "Bad request"


class TestEnvelopeFormatter:
    """Test EnvelopeFormatter"""
    
    def test_format_with_timestamp_and_version(self):
        """Test formatting with timestamp and version"""
        formatter = EnvelopeFormatter(include_timestamp=True, include_version=True)
        data = {"id": 1, "name": "test"}
        
        result = formatter.format(data)
        
        assert result["success"] is True
        assert result["data"] == data
        assert "timestamp" in result
        assert result["api_version"] == "1.0"
    
    def test_format_without_timestamp(self):
        """Test formatting without timestamp"""
        formatter = EnvelopeFormatter(include_timestamp=False, include_version=True)
        data = {"id": 1}
        
        result = formatter.format(data)
        
        assert result["success"] is True
        assert "timestamp" not in result
        assert result["api_version"] == "1.0"
    
    def test_format_without_version(self):
        """Test formatting without version"""
        formatter = EnvelopeFormatter(include_timestamp=True, include_version=False)
        data = {"id": 1}
        
        result = formatter.format(data)
        
        assert result["success"] is True
        assert "timestamp" in result
        assert "api_version" not in result
    
    def test_format_list_with_envelope(self):
        """Test format_list with envelope"""
        formatter = EnvelopeFormatter()
        items = [{"id": 1}, {"id": 2}]
        
        result = formatter.format_list(items)
        
        assert result["success"] is True
        assert result["data"] == items
        assert result["count"] == 2
        assert "timestamp" in result
    
    def test_format_error_with_envelope(self):
        """Test formatting error with envelope"""
        formatter = EnvelopeFormatter()
        error = {"message": "Server error", "code": "SERVER_ERROR"}
        
        result = formatter.format_error(error)
        
        assert result["success"] is False
        assert result["error"] == "Server error"
        assert "timestamp" in result


class TestFormatterRegistry:
    """Test FormatterRegistry"""
    
    def test_registry_initialization(self):
        """Test registry initialization"""
        registry = FormatterRegistry()
        
        assert registry.get("json") is not None
        assert registry.get("paginated") is not None
        assert registry.get("envelope") is not None
    
    def test_register_formatter(self):
        """Test registering a formatter"""
        registry = FormatterRegistry()
        
        class CustomFormatter(JSONFormatter):
            pass
        
        custom = CustomFormatter()
        registry.register("custom", custom)
        
        assert registry.get("custom") == custom
    
    def test_format_with_registry(self):
        """Test formatting with registry"""
        registry = FormatterRegistry()
        data = {"id": 1, "name": "test"}
        
        result = registry.format("json", data)
        
        assert result["success"] is True
        assert result["data"] == data
    
    def test_format_list_with_registry(self):
        """Test formatting list with registry"""
        registry = FormatterRegistry()
        items = [{"id": 1}, {"id": 2}]
        
        result = registry.format_list("json", items)
        
        assert result["success"] is True
        assert result["data"] == items
        assert result["count"] == 2
    
    def test_format_error_with_registry(self):
        """Test formatting error with registry"""
        registry = FormatterRegistry()
        error = {"message": "Error", "code": "ERROR"}
        
        result = registry.format_error("json", error)
        
        assert result["success"] is False
        assert result["error"] == "Error"
    
    def test_format_with_unknown_formatter(self):
        """Test formatting with unknown formatter"""
        registry = FormatterRegistry()
        data = {"id": 1}
        
        result = registry.format("unknown", data)
        
        assert result == data
    
    def test_paginated_format_with_registry(self):
        """Test paginated formatting with registry"""
        registry = FormatterRegistry()
        items = [{"id": 1}, {"id": 2}]
        
        result = registry.format_list("paginated", items, total=100, skip=0, limit=10)
        
        assert result["success"] is True
        assert result["pagination"]["total"] == 100


class TestGlobalRegistry:
    """Test global formatter registry"""
    
    def test_get_global_registry(self):
        """Test getting global registry"""
        registry = get_formatter_registry()
        
        assert registry is not None
        assert isinstance(registry, FormatterRegistry)
    
    def test_global_registry_singleton(self):
        """Test global registry is singleton"""
        registry1 = get_formatter_registry()
        registry2 = get_formatter_registry()
        
        assert registry1 is registry2
