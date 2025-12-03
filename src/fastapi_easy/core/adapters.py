"""ORM adapter system for FastAPI-Easy"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ORMAdapter(ABC):
    """Base ORM adapter class

    All ORM adapters should inherit from this class and implement
    the abstract methods.

    Raises:
        ValueError: If invalid parameters provided
        RuntimeError: If database operation fails
    """

    @abstractmethod
    async def get_all(
        self,
        filters: Dict[str, Any],
        sorts: Dict[str, Any],
        pagination: Dict[str, Any],
    ) -> List[Any]:
        """Get all items

        Args:
            filters: Filter conditions
            sorts: Sort conditions
            pagination: Pagination info (skip, limit)

        Returns:
            List of items (never None, may be empty)

        Raises:
            ValueError: If invalid pagination parameters
            RuntimeError: If database query fails
        """
        pass

    @abstractmethod
    async def get_one(self, id: Any) -> Optional[Any]:
        """Get single item by id

        Args:
            id: Item id

        Returns:
            Item or None if not found
        """
        pass

    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Any:
        """Create new item

        Args:
            data: Item data

        Returns:
            Created item
        """
        pass

    @abstractmethod
    async def update(self, id: Any, data: Dict[str, Any]) -> Any:
        """Update item

        Args:
            id: Item id
            data: Updated data

        Returns:
            Updated item
        """
        pass

    @abstractmethod
    async def delete_one(self, id: Any) -> Any:
        """Delete single item

        Args:
            id: Item id

        Returns:
            Deleted item
        """
        pass

    @abstractmethod
    async def delete_all(self) -> List[Any]:
        """Delete all items

        Returns:
            List of deleted items
        """
        pass

    @abstractmethod
    async def count(self, filters: Dict[str, Any]) -> int:
        """Count items

        Args:
            filters: Filter conditions

        Returns:
            Total count
        """
        pass
