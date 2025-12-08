"""Response formatters for FastAPI-Easy"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseFormatter(ABC):
    """Base formatter class"""

    @abstractmethod
    def format(self, data: Any) -> Any:
        """Format data

        Args:
            data: Data to format

        Returns:
            Formatted data
        """

    @abstractmethod
    def format_list(self, items: List[Any]) -> Any:
        """Format list of items

        Args:
            items: List of items

        Returns:
            Formatted list
        """

    @abstractmethod
    def format_error(self, error: Dict[str, Any]) -> Any:
        """Format error response

        Args:
            error: Error dictionary

        Returns:
            Formatted error
        """


class JSONFormatter(BaseFormatter):
    """JSON response formatter"""

    def format(self, data: Any) -> Dict[str, Any]:
        """Format data as JSON

        Args:
            data: Data to format

        Returns:
            JSON formatted data
        """
        if isinstance(data, dict):
            return {
                "success": True,
                "data": data,
            }
        elif isinstance(data, list):
            return {
                "success": True,
                "data": data,
                "count": len(data),
            }
        else:
            return {
                "success": True,
                "data": data,
            }

    def format_list(self, items: List[Any]) -> Dict[str, Any]:
        """Format list of items

        Args:
            items: List of items

        Returns:
            Formatted list
        """
        return {
            "success": True,
            "data": items,
            "count": len(items),
        }

    def format_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Format error response

        Args:
            error: Error dictionary

        Returns:
            Formatted error
        """
        return {
            "success": False,
            "error": error.get("message", "Unknown error"),
            "code": error.get("code", "UNKNOWN"),
            "details": error.get("details"),
        }


class PaginatedFormatter(BaseFormatter):
    """Paginated response formatter"""

    def format(self, data: Any, total: int = 0, skip: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Format data with pagination

        Args:
            data: Data to format
            total: Total count
            skip: Skip count
            limit: Limit count

        Returns:
            Paginated formatted data
        """
        items = data if isinstance(data, list) else [data]

        return {
            "success": True,
            "data": items,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "count": len(items),
                "pages": (total + limit - 1) // limit if limit > 0 else 0,
            },
        }

    def format_list(
        self, items: List[Any], total: int = 0, skip: int = 0, limit: int = 10
    ) -> Dict[str, Any]:
        """Format list with pagination

        Args:
            items: List of items
            total: Total count
            skip: Skip count
            limit: Limit count

        Returns:
            Paginated formatted list
        """
        return {
            "success": True,
            "data": items,
            "pagination": {
                "total": total,
                "skip": skip,
                "limit": limit,
                "count": len(items),
                "pages": (total + limit - 1) // limit if limit > 0 else 0,
            },
        }

    def format_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Format error response

        Args:
            error: Error dictionary

        Returns:
            Formatted error
        """
        return {
            "success": False,
            "error": error.get("message", "Unknown error"),
            "code": error.get("code", "UNKNOWN"),
            "details": error.get("details"),
        }


class EnvelopeFormatter(BaseFormatter):
    """Envelope response formatter with metadata"""

    def __init__(self, include_timestamp: bool = True, include_version: bool = True):
        """Initialize envelope formatter

        Args:
            include_timestamp: Include timestamp in response
            include_version: Include API version in response
        """
        self.include_timestamp = include_timestamp
        self.include_version = include_version

    def format(self, data: Any) -> Dict[str, Any]:
        """Format data with envelope

        Args:
            data: Data to format

        Returns:
            Envelope formatted data
        """
        from datetime import datetime

        envelope = {
            "success": True,
            "data": data,
        }

        if self.include_timestamp:
            envelope["timestamp"] = datetime.utcnow().isoformat()

        if self.include_version:
            envelope["api_version"] = "1.0"

        return envelope

    def format_list(self, items: List[Any]) -> Dict[str, Any]:
        """Format list with envelope

        Args:
            items: List of items

        Returns:
            Envelope formatted list
        """
        from datetime import datetime

        envelope = {
            "success": True,
            "data": items,
            "count": len(items),
        }

        if self.include_timestamp:
            envelope["timestamp"] = datetime.utcnow().isoformat()

        if self.include_version:
            envelope["api_version"] = "1.0"

        return envelope

    def format_error(self, error: Dict[str, Any]) -> Dict[str, Any]:
        """Format error response with envelope

        Args:
            error: Error dictionary

        Returns:
            Envelope formatted error
        """
        from datetime import datetime

        envelope = {
            "success": False,
            "error": error.get("message", "Unknown error"),
            "code": error.get("code", "UNKNOWN"),
            "details": error.get("details"),
        }

        if self.include_timestamp:
            envelope["timestamp"] = datetime.utcnow().isoformat()

        if self.include_version:
            envelope["api_version"] = "1.0"

        return envelope


class FormatterRegistry:
    """Registry for response formatters"""

    def __init__(self) -> None:
        """Initialize formatter registry"""
        self.formatters: Dict[str, BaseFormatter] = {
            "json": JSONFormatter(),
            "paginated": PaginatedFormatter(),
            "envelope": EnvelopeFormatter(),
        }

    def register(self, name: str, formatter: BaseFormatter) -> None:
        """Register a formatter

        Args:
            name: Formatter name
            formatter: Formatter instance
        """
        self.formatters[name] = formatter

    def get(self, name: str) -> Optional[BaseFormatter]:
        """Get a formatter by name

        Args:
            name: Formatter name

        Returns:
            Formatter instance or None
        """
        return self.formatters.get(name)

    def format(self, name: str, data: Any, **kwargs: Any) -> Any:
        """Format data using a formatter

        Args:
            name: Formatter name
            data: Data to format
            **kwargs: Additional arguments

        Returns:
            Formatted data
        """
        formatter = self.get(name)
        if formatter is None:
            return data

        return formatter.format(data, **kwargs)

    def format_list(self, name: str, items: List[Any], **kwargs: Any) -> Any:
        """Format list using a formatter

        Args:
            name: Formatter name
            items: List of items
            **kwargs: Additional arguments

        Returns:
            Formatted list
        """
        formatter = self.get(name)
        if formatter is None:
            return items

        return formatter.format_list(items, **kwargs)

    def format_error(self, name: str, error: Dict[str, Any]) -> Any:
        """Format error using a formatter

        Args:
            name: Formatter name
            error: Error dictionary

        Returns:
            Formatted error
        """
        formatter = self.get(name)
        if formatter is None:
            return error

        return formatter.format_error(error)


# Global formatter registry
_registry: Optional[FormatterRegistry] = None


def get_formatter_registry() -> FormatterRegistry:
    """Get global formatter registry

    Returns:
        FormatterRegistry instance
    """
    global _registry

    if _registry is None:
        _registry = FormatterRegistry()

    return _registry
