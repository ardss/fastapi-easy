"""Enhanced input validation and sanitization for FastAPI-Easy"""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

logger = logging.getLogger(__name__)


class InputValidationError(Exception):
    """Input validation error"""

    pass


class SecurityValidator:
    """Security-focused input validator and sanitizer"""

    # SQL Injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|\#|\/\*)",  # SQL comments
        r"(\bOR\b.*=.*\bOR\b)",  # OR 1=1
        r"(\bAND\b.*=.*\bAND\b)",  # AND 1=1
        r"(;|\'|\"|`|\\|%)",  # Special characters
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # onclick=, onload=, etc.
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<form[^>]*>",
        r"<input[^>]*>",
    ]

    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\.[\\/]",  # ../ or ..\
        r"[\\/]\.\.[\\/]",  # /anything/../anything
        r"(/etc/passwd|/etc/shadow)",
        r"(%2e%2e[\\/])",  # URL encoded ../
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]]",  # Command separators
        r"\b(curl|wget|nc|netcat|ssh|ftp)\b",
        r"\b(rm|mv|cp|cat|ls|ps|kill)\b",
        r"\b(python|perl|ruby|bash|sh|cmd|powershell)\b",
    ]

    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        """Sanitize string input

        Args:
            value: Input string
            max_length: Maximum allowed length

        Returns:
            Sanitized string

        Raises:
            InputValidationError: If input is invalid
        """
        if not isinstance(value, str):
            raise InputValidationError("Input must be a string")

        # Length check
        if len(value) > max_length:
            raise InputValidationError(f"Input exceeds maximum length of {max_length}")

        # Remove null bytes
        value = value.replace("\x00", "")

        # HTML escape
        value = html.escape(value, quote=True)

        # URL decode if needed
        try:
            value = unquote(value)
        except Exception:
            pass

        return value.strip()

    @classmethod
    def validate_field_name(cls, field_name: str) -> str:
        """Validate field name to prevent injection

        Args:
            field_name: Field name to validate

        Returns:
            Validated field name

        Raises:
            InputValidationError: If field name is invalid
        """
        if not isinstance(field_name, str):
            raise InputValidationError("Field name must be a string")

        # Allow only alphanumeric, underscore, and dot
        pattern = r"^[a-zA-Z_][a-zA-Z0-9_.]*$"
        if not re.match(pattern, field_name):
            raise InputValidationError(f"Invalid field name: {field_name}")

        # Check for dangerous patterns
        dangerous_patterns = [
            r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b",
            r"[;\"'`\\]",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, field_name, re.IGNORECASE):
                raise InputValidationError(f"Dangerous pattern in field name: {field_name}")

        return field_name

    @classmethod
    def validate_sql_value(cls, value: Any) -> Any:
        """Validate SQL value to prevent injection

        Args:
            value: Value to validate

        Returns:
            Validated value

        Raises:
            InputValidationError: If value is suspicious
        """
        if isinstance(value, str):
            # Check for SQL injection patterns
            for pattern in cls.SQL_INJECTION_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                    logger.warning(f"SQL injection attempt detected: {value[:100]}...")
                    raise InputValidationError("Suspicious input detected")

        elif isinstance(value, (list, tuple)):
            # Validate each item in list/tuple
            return [cls.validate_sql_value(item) for item in value]

        elif isinstance(value, dict):
            # Validate each key-value pair
            return {
                cls.validate_field_name(str(key)): cls.validate_sql_value(val)
                for key, val in value.items()
            }

        return value

    @classmethod
    def validate_and_sanitize_input(
        cls, data: Dict[str, Any], allowed_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate and sanitize input data

        Args:
            data: Input data dictionary
            allowed_fields: List of allowed field names (optional)

        Returns:
            Sanitized data dictionary

        Raises:
            InputValidationError: If input is invalid
        """
        if not isinstance(data, dict):
            raise InputValidationError("Input must be a dictionary")

        sanitized = {}

        for key, value in data.items():
            # Validate field name
            safe_key = cls.validate_field_name(str(key))

            # Check if field is allowed
            if allowed_fields and safe_key not in allowed_fields:
                logger.warning(f"Unexpected field in input: {safe_key}")
                continue

            # Sanitize string values
            if isinstance(value, str):
                sanitized[safe_key] = cls.sanitize_string(value)
            elif isinstance(value, (list, dict)):
                sanitized[safe_key] = cls.validate_and_sanitize_input(
                    value if isinstance(value, dict) else {str(i): v for i, v in enumerate(value)}
                )
            else:
                sanitized[safe_key] = cls.validate_sql_value(value)

        return sanitized

    @classmethod
    def validate_pagination_params(cls, skip: int = 0, limit: int = 100) -> tuple[int, int]:
        """Validate pagination parameters

        Args:
            skip: Number of items to skip
            limit: Number of items to return

        Returns:
            Tuple of (skip, limit)

        Raises:
            InputValidationError: If parameters are invalid
        """
        # Validate skip
        if not isinstance(skip, int) or skip < 0:
            raise InputValidationError("Skip must be a non-negative integer")

        if skip > 10000:  # Prevent excessive pagination
            raise InputValidationError("Skip value too large")

        # Validate limit
        if not isinstance(limit, int) or limit < 1:
            raise InputValidationError("Limit must be a positive integer")

        if limit > 1000:  # Reasonable maximum
            raise InputValidationError("Limit value too large")

        return skip, limit

    @classmethod
    def validate_sort_params(
        cls, sort_fields: Dict[str, str], allowed_fields: List[str]
    ) -> Dict[str, str]:
        """Validate sort parameters

        Args:
            sort_fields: Dictionary of field -> direction
            allowed_fields: List of allowed sort fields

        Returns:
            Validated sort parameters

        Raises:
            InputValidationError: If parameters are invalid
        """
        validated = {}

        for field, direction in sort_fields.items():
            # Validate field name
            safe_field = cls.validate_field_name(field)

            # Check if field is allowed
            if safe_field not in allowed_fields:
                logger.warning(f"Sort field not allowed: {safe_field}")
                continue

            # Validate direction
            safe_direction = str(direction).upper()
            if safe_direction not in ["ASC", "DESC"]:
                safe_direction = "ASC"  # Default to ascending

            validated[safe_field] = safe_direction

        return validated

    @classmethod
    def check_xss(cls, value: str) -> bool:
        """Check for XSS patterns

        Args:
            value: String to check

        Returns:
            True if XSS detected
        """
        if not isinstance(value, str):
            return False

        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE | re.MULTILINE | re.DOTALL):
                return True

        return False

    @classmethod
    def check_path_traversal(cls, path: str) -> bool:
        """Check for path traversal attempts

        Args:
            path: Path to check

        Returns:
            True if path traversal detected
        """
        if not isinstance(path, str):
            return False

        for pattern in cls.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return True

        return False

    @classmethod
    def check_command_injection(cls, value: str) -> bool:
        """Check for command injection attempts

        Args:
            value: String to check

        Returns:
            True if command injection detected
        """
        if not isinstance(value, str):
            return False

        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True

        return False

    @classmethod
    def comprehensive_validation(cls, data: Any) -> Any:
        """Perform comprehensive security validation

        Args:
            data: Data to validate

        Returns:
            Validated data

        Raises:
            InputValidationError: If any security issue is detected
        """
        if isinstance(data, str):
            # Check all security issues
            if cls.check_xss(data):
                raise InputValidationError("XSS detected in input")
            if cls.check_path_traversal(data):
                raise InputValidationError("Path traversal detected in input")
            if cls.check_command_injection(data):
                raise InputValidationError("Command injection detected in input")
            if cls.validate_sql_value(data) != data:
                raise InputValidationError("SQL injection detected in input")

            # Return sanitized string
            return cls.sanitize_string(data)

        elif isinstance(data, dict):
            # Recursively validate dictionary
            return {
                cls.validate_field_name(str(key)): cls.comprehensive_validation(value)
                for key, value in data.items()
            }

        elif isinstance(data, (list, tuple)):
            # Recursively validate list/tuple
            return [cls.comprehensive_validation(item) for item in data]

        else:
            # Return other types as-is after SQL validation
            return cls.validate_sql_value(data)


# Pydantic validators for easy integration
def sanitize_string_validator(max_length: int = 1000):
    """Pydantic validator for string sanitization"""

    def validator_func(v):
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        return SecurityValidator.sanitize_string(v, max_length)

    return validator_func


def validate_field_name_validator():
    """Pydantic validator for field names"""

    def validator_func(v):
        if not isinstance(v, str):
            raise ValueError("Must be a string")
        return SecurityValidator.validate_field_name(v)

    return validator_func


def validate_email_validator():
    """Enhanced email validator"""

    def validator_func(v):
        if not isinstance(v, str):
            raise ValueError("Must be a string")

        # Basic email pattern
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")

        # Check for dangerous patterns
        if SecurityValidator.check_xss(v) or SecurityValidator.check_sql_injection(v):
            raise ValueError("Suspicious email detected")

        return v.lower().strip()

    return validator_func


def validate_password_validator():
    """Enhanced password validator"""

    def validator_func(v):
        if not isinstance(v, str):
            raise ValueError("Must be a string")

        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")

        if len(v) > 128:
            raise ValueError("Password too long")

        # Check for common weak passwords
        weak_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
        if v.lower() in weak_passwords:
            raise ValueError("Password is too common")

        # Require at least one letter and one digit
        if not re.search(r"[a-zA-Z]", v) or not re.search(r"\d", v):
            raise ValueError("Password must contain both letters and numbers")

        return v

    return validator_func


# Helper function to check SQL injection
def check_sql_injection(value: str) -> bool:
    """Check if string contains SQL injection patterns"""
    if not isinstance(value, str):
        return False

    for pattern in SecurityValidator.SQL_INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE | re.MULTILINE | re.DOTALL):
            return True

    return False
