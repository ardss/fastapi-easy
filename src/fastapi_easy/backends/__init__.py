"""FastAPI-Easy backends"""

from .base import BaseORMAdapter
from .sqlalchemy import SQLAlchemyAdapter

# Optional backends
_optional_backends = []

# Tortoise is optional
try:
    from .tortoise import TortoiseAdapter

    _optional_backends.append("TortoiseAdapter")
except ImportError:
    pass

# SQLModel is optional
try:
    from .sqlmodel import SQLModelAdapter

    _optional_backends.append("SQLModelAdapter")
except ImportError:
    pass

# MongoDB (Motor) is optional
try:
    from .mongo import MongoAdapter

    _optional_backends.append("MongoAdapter")
except ImportError:
    pass

__all__ = [
    "BaseORMAdapter",
    "SQLAlchemyAdapter",
] + _optional_backends
