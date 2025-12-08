"""
Validation exception hierarchy for FastAPI-Easy.

This module provides comprehensive exceptions for validation failures
with detailed field-level information and suggestions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from .base import (
    ErrorCategory,
    ErrorCode,
    ErrorSeverity,
    FastAPIEasyException,
)


class ValidationException(FastAPIEasyException):
    """Base exception for validation failures."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=422,  # Unprocessable Entity
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            **kwargs,
        )

        if field:
            self.with_details(field=field, value=value)


class FieldValidationException(ValidationException):
    """Raised when a specific field fails validation."""

    def __init__(
        self,
        field: str,
        message: str,
        value: Any = None,
        expected_type: Optional[str] = None,
        **kwargs,
    ):
        full_message = f"Validation failed for field '{field}': {message}"

        super().__init__(
            message=full_message,
            field=field,
            value=value,
            **kwargs,
        )

        self.with_details(
            field=field,
            value=value,
            constraint=expected_type,
            suggestion=(
                f"Please provide a valid value for '{field}'"
                f"{f' (expected: {expected_type})' if expected_type else ''}"
            ),
        )


class TypeValidationException(FieldValidationException):
    """Raised when field value has wrong type."""

    def __init__(
        self,
        field: str,
        value: Any,
        expected_type: Union[type, str, List[Union[type, str]]],
        actual_type: Optional[type] = None,
        **kwargs,
    ):
        if isinstance(expected_type, list):
            type_names = [t if isinstance(t, str) else t.__name__ for t in expected_type]
            expected_str = " or ".join(type_names)
        else:
            expected_str = (
                expected_type if isinstance(expected_type, str) else expected_type.__name__
            )

        actual_str = actual_type.__name__ if actual_type else type(value).__name__

        message = f"Expected type {expected_str}, got {actual_str}"

        super().__init__(
            field=field,
            message=message,
            value=value,
            expected_type=expected_str,
            **kwargs,
        )

        self.with_context(
            expected_type=expected_str,
            actual_type=actual_str,
        )


class FormatValidationException(FieldValidationException):
    """Raised when field value doesn't match required format."""

    def __init__(
        self,
        field: str,
        value: Any,
        format_type: str,
        format_pattern: Optional[str] = None,
        **kwargs,
    ):
        message = f"Value does not match required format: {format_type}"

        super().__init__(
            field=field,
            message=message,
            value=value,
            **kwargs,
        )

        self.with_details(
            constraint=format_pattern,
            suggestion=(
                f"Please provide '{field}' in the correct {format_type} format"
                f"{f' (pattern: {format_pattern})' if format_pattern else ''}"
            ),
        )

        self.with_context(format_type=format_type, format_pattern=format_pattern)


class RangeValidationException(FieldValidationException):
    """Raised when field value is outside allowed range."""

    def __init__(
        self,
        field: str,
        value: Union[int, float],
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
        **kwargs,
    ):
        if min_value is not None and max_value is not None:
            message = f"Value must be between {min_value} and {max_value}"
        elif min_value is not None:
            message = f"Value must be at least {min_value}"
        elif max_value is not None:
            message = f"Value must be at most {max_value}"
        else:
            message = "Value is outside allowed range"

        super().__init__(
            field=field,
            message=message,
            value=value,
            **kwargs,
        )

        self.with_context(
            min_value=min_value,
            max_value=max_value,
            actual_value=value,
        )
        self.with_details(
            suggestion=(
                f"Please provide '{field}' with a value"
                f"{' >= ' + str(min_value) if min_value is not None else ''}"
                f"{' and ' if min_value is not None and max_value is not None else ''}"
                f"{' <= ' + str(max_value) if max_value is not None else ''}"
            ),
        )


class LengthValidationException(FieldValidationException):
    """Raised when field value has incorrect length."""

    def __init__(
        self,
        field: str,
        value: Union[str, List, Dict],
        min_length: Optional[int] = None,
        max_length: Optional[int] = None,
        actual_length: Optional[int] = None,
        **kwargs,
    ):
        actual_length = actual_length or len(value)

        if min_length is not None and max_length is not None:
            message = f"Length must be between {min_length} and {max_value}"
        elif min_length is not None:
            message = f"Length must be at least {min_length}"
        elif max_length is not None:
            message = f"Length must be at most {max_length}"
        else:
            message = "Length is outside allowed range"

        super().__init__(
            field=field,
            message=message,
            value=value,
            **kwargs,
        )

        self.with_context(
            min_length=min_length,
            max_length=max_length,
            actual_length=actual_length,
        )
        self.with_details(
            suggestion=(
                f"Please provide '{field}' with length"
                f"{' >= ' + str(min_length) if min_length is not None else ''}"
                f"{' and ' if min_length is not None and max_length is not None else ''}"
                f"{' <= ' + str(max_length) if max_length is not None else ''}"
            ),
        )


