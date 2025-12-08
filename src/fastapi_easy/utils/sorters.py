"""Sort parsing utilities for FastAPI-Easy"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class SortParser:
    """Parser for sort query parameters

    Supports sorting with:
    - Ascending: field or field=asc
    - Descending: -field or field=desc
    - Multiple fields: field1,-field2,field3
    """

    @classmethod
    def parse(
        cls,
        sort_param: Optional[str] = None,
        allowed_fields: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Parse sort query parameter

        Args:
            sort_param: Sort parameter string (e.g., "field1,-field2")
            allowed_fields: List of allowed sort fields

        Returns:
            Dictionary of field -> direction mappings
        """
        if not sort_param:
            return {}

        sorts = {}

        # Split by comma
        for field_spec in sort_param.split(","):
            field_spec = field_spec.strip()

            if not field_spec:
                continue

            # Check for descending order
            if field_spec.startswith("-"):
                field = field_spec[1:]
                direction = "desc"
            else:
                field = field_spec
                direction = "asc"

            # Check if field is allowed
            if allowed_fields and field not in allowed_fields:
                continue

            sorts[field] = direction

        return sorts

    @classmethod
    def parse_from_dict(
        cls,
        query_params: Dict[str, Any],
        allowed_fields: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """Parse sort from query parameters dictionary

        Args:
            query_params: Query parameters
            allowed_fields: List of allowed sort fields

        Returns:
            Dictionary of field -> direction mappings
        """
        sort_param = query_params.get("sort")
        if isinstance(sort_param, list):
            sort_param = sort_param[0] if sort_param else None

        return cls.parse(sort_param, allowed_fields)

    @classmethod
    def to_list(cls, sorts: Dict[str, str]) -> List[Tuple[str, str]]:
        """Convert sorts dictionary to list of tuples

        Args:
            sorts: Dictionary of sorts

        Returns:
            List of (field, direction) tuples
        """
        return list(sorts.items())
