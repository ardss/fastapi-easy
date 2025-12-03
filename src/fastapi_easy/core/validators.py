"""Input validation utilities for security"""

from typing import Any, List, Optional, Union
import re


class ValidationError(ValueError):
    """Validation error"""

    pass


class InputValidator:
    """Input validator for security"""

    # SQL keywords that should not appear in filter values
    SQL_KEYWORDS = {
        "SELECT",
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
        "EXEC",
        "EXECUTE",
        "UNION",
        "OR",
        "AND",
        "WHERE",
        "FROM",
        "JOIN",
        "GROUP",
        "ORDER",
        "HAVING",
        "LIMIT",
    }

    # Pattern for detecting SQL injection attempts
    SQL_INJECTION_PATTERN = re.compile(
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\b)|" r"(--|#|/\*|\*/|;|'|\")",
        re.IGNORECASE,
    )

    @classmethod
    def validate_field_name(cls, field_name: str) -> str:
        """Validate field name

        Args:
            field_name: Field name to validate

        Returns:
            Validated field name

        Raises:
            ValidationError: If field name is invalid
        """
        if not field_name:
            raise ValidationError("Field name cannot be empty")

        if not isinstance(field_name, str):
            raise ValidationError("Field name must be a string")

        # Allow only alphanumeric, underscore, and dot (for nested fields)
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", field_name):
            raise ValidationError(f"Invalid field name: {field_name}")

        return field_name

    @classmethod
    def validate_filter_value(cls, value: Any, operator: str = "exact") -> Any:
        """Validate filter value

        Args:
            value: Value to validate
            operator: Filter operator

        Returns:
            Validated value

        Raises:
            ValidationError: If value is invalid
        """
        if value is None:
            return None

        if not isinstance(value, (str, int, float, bool, list)):
            raise ValidationError(f"Invalid filter value type: {type(value)}")

        # For string values, check for SQL injection patterns
        if isinstance(value, str):
            # Check for SQL keywords
            value_upper = value.upper()
            for keyword in cls.SQL_KEYWORDS:
                if f" {keyword} " in f" {value_upper} ":
                    raise ValidationError(
                        f"Potential SQL injection detected: {keyword} found in value"
                    )

            # Check for SQL injection patterns
            if cls.SQL_INJECTION_PATTERN.search(value):
                raise ValidationError("Potential SQL injection pattern detected")

        # For list values (in operator), validate each item
        if isinstance(value, list):
            for item in value:
                cls.validate_filter_value(item, operator)

        return value

    @classmethod
    def validate_sort_field(cls, field_name: str) -> str:
        """Validate sort field name

        Args:
            field_name: Field name to validate

        Returns:
            Validated field name

        Raises:
            ValidationError: If field name is invalid
        """
        # Remove direction prefix if present
        if field_name.startswith("-"):
            field_name = field_name[1:]

        return cls.validate_field_name(field_name)

    @classmethod
    def validate_pagination_params(
        cls,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        max_limit: int = 1000,
    ) -> tuple[int, int]:
        """Validate pagination parameters

        Args:
            skip: Number of items to skip
            limit: Number of items to return
            max_limit: Maximum allowed limit

        Returns:
            Tuple of (skip, limit)

        Raises:
            ValidationError: If parameters are invalid
        """
        # Handle None values
        if skip is None:
            skip = 0
        if limit is None:
            limit = 10

        if not isinstance(skip, int) or skip < 0:
            raise ValidationError("skip must be a non-negative integer")

        if not isinstance(limit, int) or limit < 1:
            raise ValidationError("limit must be a positive integer")

        if limit > max_limit:
            raise ValidationError(f"limit cannot exceed {max_limit}")

        return skip, limit

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize string value

        Args:
            value: String to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string

        Raises:
            ValidationError: If string is invalid
        """
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")

        if len(value) > max_length:
            raise ValidationError(f"String exceeds maximum length of {max_length}")

        # Remove null bytes
        value = value.replace("\x00", "")

        return value


class FilterValidator:
    """Validator for filter operations"""

    def __init__(self, allowed_fields: Optional[List[str]] = None):
        """Initialize filter validator

        Args:
            allowed_fields: List of allowed filter fields
        """
        self.allowed_fields = allowed_fields or []

    def validate_filters(self, filters: dict) -> dict:
        """Validate filters dictionary

        Args:
            filters: Filters to validate

        Returns:
            Validated filters

        Raises:
            ValidationError: If any filter is invalid
        """
        validated = {}

        for key, filter_data in filters.items():
            if not isinstance(filter_data, dict):
                raise ValidationError(f"Filter {key} must be a dictionary")

            field = filter_data.get("field")
            operator = filter_data.get("operator", "exact")
            value = filter_data.get("value")

            # Validate field name
            if not field:
                raise ValidationError(f"Filter {key} missing field")

            field = InputValidator.validate_field_name(field)

            # Check if field is allowed
            if self.allowed_fields and field not in self.allowed_fields:
                raise ValidationError(f"Field {field} is not allowed for filtering")

            # Validate value
            value = InputValidator.validate_filter_value(value, operator)

            validated[key] = {
                "field": field,
                "operator": operator,
                "value": value,
            }

        return validated
