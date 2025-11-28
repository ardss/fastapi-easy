"""Tests for query projection module"""

import pytest
from fastapi_easy.core.query_projection import (
    QueryProjection,
    ProjectionBuilder,
    create_projection,
    create_projection_builder,
)


class TestQueryProjection:
    """Test QueryProjection class"""
    
    def test_projection_creation(self):
        """Test creating projection"""
        projection = QueryProjection(["id", "name", "email"])
        assert projection.get_fields() == ["id", "name", "email"]
    
    def test_add_field(self):
        """Test adding a field"""
        projection = QueryProjection(["id", "name"])
        projection.add_field("email")
        assert "email" in projection.get_fields()
    
    def test_add_duplicate_field(self):
        """Test adding duplicate field"""
        projection = QueryProjection(["id", "name"])
        projection.add_field("id")
        assert projection.get_fields().count("id") == 1
    
    def test_remove_field(self):
        """Test removing a field"""
        projection = QueryProjection(["id", "name", "email"])
        projection.remove_field("email")
        assert "email" not in projection.get_fields()
    
    def test_has_field(self):
        """Test checking if field exists"""
        projection = QueryProjection(["id", "name"])
        assert projection.has_field("id")
        assert not projection.has_field("email")
    
    def test_apply_to_dict(self):
        """Test applying projection to dictionary"""
        projection = QueryProjection(["id", "name"])
        data = {"id": 1, "name": "John", "email": "john@example.com"}
        
        result = projection.apply_to_dict(data)
        assert result == {"id": 1, "name": "John"}
        assert "email" not in result
    
    def test_apply_to_list(self):
        """Test applying projection to list"""
        projection = QueryProjection(["id", "name"])
        data = [
            {"id": 1, "name": "John", "email": "john@example.com"},
            {"id": 2, "name": "Jane", "email": "jane@example.com"},
        ]
        
        result = projection.apply_to_list(data)
        assert len(result) == 2
        assert all("email" not in item for item in result)
        assert all("name" in item for item in result)
    
    def test_validate_fields_valid(self):
        """Test validating valid fields"""
        projection = QueryProjection(["id", "name"])
        available = ["id", "name", "email"]
        
        assert projection.validate_fields(available)
    
    def test_validate_fields_invalid(self):
        """Test validating invalid fields"""
        projection = QueryProjection(["id", "invalid"])
        available = ["id", "name", "email"]
        
        assert not projection.validate_fields(available)
    
    def test_get_invalid_fields(self):
        """Test getting invalid fields"""
        projection = QueryProjection(["id", "invalid1", "invalid2"])
        available = ["id", "name", "email"]
        
        invalid = projection.get_invalid_fields(available)
        assert set(invalid) == {"invalid1", "invalid2"}
    
    def test_method_chaining(self):
        """Test method chaining"""
        projection = QueryProjection(["id"])
        projection.add_field("name").add_field("email").remove_field("email")
        
        assert projection.get_fields() == ["id", "name"]


class TestProjectionBuilder:
    """Test ProjectionBuilder class"""
    
    def test_builder_add(self):
        """Test builder add method"""
        builder = ProjectionBuilder()
        builder.add("id").add("name")
        
        projection = builder.build()
        assert projection.get_fields() == ["id", "name"]
    
    def test_builder_add_multiple(self):
        """Test builder add_multiple method"""
        builder = ProjectionBuilder()
        builder.add_multiple(["id", "name", "email"])
        
        projection = builder.build()
        assert projection.get_fields() == ["id", "name", "email"]
    
    def test_builder_exclude(self):
        """Test builder exclude method"""
        builder = ProjectionBuilder()
        builder.add_multiple(["id", "name", "email"])
        builder.exclude("email")
        
        projection = builder.build()
        assert "email" not in projection.get_fields()
    
    def test_builder_chaining(self):
        """Test builder method chaining"""
        projection = (
            ProjectionBuilder()
            .add("id")
            .add("name")
            .add("email")
            .exclude("email")
            .build()
        )
        
        assert projection.get_fields() == ["id", "name"]


class TestFactoryFunctions:
    """Test factory functions"""
    
    def test_create_projection(self):
        """Test create_projection factory"""
        projection = create_projection("id", "name", "email")
        assert projection.get_fields() == ["id", "name", "email"]
    
    def test_create_projection_builder(self):
        """Test create_projection_builder factory"""
        builder = create_projection_builder()
        assert isinstance(builder, ProjectionBuilder)
        assert builder.fields == []
