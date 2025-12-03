"""Unit tests for JWT authentication"""

import os
from datetime import datetime, timedelta, timezone

import pytest

from fastapi_easy.security import (
    InvalidTokenError,
    JWTAuth,
    TokenExpiredError,
)


class TestJWTAuth:
    """Test JWT authentication"""

    @pytest.fixture
    def jwt_auth(self):
        """Create JWT auth instance"""
        return JWTAuth(
            secret_key="test-secret-key",
            algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )

    def test_init_with_secret_key(self):
        """Test initialization with secret key"""
        jwt_auth = JWTAuth(secret_key="test-key")
        assert jwt_auth.secret_key == "test-key"
        assert jwt_auth.algorithm == "HS256"
        assert jwt_auth.access_token_expire_minutes == 15
        assert jwt_auth.refresh_token_expire_days == 7

    def test_init_without_secret_key(self):
        """Test initialization without secret key raises error"""
        # Clear environment variable
        os.environ.pop("JWT_SECRET_KEY", None)

        with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
            JWTAuth()

    def test_init_with_env_variable(self):
        """Test initialization with environment variable"""
        os.environ["JWT_SECRET_KEY"] = "env-secret-key"
        jwt_auth = JWTAuth()
        assert jwt_auth.secret_key == "env-secret-key"
        os.environ.pop("JWT_SECRET_KEY", None)

    def test_create_access_token(self, jwt_auth):
        """Test creating access token"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["admin", "user"],
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token
        payload = jwt_auth.verify_token(token)
        assert payload.sub == "user123"
        assert payload.roles == ["admin", "user"]
        assert payload.type == "access"

    def test_create_refresh_token(self, jwt_auth):
        """Test creating refresh token"""
        token = jwt_auth.create_refresh_token(subject="user123")

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token
        payload = jwt_auth.verify_token(token)
        assert payload.sub == "user123"
        assert payload.type == "refresh"

    def test_verify_valid_token(self, jwt_auth):
        """Test verifying valid token"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["admin"],
            permissions=["read", "write"],
        )

        payload = jwt_auth.verify_token(token)
        assert payload.sub == "user123"
        assert payload.roles == ["admin"]
        assert payload.permissions == ["read", "write"]
        assert payload.type == "access"

    def test_verify_invalid_token(self, jwt_auth):
        """Test verifying invalid token"""
        with pytest.raises(InvalidTokenError):
            jwt_auth.verify_token("invalid.token.here")

    def test_verify_expired_token(self, jwt_auth):
        """Test verifying expired token"""
        # Create token that expires immediately
        token = jwt_auth.create_access_token(
            subject="user123",
            expires_delta=timedelta(seconds=-1),
        )

        with pytest.raises(TokenExpiredError):
            jwt_auth.verify_token(token)

    def test_decode_token_without_verification(self, jwt_auth):
        """Test decoding token without verification"""
        token = jwt_auth.create_access_token(subject="user123")

        payload = jwt_auth.decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["type"] == "access"

    def test_refresh_access_token(self, jwt_auth):
        """Test refreshing access token"""
        refresh_token = jwt_auth.create_refresh_token(subject="user123")

        new_access_token = jwt_auth.refresh_access_token(
            refresh_token=refresh_token,
            roles=["admin"],
        )

        assert isinstance(new_access_token, str)

        # Verify new token
        payload = jwt_auth.verify_token(new_access_token)
        assert payload.sub == "user123"
        assert payload.roles == ["admin"]
        assert payload.type == "access"

    def test_refresh_with_invalid_token_type(self, jwt_auth):
        """Test refreshing with access token (should fail)"""
        access_token = jwt_auth.create_access_token(subject="user123")

        with pytest.raises(InvalidTokenError, match="not a refresh token"):
            jwt_auth.refresh_access_token(refresh_token=access_token)

    def test_get_token_expiration(self, jwt_auth):
        """Test getting token expiration time"""
        token = jwt_auth.create_access_token(subject="user123")

        expiration = jwt_auth.get_token_expiration(token)
        assert expiration is not None
        assert isinstance(expiration, datetime)
        assert expiration > datetime.now(timezone.utc)

    def test_is_token_expired(self, jwt_auth):
        """Test checking if token is expired"""
        # Valid token
        valid_token = jwt_auth.create_access_token(subject="user123")
        assert not jwt_auth.is_token_expired(valid_token)

        # Expired token
        expired_token = jwt_auth.create_access_token(
            subject="user123",
            expires_delta=timedelta(seconds=-1),
        )
        assert jwt_auth.is_token_expired(expired_token)

    def test_custom_expiration_times(self):
        """Test custom expiration times"""
        jwt_auth = JWTAuth(
            secret_key="test-key",
            access_token_expire_minutes=30,
            refresh_token_expire_days=14,
        )

        assert jwt_auth.access_token_expire_minutes == 30
        assert jwt_auth.refresh_token_expire_days == 14

    def test_token_with_empty_roles_and_permissions(self, jwt_auth):
        """Test token with empty roles and permissions"""
        token = jwt_auth.create_access_token(subject="user123")

        payload = jwt_auth.verify_token(token)
        assert payload.roles == []
        assert payload.permissions == []

    def test_token_payload_structure(self, jwt_auth):
        """Test token payload structure"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["admin"],
            permissions=["read"],
        )

        payload = jwt_auth.verify_token(token)
        assert hasattr(payload, "sub")
        assert hasattr(payload, "roles")
        assert hasattr(payload, "permissions")
        assert hasattr(payload, "exp")
        assert hasattr(payload, "iat")
        assert hasattr(payload, "type")

    def test_different_algorithms(self):
        """Test different JWT algorithms"""
        # HS256 (default)
        jwt_auth_hs256 = JWTAuth(
            secret_key="test-key",
            algorithm="HS256",
        )
        token_hs256 = jwt_auth_hs256.create_access_token(subject="user123")
        assert jwt_auth_hs256.verify_token(token_hs256).sub == "user123"

    def test_token_cannot_be_verified_with_different_key(self, jwt_auth):
        """Test token cannot be verified with different key"""
        token = jwt_auth.create_access_token(subject="user123")

        # Create new JWT auth with different key
        jwt_auth_different = JWTAuth(secret_key="different-key")

        with pytest.raises(InvalidTokenError):
            jwt_auth_different.verify_token(token)

    def test_multiple_tokens_are_different(self, jwt_auth):
        """Test that multiple tokens can be created"""
        import time

        token1 = jwt_auth.create_access_token(subject="user123")
        time.sleep(1.1)  # Delay to ensure different iat (at least 1 second)
        token2 = jwt_auth.create_access_token(subject="user123")

        # Tokens should be different (different iat)
        assert token1 != token2

        # But both should be valid
        assert jwt_auth.verify_token(token1).sub == "user123"
        assert jwt_auth.verify_token(token2).sub == "user123"
