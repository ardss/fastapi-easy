"""Utility for handling Pydantic models as query parameters in GET requests."""

from typing import Any, Type, get_type_hints, Callable
from fastapi import Query, Depends
from pydantic import BaseModel, ValidationError


def QueryParams(schema: Type[BaseModel]) -> Callable:
    """
    Decorator to convert Pydantic model dependencies into query parameters for GET requests.

    This solves the issue where using Pydantic models with Depends() in GET
    endpoints causes OpenAPI to incorrectly show a request body requirement.

    Usage:
        @QueryParams(UserQuery)
        async def get_users(params: UserQuery):
            return params

    Args:
        schema: Pydantic model class to convert to query parameters

    Returns:
        Dependency function that converts query parameters to the Pydantic model
    """

    def dependency(**query_params: Any) -> BaseModel:
        """Convert query parameters to Pydantic model"""
        try:
            return schema(**query_params)
        except ValidationError as e:
            # FastAPI will automatically handle the validation error
            raise e

    # Get field information from the Pydantic model
    model_fields = schema.model_fields
    type_hints = get_type_hints(schema)

    # Create default values and descriptions for each field
    defaults = {}
    for field_name, field_info in model_fields.items():
        # Extract description from field if available
        description = (
            field_info.description
            if hasattr(field_info, "description")
            else f"Query parameter: {field_name}"
        )

        # Handle default value
        if field_info.default is not None and field_info.default != ...:
            # Field has a default value
            defaults[field_name] = Query(default=field_info.default, description=description)
        elif field_info.default_factory is not None:
            # Field has a default factory
            defaults[field_name] = Query(
                default_factory=field_info.default_factory, description=description
            )
        else:
            # Required field
            defaults[field_name] = Query(..., description=description)

    # Update dependency function signature with proper defaults
    dependency.__defaults__ = tuple(defaults.values())
    dependency.__annotations__ = {**type_hints, "return": schema}

    return dependency


def as_query_params(schema: Type[BaseModel]) -> Callable:
    """
    Alternative way to use Pydantic models as query parameters.

    This creates a dependency that can be used directly in FastAPI endpoints.

    Args:
        schema: Pydantic model class to convert to query parameters

    Returns:
        Dependency function that converts query parameters to the Pydantic model

    Example:
        async def get_users(params: UserQuery = Depends(as_query_params(UserQuery))):
            return {"name": params.name, "age": params.age}
    """

    def query_dependency(**kwargs: Any) -> BaseModel:
        """Convert query parameters to Pydantic model"""
        return schema(**kwargs)

    # Get field information from the Pydantic model
    model_fields = schema.model_fields
    type_hints = get_type_hints(schema)

    # Add Query dependencies for each field
    for field_name, field_info in model_fields.items():
        field_type = type_hints.get(field_name, Any)
        description = (
            field_info.description
            if hasattr(field_info, "description")
            else f"Query parameter: {field_name}"
        )

        if field_info.default is not None and field_info.default != ...:
            query_dependency.__annotations__[field_name] = field_type
            # Set default value using Query
            setattr(
                query_dependency,
                field_name,
                Query(default=field_info.default, description=description),
            )
        else:
            query_dependency.__annotations__[field_name] = field_type
            # Set required value using Query
            setattr(query_dependency, field_name, Query(..., description=description))

    query_dependency.__annotations__["return"] = schema

    return query_dependency


# Example usage and test
if __name__ == "__main__":
    from fastapi import FastAPI
    import uvicorn

    app = FastAPI()

    class UserQuery(BaseModel):
        name: str
        age: int = None
        city: str = "New York"

        model_config = {
            "json_schema_extra": {"example": {"name": "John", "age": 30, "city": "New York"}}
        }

    @app.get("/users/")
    async def get_users(params: UserQuery = Depends(as_query_params(UserQuery))):
        """Get users with query parameters - correctly shows as query params in OpenAPI."""
        return {
            "message": f"Searching for users: {params.name}, "
            f"Age: {params.age}, City: {params.city}"
        }

    # This will correctly show query parameters in OpenAPI instead of request body
    if __name__ == "__main__":
        uvicorn.run(app, host="0.0.0.0", port=8000)
