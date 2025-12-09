"""Utility for handling Pydantic models as query parameters in GET requests."""

from __future__ import annotations

import json
from typing import Any, Callable, Type, get_origin, get_type_hints

from fastapi import Depends, Query
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

    if origin is list or field_type is list or origin is dict or field_type is dict:
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
    # Get field information from the Pydantic model
    model_fields = schema.model_fields
    type_hints = get_type_hints(schema)

    # Create dependency with explicit parameters
    import inspect

    def dependency(**query_params: Any) -> BaseModel:
        """Convert query parameters to Pydantic model"""
        # Filter out None values for fields that have None as default
        filtered_params = {}
        for field_name, value in query_params.items():
            if field_name in model_fields:
                field_info = model_fields[field_name]
                # Skip None values for fields with None default
                if value is None and field_info.default is None:
                    continue
            filtered_params[field_name] = value

        try:
            return schema(**filtered_params)
        except ValidationError as e:
            # Try to parse complex types if validation fails
            try:
                parsed_params = {}

                for field_name, value in filtered_params.items():
                    if field_name in type_hints:
                        field_type = type_hints[field_name]
                        parsed_params[field_name] = _parse_complex_type(value, field_type)
                    else:
                        parsed_params[field_name] = value

                return schema(**parsed_params)
            except ValidationError:
                # If still fails, raise the original error
                raise e

    # Set proper function signature for FastAPI
    sig_parameters = []
    annotations_dict = {}

    # Separate required and optional fields to ensure correct signature order
    required_fields = []
    optional_fields = []

    for field_name, field_info in model_fields.items():
        field_type = type_hints.get(field_name, Any)

        # Extract description from field if available
        description = (
            field_info.description
            if hasattr(field_info, "description")
            else f"Query parameter: {field_name}"
        )

        # Create Query object based on field properties
        if field_info.default is not ...:
            # Field has a default value (including None)
            query_obj = Query(default=field_info.default, description=description)
            has_default = True
        elif field_info.default_factory is not None:
            # Field has a default factory
            query_obj = Query(
                default_factory=field_info.default_factory, description=description
            )
            has_default = True
        else:
            # Required field (only when default is Ellipsis ...)
            query_obj = Query(..., description=description)
            has_default = False

        # Create parameter for signature
        param = inspect.Parameter(
            name=field_name,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=query_obj if has_default else inspect.Parameter.empty,
            annotation=field_type
        )

        if has_default:
            optional_fields.append((field_name, param, field_type))
        else:
            required_fields.append((field_name, param, field_type))

    # Add required fields first, then optional fields (Python signature requirement)
    for field_name, param, field_type in required_fields + optional_fields:
        sig_parameters.append(param)
        annotations_dict[field_name] = field_type

    # Update function signature and annotations
    dependency.__signature__ = inspect.Signature(sig_parameters)
    dependency.__annotations__ = {**annotations_dict, "return": schema}

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
    # Get field information from the Pydantic model
    model_fields = schema.model_fields
    type_hints = get_type_hints(schema)

    # Create dependency with explicit parameters
    import inspect

    def query_dependency(**kwargs: Any) -> BaseModel:
        """Convert query parameters to Pydantic model"""
        # Filter out None values for fields that have None as default
        filtered_params = {}
        for field_name, value in kwargs.items():
            if field_name in model_fields:
                field_info = model_fields[field_name]
                # Skip None values for fields with None default
                if value is None and field_info.default is None:
                    continue
            filtered_params[field_name] = value

        # Parse complex types from JSON strings before validation
        parsed_params = {}

        for field_name, value in filtered_params.items():
            if field_name in type_hints:
                field_type = type_hints[field_name]
                parsed_params[field_name] = _parse_complex_type(value, field_type)
            else:
                parsed_params[field_name] = value

        return schema(**parsed_params)

    # Set proper function signature for FastAPI
    sig_parameters = []
    annotations_dict = {}

    # Separate required and optional fields to ensure correct signature order
    required_fields = []
    optional_fields = []

    for field_name, field_info in model_fields.items():
        field_type = type_hints.get(field_name, Any)

        # Extract description from field if available
        description = (
            field_info.description
            if hasattr(field_info, "description")
            else f"Query parameter: {field_name}"
        )

        # Create Query object based on field properties
        if field_info.default is not ...:
            # Field has a default value (including None)
            query_obj = Query(default=field_info.default, description=description)
            has_default = True
        elif field_info.default_factory is not None:
            # Field has a default factory
            query_obj = Query(
                default_factory=field_info.default_factory, description=description
            )
            has_default = True
        else:
            # Required field (only when default is Ellipsis ...)
            query_obj = Query(..., description=description)
            has_default = False

        # Create parameter for signature
        param = inspect.Parameter(
            name=field_name,
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=query_obj if has_default else inspect.Parameter.empty,
            annotation=field_type
        )

        if has_default:
            optional_fields.append((field_name, param, field_type))
        else:
            required_fields.append((field_name, param, field_type))

    # Add required fields first, then optional fields (Python signature requirement)
    for field_name, param, field_type in required_fields + optional_fields:
        sig_parameters.append(param)
        annotations_dict[field_name] = field_type

    # Update function signature and annotations
    query_dependency.__signature__ = inspect.Signature(sig_parameters)
    query_dependency.__annotations__ = {**annotations_dict, "return": schema}

    return query_dependency


# Example usage and test
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI

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
