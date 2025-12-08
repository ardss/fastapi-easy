"""Utility modules for FastAPI-Easy"""

from __future__ import annotations

from .connection_manager import (
    ConnectionConfig,
    ConnectionManager,
    get_connection_manager,
    managed_connection,
    with_connection_manager,
)
from .filters import FilterParser
from .hot_reload_state import (
    StateManager,
    TokenStore,
    get_state_manager,
    persistent_state,
)
from .pagination import PaginationParams, paginate
from .query_params import QueryParams, as_query_params
from .sorters import SortParser
from .static_files import EnhancedStaticFiles, setup_static_files

__all__ = [
    # Existing utilities
    "PaginationParams",
    "paginate",
    "FilterParser",
    "SortParser",
    # Query parameter utilities
    "QueryParams",
    "as_query_params",
    # Static file serving
    "EnhancedStaticFiles",
    "setup_static_files",
    # Connection management
    "ConnectionManager",
    "ConnectionConfig",
    "managed_connection",
    "with_connection_manager",
    "get_connection_manager",
    # Hot reload state management
    "StateManager",
    "TokenStore",
    "get_state_manager",
    "persistent_state",
]
