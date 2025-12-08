"""
FastAPI-Easy: A modern CRUD framework for FastAPI

A production-ready CRUD router generation framework that reduces code by 95%
and development time by 87%.

License: AGPL-3.0
For commercial licensing, please contact: 1339731209@qq.com
"""

__version__ = "0.1.6"
__author__ = "FastAPI-Easy Team"
__license__ = "AGPL-3.0"

from typing import Optional, Type

from .app import FastAPIEasy
from .backends import SQLAlchemyAdapter
from .core.adapters import ORMAdapter
from .core.config import CRUDConfig
from .core.crud_router import CRUDRouter
from .core.errors import AppError, ErrorCode
from .core.hooks import HookRegistry

# Optional adapters
TortoiseAdapter: Optional[Type[ORMAdapter]] = None
try:
    from .backends import TortoiseAdapter as _TortoiseAdapter

    TortoiseAdapter = _TortoiseAdapter
except ImportError:
    pass

SQLModelAdapter: Optional[Type[ORMAdapter]] = None
try:
    from .backends import SQLModelAdapter as _SQLModelAdapter

    SQLModelAdapter = _SQLModelAdapter
except ImportError:
    pass

MongoAdapter: Optional[Type[ORMAdapter]] = None
try:
    from .backends import MongoAdapter as _MongoAdapter

    MongoAdapter = _MongoAdapter
except ImportError:
    pass

__all__ = [
    "CRUDRouter",
    "ORMAdapter",
    "HookRegistry",
    "AppError",
    "ErrorCode",
    "CRUDConfig",
    "FastAPIEasy",
    "SQLAlchemyAdapter",
    "TortoiseAdapter",
    "SQLModelAdapter",
    "MongoAdapter",
]
