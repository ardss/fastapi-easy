"""
Configuration exception hierarchy for FastAPI-Easy.

This module provides exceptions for configuration-related errors
with detailed information about missing or invalid settings.
"""

from __future__ import annotations

from typing import Any, List, Optional

from .base import (
    ErrorCategory,
    ErrorCode,
    ErrorSeverity,
    FastAPIEasyException,
)


class ConfigurationException(FastAPIEasyException):
    """Base exception for configuration errors."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_CONFIGURATION,
            status_code=500,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs,
        )

        self.with_context(
            config_key=config_key,
            config_file=config_file,
        )


class MissingConfigurationException(ConfigurationException):
    """Raised when required configuration is missing."""

    def __init__(
        self,
        config_key: str,
        config_section: Optional[str] = None,
        config_file: Optional[str] = None,
        environment_variable: Optional[str] = None,
        **kwargs,
    ):
        message = f"Missing required configuration: {config_key}"
        if config_section:
            message += f" (section: {config_section})"

        super().__init__(
            message=message,
            config_key=config_key,
            config_file=config_file,
            code=ErrorCode.MISSING_CONFIGURATION,
            **kwargs,
        )

        self.with_context(
            config_section=config_section,
            environment_variable=environment_variable,
        )
        self.with_details(
            field=config_key,
            suggestion=(
                f"Please provide configuration for '{config_key}'\n"
                f"Options:\n"
                f"1. Add to configuration file{' (' + config_file + ')' if config_file else ''}\n"
                f"2. Set environment variable{' (' + environment_variable + ')' if environment_variable else ''}\n"
                f"3. Pass as application parameter"
            ),
        )


class InvalidConfigurationException(ConfigurationException):
    """Raised when configuration value is invalid."""

    def __init__(
        self,
        config_key: str,
        value: Any,
        reason: str,
        expected_type: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs,
    ):
        message = f"Invalid configuration for '{config_key}': {reason}"
        if expected_type:
            message += f" (expected: {expected_type})"

        super().__init__(
            message=message,
            config_key=config_key,
            config_file=config_file,
            **kwargs,
        )

        self.with_context(
            invalid_value=value,
            expected_type=expected_type,
            validation_reason=reason,
        )
        self.with_details(
            field=config_key,
            value=str(value),
            constraint=expected_type,
            suggestion=(
                f"Please fix configuration for '{config_key}'\n"
                f"Expected: {expected_type or reason}\n"
                f"Current value: {value}"
            ),
        )


class EnvironmentConfigurationException(ConfigurationException):
    """Raised when environment configuration has issues."""

    def __init__(
        self,
        environment: str,
        issue: str,
        details: Optional[str] = None,
        **kwargs,
    ):
        message = f"Environment configuration error in '{environment}': {issue}"
        if details:
            message += f" - {details}"

        super().__init__(
            message=message,
            code=ErrorCode.ENVIRONMENT_CONFIGURATION_ERROR,
            **kwargs,
        )

        self.with_context(
            environment=environment,
            environment_issue=issue,
        )
        self.with_details(
            suggestion=(
                "Environment configuration solutions:\n"
                "1. Check environment-specific configuration files\n"
                "2. Verify environment variables are set correctly\n"
                "3. Ensure environment detection is working\n"
                "4. Check configuration inheritance"
            ),
        )


class SecurityConfigurationException(ConfigurationException):
    """Raised when security configuration is inadequate or missing."""

    def __init__(
        self,
        security_issue: str,
        severity: str = "high",
        config_key: Optional[str] = None,
        **kwargs,
    ):
        message = f"Security configuration issue: {security_issue}"

        super().__init__(
            message=message,
            config_key=config_key,
            code=ErrorCode.SECURITY_CONFIGURATION_ERROR,
            severity=ErrorSeverity.CRITICAL if severity == "critical" else ErrorSeverity.HIGH,
            **kwargs,
        )

        self.with_context(
            security_issue=security_issue,
            security_severity=severity,
        )
        self.with_details(
            suggestion=(
                "Security configuration recommendations:\n"
                "1. Review security best practices\n"
                "2. Ensure all security settings are properly configured\n"
                "3. Use environment variables for sensitive data\n"
                "4. Implement proper key rotation\n"
                "5. Enable security auditing and logging"
            ),
            documentation_url="https://docs.fastapi-easy.com/security/configuration",
        )


class ConfigurationConflictException(ConfigurationException):
    """Raised when configuration conflicts are detected."""

    def __init__(
        self,
        conflict_source: List[str],
        config_key: str,
        conflicting_values: List[Any],
        **kwargs,
    ):
        message = f"Configuration conflict for '{config_key}'"
        if conflict_source:
            message += f" between: {', '.join(conflict_source)}"

        super().__init__(
            message=message,
            config_key=config_key,
            **kwargs,
        )

        self.with_context(
            conflict_sources=conflict_source,
            conflicting_values=conflicting_values,
        )
        self.with_details(
            suggestion=(
                "Configuration conflict resolution:\n"
                "1. Prioritize configuration sources correctly\n"
                "2. Remove or update conflicting values\n"
                "3. Use explicit configuration to override\n"
                "4. Check configuration loading order"
            ),
        )


class ConfigurationLoadException(ConfigurationException):
    """Raised when configuration cannot be loaded."""

    def __init__(
        self,
        source: str,
        error_detail: Optional[str] = None,
        **kwargs,
    ):
        message = f"Failed to load configuration from {source}"
        if error_detail:
            message += f": {error_detail}"

        super().__init__(
            message=message,
            **kwargs,
        )

        self.with_context(
            configuration_source=source,
            load_error=error_detail,
        )
        self.with_details(
            suggestion=(
                "Configuration loading solutions:\n"
                "1. Check file permissions and accessibility\n"
                "2. Verify configuration file format (JSON, YAML, TOML)\n"
                "3. Ensure all required files exist\n"
                "4. Check for syntax errors in configuration files"
            ),
        )


class ConfigurationSchemaException(ConfigurationException):
    """Raised when configuration doesn't match expected schema."""

    def __init__(
        self,
        schema_errors: List[str],
        config_file: Optional[str] = None,
        **kwargs,
    ):
        message = "Configuration schema validation failed"
        if config_file:
            message += f" in {config_file}"

        super().__init__(
            message=message,
            config_file=config_file,
            **kwargs,
        )

        self.with_context(
            schema_errors=schema_errors,
            error_count=len(schema_errors),
        )
        self.with_details(
            debug_info={"schema_errors": schema_errors},
            suggestion=(
                "Schema validation solutions:\n"
                "1. Fix schema validation errors in configuration\n"
                "2. Reference configuration schema documentation\n"
                "3. Use configuration validation tools\n"
                "4. Check for missing required fields"
            ),
        )


class ConfigurationVersionException(ConfigurationException):
    """Raised when configuration version is incompatible."""

    def __init__(
        self,
        current_version: str,
        required_version: str,
        compatibility_issue: str,
        **kwargs,
    ):
        message = f"Configuration version {current_version} is incompatible"
        message += f" (requires: {required_version})"
        message += f": {compatibility_issue}"

        super().__init__(
            message=message,
            **kwargs,
        )

        self.with_context(
            current_version=current_version,
            required_version=required_version,
            compatibility_issue=compatibility_issue,
        )
        self.with_details(
            suggestion=(
                "Version compatibility solutions:\n"
                "1. Update configuration to required version\n"
                "2. Check migration guide for version changes\n"
                "3. Use configuration migration tools\n"
                "4. Verify backward compatibility"
            ),
            documentation_url="https://docs.fastapi-easy.com/configuration/versioning",
        )
