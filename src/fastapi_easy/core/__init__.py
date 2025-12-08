"""Core modules for FastAPI-Easy"""

from __future__ import annotations

from .adapters import ORMAdapter
from .config import CRUDConfig
from .crud_router import CRUDRouter
from .errors import AppError, ErrorCode
from .hooks import HookRegistry

__all__ = [
    "AppError",
    "CRUDConfig",
    "CRUDRouter",
    "ErrorCode",
    "HookRegistry",
    "ORMAdapter",
]
