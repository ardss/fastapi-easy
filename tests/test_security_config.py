"""Tests for security config"""

import pytest

from fastapi_easy.security.audit_log import AuditLogger
from fastapi_easy.security.jwt_auth import JWTAuth
from fastapi_easy.security.permission_loader import StaticPermissionLoader
from fastapi_easy.security.resource_checker import StaticResourceChecker
from fastapi_easy.security.security_config import SecurityConfig


class TestSecurityConfig:
    """Test security config"""

    def test_init_valid(self):
        """Test initialization with valid parameters"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        config = SecurityConfig(jwt_auth=jwt_auth)

        assert config.jwt_auth is jwt_auth
        assert config.permission_loader is None
        assert config.resource_checker is None
        assert config.audit_logger is not None

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        permission_loader = StaticPermissionLoader({"user1": ["read"]})
        resource_checker = StaticResourceChecker({})
        audit_logger = AuditLogger()

        config = SecurityConfig(
            jwt_auth=jwt_auth,
            permission_loader=permission_loader,
            resource_checker=resource_checker,
            audit_logger=audit_logger,
        )

        assert config.jwt_auth is jwt_auth
        assert config.permission_loader is permission_loader
        assert config.resource_checker is resource_checker
        assert config.audit_logger is audit_logger

    def test_init_jwt_auth_none(self):
        """Test initialization with None jwt_auth"""
        with pytest.raises(ValueError):
            SecurityConfig(jwt_auth=None)

    def test_init_jwt_auth_invalid_type(self):
        """Test initialization with invalid jwt_auth type"""
        with pytest.raises(TypeError):
            SecurityConfig(jwt_auth="invalid")

    def test_validate(self):
        """Test validation"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        config = SecurityConfig(jwt_auth=jwt_auth)

        # Should not raise
        config.validate()

    def test_validate_invalid(self):
        """Test validation with invalid config"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        config = SecurityConfig(jwt_auth=jwt_auth)
        config.jwt_auth = None

        with pytest.raises(ValueError):
            config.validate()

    def test_from_env(self):
        """Test creating config from environment"""
        import os
        os.environ["JWT_SECRET_KEY"] = "test-secret-key"
        
        try:
            config = SecurityConfig.from_env()
            assert config.jwt_auth is not None
            assert config.audit_logger is not None
        finally:
            os.environ.pop("JWT_SECRET_KEY", None)

    def test_get_jwt_auth(self):
        """Test getting jwt_auth"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        config = SecurityConfig(jwt_auth=jwt_auth)

        assert config.get_jwt_auth() is jwt_auth

    def test_get_permission_loader(self):
        """Test getting permission_loader"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        permission_loader = StaticPermissionLoader({"user1": ["read"]})
        config = SecurityConfig(jwt_auth=jwt_auth, permission_loader=permission_loader)

        assert config.get_permission_loader() is permission_loader

    def test_get_permission_loader_none(self):
        """Test getting permission_loader when None"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        config = SecurityConfig(jwt_auth=jwt_auth)

        assert config.get_permission_loader() is None

    def test_get_resource_checker(self):
        """Test getting resource_checker"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        resource_checker = StaticResourceChecker({})
        config = SecurityConfig(jwt_auth=jwt_auth, resource_checker=resource_checker)

        assert config.get_resource_checker() is resource_checker

    def test_get_resource_checker_none(self):
        """Test getting resource_checker when None"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        config = SecurityConfig(jwt_auth=jwt_auth)

        assert config.get_resource_checker() is None

    def test_get_audit_logger(self):
        """Test getting audit_logger"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        audit_logger = AuditLogger()
        config = SecurityConfig(jwt_auth=jwt_auth, audit_logger=audit_logger)

        assert config.get_audit_logger() is audit_logger

    def test_get_audit_logger_default(self):
        """Test getting audit_logger default"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        config = SecurityConfig(jwt_auth=jwt_auth)

        assert config.get_audit_logger() is not None
        assert isinstance(config.get_audit_logger(), AuditLogger)

    def test_repr(self):
        """Test string representation"""
        jwt_auth = JWTAuth(secret_key="test-secret-key")
        config = SecurityConfig(jwt_auth=jwt_auth)

        repr_str = repr(config)
        assert "SecurityConfig" in repr_str
        assert "JWTAuth" in repr_str