class RequiredFieldException(FieldValidationException):
    """Raised when required field is missing or empty."""

    def __init__(
        self,
        field: str,
        reason: Optional[str] = None,
        **kwargs,
    ):
        message = f"Field '{field}' is required"
        if reason:
            message += f": {reason}"

        super().__init__(
            field=field,
            message=message,
            value=None,
            **kwargs,
        )

        self.with_details(
            suggestion=f"Please provide a value for required field '{field}'",
        )


class UniqueConstraintException(FieldValidationException):
    """Raised when unique constraint is violated."""

    def __init__(
        self,
        field: str,
        value: Any,
        resource_type: Optional[str] = None,
        existing_id: Optional[Any] = None,
        **kwargs,
    ):
        message = f"Value for '{field}' must be unique"
        if resource_type:
            message += f" among {resource_type}"

        super().__init__(
            field=field,
            message=message,
            value=value,
            **kwargs,
        )

        self.with_context(
            resource_type=resource_type,
            existing_id=existing_id,
            unique_field=field,
        )
        self.with_details(
            suggestion=(
                f"Please provide a different value for '{field}'"
                f"{'. The value is already in use.' if not resource_type else f'. This value is already used by another {resource_type}.'}"
            ),
        )


class BusinessRuleValidationException(ValidationException):
    """Raised when business rule validation fails."""

    def __init__(
        self,
        rule: str,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        **kwargs,
    ):
        full_message = f"Business rule violation: {message}"

        super().__init__(
            message=full_message,
            field=field,
            value=value,
            **kwargs,
        )

        self.with_context(rule=rule)
        self.with_details(
            field=field,
            value=value,
            constraint=rule,
            suggestion=(
                "Please ensure your data complies with business rules\n"
                "If you believe this is an error, contact support"
            ),
        )


class ConditionalValidationException(ValidationException):
    """Raised when conditional validation fails."""

    def __init__(
        self,
        condition: str,
        field: str,
        message: str,
        dependent_field: Optional[str] = None,
        **kwargs,
    ):
        full_message = f"Conditional validation failed for '{field}': {message}"

        super().__init__(
            message=full_message,
            field=field,
            **kwargs,
        )

        self.with_context(
            condition=condition,
            dependent_field=dependent_field,
        )
        self.with_details(
            field=field,
            constraint=f"when {condition}",
            suggestion=(
                f"Please ensure '{field}' satisfies the condition: {condition}"
                f"{f' based on {dependent_field}' if dependent_field else ''}"
            ),
        )


class ValidationErrorList(ValidationException):
    """Exception for multiple validation errors."""

    def __init__(
        self,
        errors: List[Dict[str, Any]],
        **kwargs,
    ):
        message = f"Validation failed with {len(errors)} error{'s' if len(errors) != 1 else ''}"

        super().__init__(
            message=message,
            **kwargs,
        )

        self.errors = errors
        self.with_context(error_count=len(errors))
        self.with_details(
            suggestion=(
                "Please fix all validation errors before retrying\n"
                "Check each field for specific requirements"
            ),
        )

    def to_dict(self, include_debug: bool = False) -> Dict[str, Any]:
        """Override to include all validation errors."""
        base_dict = super().to_dict(include_debug=include_debug)

        # Add individual errors
        base_dict["error"]["validation_errors"] = self.errors

        return base_dict


class SchemaValidationException(ValidationException):
    """Raised when data schema validation fails."""

    def __init__(
        self,
        schema_name: str,
        errors: List[str],
        data_path: Optional[str] = None,
        **kwargs,
    ):
        message = f"Schema '{schema_name}' validation failed"
        if data_path:
            message += f" at path: {data_path}"

        super().__init__(
            message=message,
            **kwargs,
        )

        self.with_context(
            schema_name=schema_name,
            data_path=data_path,
        )
        self.with_details(
            debug_info={"schema_errors": errors},
            suggestion=(
                "Please ensure your data matches the required schema\n"
                "Check the schema documentation for proper structure"
            ),
        )


class CrossFieldValidationException(ValidationException):
    """Raised when cross-field validation fails."""

    def __init__(
        self,
        fields: List[str],
        rule: str,
        message: str,
        **kwargs,
    ):
        full_message = f"Cross-field validation failed: {message}"

        super().__init__(
            message=full_message,
            **kwargs,
        )

        self.with_context(
            fields=fields,
            rule=rule,
        )
        self.with_details(
            suggestion=(
                f"Please ensure the fields {', '.join(fields)} satisfy the rule: {rule}\n"
                "These fields are related and must be consistent"
            ),
        )


class DependentFieldException(ValidationException):
    """Raised when dependent field validation fails."""

    def __init__(
        self,
        field: str,
        dependent_field: str,
        dependency_type: str,
        **kwargs,
    ):
        message = f"Field '{field}' requires '{dependent_field}' ({dependency_type})"

        super().__init__(
            message=message,
            field=field,
            **kwargs,
        )

        self.with_context(
            dependent_field=dependent_field,
            dependency_type=dependency_type,
        )
        self.with_details(
            suggestion=(
                f"Please provide '{dependent_field}' along with '{field}'\n"
                "These fields are related and must be provided together"
            ),
        )
