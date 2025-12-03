"""SQLModel async ORM adapter"""

from typing import Type, Any
from .sqlalchemy import SQLAlchemyAdapter

try:
    from sqlmodel import SQLModel
except ImportError:
    SQLModel = Any  # type: ignore


class SQLModelAdapter(SQLAlchemyAdapter):
    """SQLModel async ORM adapter

    Inherits from SQLAlchemyAdapter since SQLModel is built on top of SQLAlchemy.
    """

    def __init__(
        self,
        model: Type[SQLModel],
        session_factory: Any,
        pk_field: str = "id",
    ):
        """Initialize SQLModel adapter

        Args:
            model: SQLModel class
            session_factory: Async session factory
            pk_field: Primary key field name
        """
        super().__init__(model, session_factory, pk_field)
