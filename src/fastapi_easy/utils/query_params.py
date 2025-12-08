"""Utility for handling Pydantic models as query parameters in GET requests."""

import json
from typing import Any, Type, get_type_hints, Callable, get_origin, get_args
from fastapi import Query, Depends
from pydantic import BaseModel, ValidationError


def _parse_complex_type(value: Any, field_type: Type) -> Any:
    """
    Parse complex types (list, dict) from JSON strings when needed.

    Args:
        value: The raw value from query parameters
        field_type: The expected field type from the model

    Returns:
        Parsed value or original value if no parsing needed
    """
    # If value is not a string, return as-is
    if not isinstance(value, str):
        return value

    # Check if this is a complex type that needs JSON parsing
    origin = get_origin(field_type)

    if origin is list or field_type is list:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, return original string
            # Pydantic will handle the validation error
            return value
    elif origin is dict or field_type is dict:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, return original string
            # Pydantic will handle the validation error
            return value
    # Handle other complex types like typing.List[str]
    elif origin is not None and origin in (list, dict):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value

    # For simple types, return as-is
    return value


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
            # Try to parse complex types if validation fails
            try:
                type_hints = get_type_hints(schema)
                parsed_params = {}

                for field_name, value in query_params.items():
                    if field_name in type_hints:
                        field_type = type_hints[field_name]
                        parsed_params[field_name] = _parse_complex_type(value, field_type)
                    else:
                        parsed_params[field_name] = value

                return schema(**parsed_params)
            except ValidationError:
                # If still fails, raise the original error
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
        # Parse complex types from JSON strings before validation
        type_hints = get_type_hints(schema)
        parsed_params = {}

        for field_name, value in kwargs.items():
            if field_name in type_hints:
                field_type = type_hints[field_name]
                parsed_params[field_name] = _parse_complex_type(value, field_type)
            else:
                parsed_params[field_name] = value

        return schema(**parsed_params)

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
