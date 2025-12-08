"""Tests for query_params utility"""

import pytest
from typing import Any, Dict
from fastapi import FastAPI, Depends, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from fastapi_easy.utils.query_params import QueryParams, as_query_params


class UserQuery(BaseModel):
    """Test query model"""
    name: str
    age: int = None
    city: str = "New York"


def test_query_params_decorator():
    """Test QueryParams decorator functionality"""
    dependency = QueryParams(UserQuery)

    # Test with valid parameters
    result = dependency(name="John", age=30, city="Boston")
    assert isinstance(result, UserQuery)
    assert result.name == "John"
    assert result.age == 30
    assert result.city == "Boston"

    # Test with default values
    result = dependency(name="Alice")
    assert result.name == "Alice"
    assert result.age is None
    assert result.city == "New York"


def test_query_params_validation_error():
    """Test QueryParams decorator with invalid data"""
    dependency = QueryParams(UserQuery)

    # Test with missing required field
    with pytest.raises(ValidationError):
        dependency(age=30, city="Boston")


def test_as_query_params_function():
    """Test as_query_params function functionality"""
    dependency = as_query_params(UserQuery)

    # Test with valid parameters
    result = dependency(name="John", age=30, city="Boston")
    assert isinstance(result, UserQuery)
    assert result.name == "John"
    assert result.age == 30
    assert result.city == "Boston"

    # Test with default values
    result = dependency(name="Alice")
    assert result.name == "Alice"
    assert result.age is None
    assert result.city == "New York"


def test_as_query_params_validation_error():
    """Test as_query_params function with invalid data"""
    dependency = as_query_params(UserQuery)

    # Test with missing required field
    with pytest.raises(ValidationError):
        dependency(age=30, city="Boston")


def test_query_params_with_optional_fields():
    """Test QueryParams with optional fields"""
    class OptionalQuery(BaseModel):
        required: str
        optional_field: str = None
        default_field: str = "default"

    dependency = QueryParams(OptionalQuery)

    # Test with only required field
    result = dependency(required="value")
    assert result.required == "value"
    assert result.optional_field is None
    assert result.default_field == "default"


def test_query_params_with_complex_types():
    """Test QueryParams with complex field types"""
    class ComplexQuery(BaseModel):
        items: list = []
        metadata: dict = {}
        count: int = 0

    dependency = QueryParams(ComplexQuery)

    result = dependency(items='["a", "b"]', metadata='{"key": "value"}', count="5")
    assert isinstance(result, ComplexQuery)


def test_query_params_fastapi_integration():
    """Test QueryParams integration with FastAPI"""
    app = FastAPI()

    @app.get("/users/")
    async def get_users(params: UserQuery = Depends(QueryParams(UserQuery))):
        return {"name": params.name, "age": params.age, "city": params.city}

    client = TestClient(app)
    response = client.get("/users/?name=John&age=30&city=Boston")
    assert response.status_code == 200
    assert response.json() == {"name": "John", "age": 30, "city": "Boston"}


def test_as_query_params_fastapi_integration():
    """Test as_query_params integration with FastAPI"""
    app = FastAPI()

    @app.get("/users/")
    async def get_users(params: UserQuery = Depends(as_query_params(UserQuery))):
        return {"name": params.name, "age": params.age, "city": params.city}

    client = TestClient(app)
    response = client.get("/users/?name=Alice")
    assert response.status_code == 200
    assert response.json() == {"name": "Alice", "age": None, "city": "New York"}


def test_query_preserves_annotations():
    """Test that QueryParams preserves type annotations"""
    dependency = QueryParams(UserQuery)

    # Check that annotations are preserved
    assert hasattr(dependency, '__annotations__')
    assert 'return' in dependency.__annotations__
    assert dependency.__annotations__['return'] == UserQuery


def test_as_query_params_preserves_annotations():
    """Test that as_query_params preserves type annotations"""
    dependency = as_query_params(UserQuery)

    # Check that annotations are preserved
    assert hasattr(dependency, '__annotations__')
    assert 'return' in dependency.__annotations__
    assert dependency.__annotations__['return'] == UserQuery


def test_query_params_with_model_description():
    """Test QueryParams with model field descriptions"""
    class DescribedQuery(BaseModel):
        """Query model with field descriptions"""
        name: str
        age: int = None

        model_config = {
            "json_schema_extra": {
                "example": {"name": "John", "age": 30}
            }
        }

    dependency = QueryParams(DescribedQuery)
    result = dependency(name="John", age=30)

    assert isinstance(result, DescribedQuery)
    assert result.name == "John"
    assert result.age == 30


def test_query_params_error_handling():
    """Test QueryParams error handling"""
    dependency = QueryParams(UserQuery)

    # Test with invalid data types that should raise ValidationError
    with pytest.raises(ValidationError):
        dependency(name=123)  # name should be string


def test_query_params_empty_model():
    """Test QueryParams with empty model"""
    class EmptyQuery(BaseModel):
        pass

    dependency = QueryParams(EmptyQuery)
    result = dependency()

    assert isinstance(result, EmptyQuery)