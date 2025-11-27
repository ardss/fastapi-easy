"""Tests for filter utilities"""

import pytest
from fastapi_easy.utils.filters import FilterParser


class TestFilterParser:
    """Test filter parser"""
    
    def test_exact_match(self):
        """Test exact match filter"""
        filters = FilterParser.parse({"name": "apple"})
        
        assert "name" in filters
        assert filters["name"]["field"] == "name"
        assert filters["name"]["operator"] == "exact"
        assert filters["name"]["value"] == "apple"
    
    def test_not_equal_operator(self):
        """Test not equal operator"""
        filters = FilterParser.parse({"status__ne": "inactive"})
        
        assert "status__ne" in filters
        assert filters["status__ne"]["operator"] == "ne"
        assert filters["status__ne"]["value"] == "inactive"
    
    def test_greater_than_operator(self):
        """Test greater than operator"""
        filters = FilterParser.parse({"price__gt": "100"})
        
        assert "price__gt" in filters
        assert filters["price__gt"]["operator"] == "gt"
        assert filters["price__gt"]["value"] == "100"
    
    def test_greater_than_or_equal_operator(self):
        """Test greater than or equal operator"""
        filters = FilterParser.parse({"price__gte": "50"})
        
        assert filters["price__gte"]["operator"] == "gte"
    
    def test_less_than_operator(self):
        """Test less than operator"""
        filters = FilterParser.parse({"price__lt": "200"})
        
        assert filters["price__lt"]["operator"] == "lt"
    
    def test_less_than_or_equal_operator(self):
        """Test less than or equal operator"""
        filters = FilterParser.parse({"price__lte": "150"})
        
        assert filters["price__lte"]["operator"] == "lte"
    
    def test_in_operator(self):
        """Test in operator"""
        filters = FilterParser.parse({"status__in": "active,pending,review"})
        
        assert filters["status__in"]["operator"] == "in"
        assert filters["status__in"]["value"] == "active,pending,review"
    
    def test_like_operator(self):
        """Test like operator"""
        filters = FilterParser.parse({"name__like": "%apple%"})
        
        assert filters["name__like"]["operator"] == "like"
    
    def test_ilike_operator(self):
        """Test case-insensitive like operator"""
        filters = FilterParser.parse({"name__ilike": "%APPLE%"})
        
        assert filters["name__ilike"]["operator"] == "ilike"
    
    def test_multiple_filters(self):
        """Test multiple filters"""
        filters = FilterParser.parse({
            "name": "apple",
            "price__gt": "10",
            "status__in": "active,pending",
        })
        
        assert len(filters) == 3
        assert filters["name"]["operator"] == "exact"
        assert filters["price__gt"]["operator"] == "gt"
        assert filters["status__in"]["operator"] == "in"
    
    def test_allowed_fields_filter(self):
        """Test filtering by allowed fields"""
        filters = FilterParser.parse(
            {"name": "apple", "secret": "value", "price": "10"},
            allowed_fields=["name", "price"],
        )
        
        assert "name" in filters
        assert "price" in filters
        assert "secret" not in filters
    
    def test_empty_filters(self):
        """Test empty filter parameters"""
        filters = FilterParser.parse({})
        
        assert filters == {}
    
    def test_underscore_prefix_ignored(self):
        """Test that underscore-prefixed parameters are ignored"""
        filters = FilterParser.parse({
            "name": "apple",
            "_internal": "value",
        })
        
        assert "name" in filters
        assert "_internal" not in filters
    
    def test_invalid_operator_treated_as_exact(self):
        """Test that invalid operators are treated as exact match"""
        filters = FilterParser.parse({"field__invalid": "value"})
        
        assert "field__invalid" in filters
        assert filters["field__invalid"]["operator"] == "exact"
        assert filters["field__invalid"]["field"] == "field__invalid"
    
    def test_get_operator_description(self):
        """Test getting operator description"""
        assert "greater_than" in FilterParser.get_operator_description("gt")
        assert "less_than" in FilterParser.get_operator_description("lt")
        assert "exact match" in FilterParser.get_operator_description("unknown")
