"""Tests for error handling system"""

import pytest
from fastapi_easy.core.errors import (
    ErrorCode,
    AppError,
    NotFoundError,
    ValidationError,
    PermissionDeniedError,
    ConflictError,
    UnauthorizedError,
    BadRequestError,
)


class TestErrorCode:
    """Test error code enum"""
    
    def test_error_codes_exist(self):
        """Test that all error codes are defined"""
        assert ErrorCode.NOT_FOUND.value == "NOT_FOUND"
        assert ErrorCode.VALIDATION_ERROR.value == "VALIDATION_ERROR"
        assert ErrorCode.PERMISSION_DENIED.value == "PERMISSION_DENIED"
        assert ErrorCode.CONFLICT.value == "CONFLICT"
        assert ErrorCode.INTERNAL_ERROR.value == "INTERNAL_ERROR"
        assert ErrorCode.UNAUTHORIZED.value == "UNAUTHORIZED"
        assert ErrorCode.BAD_REQUEST.value == "BAD_REQUEST"


class TestAppError:
    """Test base application error"""
    
    def test_app_error_creation(self):
        """Test creating an app error"""
        error = AppError(
            code=ErrorCode.INTERNAL_ERROR,
            status_code=500,
            message="Something went wrong",
            details={"reason": "database_error"},
        )
        
        assert error.code == ErrorCode.INTERNAL_ERROR
        assert error.status_code == 500
        assert error.message == "Something went wrong"
        assert error.details["reason"] == "database_error"
    
    def test_app_error_to_dict(self):
        """Test converting error to dictionary"""
        error = AppError(
            code=ErrorCode.INTERNAL_ERROR,
            status_code=500,
            message="Error message",
            details={"key": "value"},
        )
        
        result = error.to_dict()
        
        assert result["code"] == "INTERNAL_ERROR"
        assert result["message"] == "Error message"
        assert result["details"]["key"] == "value"
    
    def test_app_error_is_exception(self):
        """Test that AppError is an exception"""
        error = AppError(
            code=ErrorCode.INTERNAL_ERROR,
            status_code=500,
            message="Test error",
        )
        
        assert isinstance(error, Exception)


class TestNotFoundError:
    """Test not found error"""
    
    def test_not_found_error(self):
        """Test creating a not found error"""
        error = NotFoundError("User", 123)
        
        assert error.code == ErrorCode.NOT_FOUND
        assert error.status_code == 404
        assert "User" in error.message
        assert "123" in error.message
        assert error.details["resource"] == "User"
        assert error.details["id"] == "123"


class TestValidationError:
    """Test validation error"""
    
    def test_validation_error(self):
        """Test creating a validation error"""
        error = ValidationError("email", "Invalid email format")
        
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert error.status_code == 422
        assert "email" in error.message
        assert error.details["field"] == "email"
        assert error.details["message"] == "Invalid email format"


class TestPermissionDeniedError:
    """Test permission denied error"""
    
    def test_permission_denied_error(self):
        """Test creating a permission denied error"""
        error = PermissionDeniedError("delete", "Admin access required")
        
        assert error.code == ErrorCode.PERMISSION_DENIED
        assert error.status_code == 403
        assert "delete" in error.message
        assert error.details["action"] == "delete"
        assert error.details["reason"] == "Admin access required"


class TestConflictError:
    """Test conflict error"""
    
    def test_conflict_error(self):
        """Test creating a conflict error"""
        error = ConflictError(
            "Resource already exists",
            details={"resource_id": "123"},
        )
        
        assert error.code == ErrorCode.CONFLICT
        assert error.status_code == 409
        assert error.message == "Resource already exists"
        assert error.details["resource_id"] == "123"


class TestUnauthorizedError:
    """Test unauthorized error"""
    
    def test_unauthorized_error(self):
        """Test creating an unauthorized error"""
        error = UnauthorizedError("Invalid credentials")
        
        assert error.code == ErrorCode.UNAUTHORIZED
        assert error.status_code == 401
        assert error.message == "Invalid credentials"


class TestBadRequestError:
    """Test bad request error"""
    
    def test_bad_request_error(self):
        """Test creating a bad request error"""
        error = BadRequestError(
            "Invalid request format",
            details={"field": "data"},
        )
        
        assert error.code == ErrorCode.BAD_REQUEST
        assert error.status_code == 400
        assert error.message == "Invalid request format"
        assert error.details["field"] == "data"
