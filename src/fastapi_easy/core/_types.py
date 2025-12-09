"""
Common type definitions for FastAPI-Easy

This module provides common type annotations that can be used throughout
the project to ensure consistent typing.
"""

from __future__ import annotations

from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)
from collections.abc import Mapping
from datetime import datetime, timedelta
from decimal import Decimal

# Generic TypeVars
T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")
R = TypeVar("R", covariant=True)
ID = TypeVar("ID", bound=Union[str, int])

# Common data types
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
JSONObject = Dict[str, JSONValue]
JSONList = List[JSONValue]

# Database types
DatabaseID = Union[int, str]
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")
ResponseType = TypeVar("ResponseType")

# HTTP types
HTTPMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
QueryParamValue = Union[str, int, float, bool, List[str]]
Headers = Dict[str, str]
Cookies = Dict[str, str]

# Cache types
CacheKey = Union[str, int, Tuple[Any, ...]]
CacheValue = Any
TTL = Union[int, float, timedelta]

# Security types
Permission = str
Role = str
Token = str
Credentials = Dict[str, str]

# Configuration types
ConfigValue = Union[str, int, float, bool, List[Any], Dict[str, Any]]
EnvVar = str

# Event types
EventHandler = Callable[..., Awaitable[None]]
EventData = Dict[str, Any]

# Error types
ErrorCode = str
ErrorMessage = str
ErrorDetail = Dict[str, Any]

# Performance types
MetricName = str
MetricValue = Union[int, float, Decimal]
PerformanceTags = Dict[str, str]

# Testing types
TestResult = Dict[str, Any]
TestSuite = List[TestResult]
AssertionError = Type[AssertionError]

# Common callable signatures
VoidCallable = Callable[..., None]
AsyncVoidCallable = Callable[..., Awaitable[None]]
BoolCallable = Callable[..., bool]
AsyncBoolCallable = Callable[..., Awaitable[bool]]
StringCallable = Callable[..., str]
AsyncStringCallable = Callable[..., Awaitable[str]]

# Container types with proper typing
StringDict = Dict[str, str]
AnyDict = Dict[str, Any]
StringList = List[str]
AnyList = List[Any]

# Optional type constructors
def make_optional_list(item_type: Type[Any]) -> Type[Any]:
    """Create an optional list type"""
    return Optional[List[item_type]]

def make_optional_dict(key_type: Type[Any], value_type: Type[Any]) -> Type[Any]:
    """Create an optional dict type"""
    return Optional[Dict[key_type, value_type]]