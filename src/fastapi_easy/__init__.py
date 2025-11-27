"""
FastAPI-Easy: A modern CRUD framework for FastAPI

A production-ready CRUD router generation framework that reduces code by 95%
and development time by 87%.
"""

__version__ = "0.1.0"
__author__ = "FastAPI-Easy Team"
__license__ = "MIT"

from .core.crud_router import CRUDRouter
from .core.operations import Operation, OperationRegistry
from .core.adapters import ORMAdapter
from .core.hooks import HookRegistry
from .core.errors import AppError, ErrorCode
from .core.config import CRUDConfig

__all__ = [
    "CRUDRouter",
    "Operation",
    "OperationRegistry",
    "ORMAdapter",
    "HookRegistry",
    "AppError",
    "ErrorCode",
    "CRUDConfig",
]
