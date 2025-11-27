"""
FastAPI-Easy: A modern CRUD framework for FastAPI

A production-ready CRUD router generation framework that reduces code by 95%
and development time by 87%.

License: AGPL-3.0
For commercial licensing, please contact: 1339731209@qq.com
"""

__version__ = "0.1.0"
__author__ = "FastAPI-Easy Team"
__license__ = "AGPL-3.0"

from .core.crud_router import CRUDRouter
from .core.adapters import ORMAdapter
from .core.hooks import HookRegistry
from .core.errors import AppError, ErrorCode
from .core.config import CRUDConfig

__all__ = [
    "CRUDRouter",
    "ORMAdapter",
    "HookRegistry",
    "AppError",
    "ErrorCode",
    "CRUDConfig",
]
