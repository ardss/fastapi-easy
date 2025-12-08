"""Filter parsing utilities for FastAPI-Easy"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class FilterParser:
    """Parser for filter query parameters

    Supports multiple filter operators:
    - exact: field=value
    - ne: field__ne=value (not equal)
    - gt: field__gt=value (greater than)
    - gte: field__gte=value (greater than or equal)
    - lt: field__lt=value (less than)
    - lte: field__lte=value (less than or equal)
    - in: field__in=v1,v2,v3 (in list)
    - like: field__like=pattern (contains)
    - ilike: field__ilike=pattern (case-insensitive contains)
    """

    OPERATORS = {
        "ne": "not_equal",
        "gt": "greater_than",
        "gte": "greater_than_or_equal",
        "lt": "less_than",
        "lte": "less_than_or_equal",
        "in": "in_list",
        "like": "contains",
        "ilike": "case_insensitive_contains",
    }

    @classmethod
    def parse(
        cls,
        query_params: Dict[str, Any],
        allowed_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Parse filter query parameters

        Args:
            query_params: Query parameters from request
            allowed_fields: List of allowed filter fields

        Returns:
            Dictionary of parsed filters
        """
        filters = {}

        for key, value in query_params.items():
            if key.startswith("_"):
                continue

            # Check if field is allowed
            if allowed_fields and key.split("__")[0] not in allowed_fields:
                continue

            # Parse field and operator
            if "__" in key:
                field, operator = key.rsplit("__", 1)
                if operator in cls.OPERATORS:
                    filters[key] = {
                        "field": field,
                        "operator": operator,  # Use the operator key, not the mapped value
                        "value": value,
                    }
                else:
                    # Treat as exact match
                    filters[key] = {
                        "field": key,
                        "operator": "exact",
                        "value": value,
                    }
            else:
                # Exact match
                filters[key] = {
                    "field": key,
                    "operator": "exact",
                    "value": value,
                }

        return filters

    @classmethod
    def get_operator_description(cls, operator: str) -> str:
        """Get description of an operator

        Args:
            operator: Operator name

        Returns:
            Operator description
        """
        return cls.OPERATORS.get(operator, "exact match")
