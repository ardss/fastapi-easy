"""Query projection optimization for reducing network transfer"""

import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class QueryProjection:
    """Query projection for selecting specific fields"""

    def __init__(self, fields: List[str]):
        """Initialize query projection

        Args:
            fields: List of field names to include
        """
        self.fields = fields

    def get_fields(self) -> List[str]:
        """Get selected fields

        Returns:
            List of field names
        """
        return self.fields

    def add_field(self, field: str) -> "QueryProjection":
        """Add a field to projection

        Args:
            field: Field name to add

        Returns:
            Self for chaining
        """
        if field not in self.fields:
            self.fields.append(field)
        return self

    def remove_field(self, field: str) -> "QueryProjection":
        """Remove a field from projection

        Args:
            field: Field name to remove

        Returns:
            Self for chaining
        """
        if field in self.fields:
            self.fields.remove(field)
        return self

    def has_field(self, field: str) -> bool:
        """Check if field is in projection

        Args:
            field: Field name to check

        Returns:
            True if field is included
        """
        return field in self.fields

    def apply_to_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply projection to dictionary

        Args:
            data: Dictionary to project

        Returns:
            Projected dictionary with only selected fields

        Raises:
            TypeError: If data is not a dictionary
        """
        if data is None:
            logger.warning("Projection applied to None data, returning empty dict")
            return {}

        if not isinstance(data, dict):
            logger.error(f"Expected dict for projection, got {type(data)}")
            raise TypeError(f"Expected dict, got {type(data).__name__}")

        try:
            return {k: v for k, v in data.items() if k in self.fields}
        except Exception as e:
            logger.error(f"Failed to apply projection: {str(e)}")
            raise

    def apply_to_list(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply projection to list of dictionaries

        Args:
            data_list: List of dictionaries to project

        Returns:
            List of projected dictionaries
        """
        return [self.apply_to_dict(item) for item in data_list]

    def validate_fields(self, available_fields: List[str]) -> bool:
        """Validate that all projection fields exist

        Args:
            available_fields: List of available field names

        Returns:
            True if all projection fields are available, False otherwise
        """
        invalid = self.get_invalid_fields(available_fields)
        if invalid:
            logger.warning(f"Invalid projection fields: {invalid}")
            return False
        return True

    def validate_fields_strict(self, available_fields: List[str]) -> bool:
        """Validate fields and raise exception if invalid

        Args:
            available_fields: List of available field names

        Returns:
            True if all projection fields are available

        Raises:
            ValueError: If invalid fields are found
        """
        invalid = self.get_invalid_fields(available_fields)
        if invalid:
            logger.error(f"Invalid projection fields: {invalid}")
            raise ValueError(f"Invalid projection fields: {invalid}")
        return True

    def get_invalid_fields(self, available_fields: List[str]) -> List[str]:
        """Get fields that don't exist in available fields

        Args:
            available_fields: List of available field names

        Returns:
            List of invalid fields
        """
        return [field for field in self.fields if field not in available_fields]


class ProjectionBuilder:
    """Builder for creating query projections"""

    def __init__(self):
        """Initialize projection builder"""
        self.fields: List[str] = []

    def add(self, field: str) -> "ProjectionBuilder":
        """Add a field

        Args:
            field: Field name to add

        Returns:
            Self for chaining
        """
        if field not in self.fields:
            self.fields.append(field)
        return self

    def add_multiple(self, fields: List[str]) -> "ProjectionBuilder":
        """Add multiple fields

        Args:
            fields: List of field names to add

        Returns:
            Self for chaining
        """
        for field in fields:
            self.add(field)
        return self

    def exclude(self, field: str) -> "ProjectionBuilder":
        """Exclude a field

        Args:
            field: Field name to exclude

        Returns:
            Self for chaining
        """
        if field in self.fields:
            self.fields.remove(field)
        return self

    def build(self) -> QueryProjection:
        """Build the projection

        Returns:
            QueryProjection instance
        """
        return QueryProjection(self.fields.copy())


def create_projection(*fields: str) -> QueryProjection:
    """Create a query projection

    Args:
        *fields: Field names to include

    Returns:
        QueryProjection instance
    """
    return QueryProjection(list(fields))


def create_projection_builder() -> ProjectionBuilder:
    """Create a projection builder

    Returns:
        ProjectionBuilder instance
    """
    return ProjectionBuilder()
