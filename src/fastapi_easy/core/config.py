"""Configuration system for FastAPI-Easy"""

from dataclasses import dataclass, field
from typing import List, Type, Optional, Dict, Any


@dataclass
class CRUDConfig:
    """CRUD Router Configuration

    Centralized configuration for all CRUD operations.
    """

    # Feature toggles
    enable_filters: bool = True
    enable_sorters: bool = True
    enable_pagination: bool = True
    enable_soft_delete: bool = False
    enable_audit: bool = False
    enable_bulk_operations: bool = False

    # Filter configuration
    filter_fields: Optional[List[str]] = None

    # Sorter configuration
    sort_fields: Optional[List[str]] = None
    default_sort: Optional[str] = None

    # Pagination configuration
    default_limit: int = 10
    max_limit: int = 100

    # Soft delete configuration
    deleted_at_field: str = "deleted_at"

    # Error handling
    include_error_details: bool = True
    log_errors: bool = True

    # Safety settings
    enable_delete_all: bool = False  # Disabled by default for safety

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate configuration

        Raises:
            ValueError: If configuration is invalid
        """
        if self.default_limit <= 0:
            raise ValueError("default_limit must be greater than 0")

        if self.max_limit <= 0:
            raise ValueError("max_limit must be greater than 0")

        if self.default_limit > self.max_limit:
            raise ValueError("default_limit cannot be greater than max_limit")

        if self.filter_fields is not None and not isinstance(self.filter_fields, list):
            raise ValueError("filter_fields must be a list or None")

        if self.sort_fields is not None and not isinstance(self.sort_fields, list):
            raise ValueError("sort_fields must be a list or None")

        if not isinstance(self.deleted_at_field, str) or not self.deleted_at_field:
            raise ValueError("deleted_at_field must be a non-empty string")
