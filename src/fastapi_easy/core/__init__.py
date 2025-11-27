"""Core modules for FastAPI-Easy"""

from .crud_router import CRUDRouter
from .operations import Operation, OperationRegistry
from .adapters import ORMAdapter
from .hooks import HookRegistry
from .errors import AppError, ErrorCode
from .config import CRUDConfig

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
