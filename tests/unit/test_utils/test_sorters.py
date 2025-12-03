"""Tests for sort utilities"""

import pytest
from fastapi_easy.utils.sorters import SortParser


class TestSortParser:
    """Test sort parser"""

    def test_single_field_ascending(self):
        """Test single field ascending sort"""
        sorts = SortParser.parse("name")

        assert "name" in sorts
        assert sorts["name"] == "asc"

    def test_single_field_descending(self):
        """Test single field descending sort"""
        sorts = SortParser.parse("-created_at")

        assert "created_at" in sorts
        assert sorts["created_at"] == "desc"

    def test_multiple_fields(self):
        """Test multiple fields sort"""
        sorts = SortParser.parse("category,name,-price")

        assert len(sorts) == 3
        assert sorts["category"] == "asc"
        assert sorts["name"] == "asc"
        assert sorts["price"] == "desc"

    def test_empty_sort(self):
        """Test empty sort parameter"""
        sorts = SortParser.parse(None)

        assert sorts == {}

    def test_empty_string_sort(self):
        """Test empty string sort parameter"""
        sorts = SortParser.parse("")

        assert sorts == {}

    def test_whitespace_handling(self):
        """Test whitespace handling"""
        sorts = SortParser.parse("  name  ,  -price  ")

        assert "name" in sorts
        assert "price" in sorts

    def test_allowed_fields_filter(self):
        """Test filtering by allowed fields"""
        sorts = SortParser.parse(
            "name,-price,secret",
            allowed_fields=["name", "price"],
        )

        assert "name" in sorts
        assert "price" in sorts
        assert "secret" not in sorts

    def test_parse_from_dict(self):
        """Test parsing from query parameters dictionary"""
        query_params = {"sort": "name,-price"}

        sorts = SortParser.parse_from_dict(query_params)

        assert sorts["name"] == "asc"
        assert sorts["price"] == "desc"

    def test_parse_from_dict_list(self):
        """Test parsing from query parameters with list value"""
        query_params = {"sort": ["name,-price"]}

        sorts = SortParser.parse_from_dict(query_params)

        assert sorts["name"] == "asc"
        assert sorts["price"] == "desc"

    def test_parse_from_dict_missing_sort(self):
        """Test parsing when sort parameter is missing"""
        query_params = {"filter": "value"}

        sorts = SortParser.parse_from_dict(query_params)

        assert sorts == {}

    def test_parse_from_dict_empty_list(self):
        """Test parsing with empty sort list"""
        query_params = {"sort": []}

        sorts = SortParser.parse_from_dict(query_params)

        assert sorts == {}

    def test_to_list(self):
        """Test conversion to list of tuples"""
        sorts = {"name": "asc", "price": "desc"}

        result = SortParser.to_list(sorts)

        assert isinstance(result, list)
        assert ("name", "asc") in result
        assert ("price", "desc") in result

    def test_to_list_empty(self):
        """Test conversion of empty sorts to list"""
        sorts = {}

        result = SortParser.to_list(sorts)

        assert result == []

    def test_complex_sort_string(self):
        """Test complex sort string"""
        sorts = SortParser.parse("created_at,-updated_at,name,status")

        assert len(sorts) == 4
        assert sorts["created_at"] == "asc"
        assert sorts["updated_at"] == "desc"
        assert sorts["name"] == "asc"
        assert sorts["status"] == "asc"
