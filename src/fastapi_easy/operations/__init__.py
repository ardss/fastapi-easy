"""Built-in operations for FastAPI-Easy"""

from .get_all import GetAllOperation
from .get_one import GetOneOperation
from .create import CreateOperation
from .update import UpdateOperation
from .delete_one import DeleteOneOperation
from .delete_all import DeleteAllOperation

__all__ = [
    "GetAllOperation",
    "GetOneOperation",
    "CreateOperation",
    "UpdateOperation",
    "DeleteOneOperation",
    "DeleteAllOperation",
]
