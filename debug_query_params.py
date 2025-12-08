#!/usr/bin/env python3
"""Debug script for QueryParams issue"""

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_easy.utils.query_params import QueryParams


class UserQuery(BaseModel):
    name: str
    age: int = None
    city: str = "New York"


def test_basic_functionality():
    """Test basic functionality first"""
    dependency = QueryParams(UserQuery)

    # Test direct call
    result = dependency(name="John", age="30", city="Boston")
    print("Direct call result:", result)
    print("Type:", type(result))
    print("Values:", result.name, result.age, result.city)


def test_fastapi_integration():
    """Test FastAPI integration"""
    app = FastAPI()

    @app.get("/users/")
    async def get_users(params: UserQuery = Depends(QueryParams(UserQuery))):
        return {"name": params.name, "age": params.age, "city": params.city}

    client = TestClient(app)
    response = client.get("/users/?name=John&age=30&city=Boston")
    print("Response status:", response.status_code)
    print("Response content:", response.content)
    print("Response JSON:", response.json() if response.status_code == 200 else "Error")


if __name__ == "__main__":
    print("=== Testing basic functionality ===")
    test_basic_functionality()

    print("\n=== Testing FastAPI integration ===")
    test_fastapi_integration()