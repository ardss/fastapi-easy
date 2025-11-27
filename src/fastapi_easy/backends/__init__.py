"""FastAPI-Easy backends"""

from .base import BaseORMAdapter
from .sqlalchemy import SQLAlchemyAdapter

# Tortoise is optional
try:
    from .tortoise import TortoiseAdapter
    __all__ = [
        "BaseORMAdapter",
        "SQLAlchemyAdapter",
        "TortoiseAdapter",
    ]
except ImportError:
    __all__ = [
        "BaseORMAdapter",
        "SQLAlchemyAdapter",
    ]
