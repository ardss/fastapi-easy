"""Unit tests for password hashing"""

import pytest
from unittest.mock import patch, MagicMock

# Import password test configuration to mock bcrypt
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tests.conftest_password import bcrypt_mock

# Mock bcrypt before importing the module
with patch.dict("sys.modules", {"bcrypt": bcrypt_mock}):
    with patch("fastapi_easy.security.password.bcrypt", bcrypt_mock):
        from fastapi_easy.security import PasswordManager


@pytest.mark.unit
@pytest.mark.security
class TestPasswordManager:
    """Test password manager"""

    @pytest.fixture
    def password_manager(self):
        """Create password manager instance"""
        return PasswordManager(rounds=10)

    def test_hash_password(self, password_manager):
        """Test hashing password"""
        password = "test_password_123"
        hashed = password_manager.hash_password(password)

        assert hashed is not None
        assert len(hashed) > 0
        assert password not in hashed

    def test_verify_password_correct(self, password_manager):
        """Test verifying correct password"""
        password = "test_password_123"
        hashed = password_manager.hash_password(password)

        assert password_manager.verify_password(password, hashed)

    def test_verify_password_incorrect(self, password_manager):
        """Test verifying incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = password_manager.hash_password(password)

        assert not password_manager.verify_password(wrong_password, hashed)

    def test_hash_empty_password(self, password_manager):
        """Test hashing empty password raises error"""
        with pytest.raises(ValueError):
            password_manager.hash_password("")

    def test_verify_empty_password(self, password_manager):
        """Test verifying empty password raises error"""
        password = "test_password_123"
        hashed = password_manager.hash_password(password)

        with pytest.raises(ValueError):
            password_manager.verify_password("", hashed)

    def test_verify_empty_hash(self, password_manager):
        """Test verifying with empty hash raises error"""
        with pytest.raises(ValueError):
            password_manager.verify_password("password", "")

    def test_different_passwords_different_hashes(self, password_manager):
        """Test different passwords produce different hashes"""
        password1 = "password_one"
        password2 = "password_two"

        hash1 = password_manager.hash_password(password1)
        hash2 = password_manager.hash_password(password2)

        assert hash1 != hash2

    def test_same_password_different_hashes(self, password_manager):
        """Test same password produces different hashes (due to salt)"""
        password = "test_password"

        hash1 = password_manager.hash_password(password)
        hash2 = password_manager.hash_password(password)

        # Hashes should be different due to different salts
        assert hash1 != hash2
        # But both should verify correctly
        assert password_manager.verify_password(password, hash1)
        assert password_manager.verify_password(password, hash2)

    def test_needs_rehash_same_rounds(self, password_manager):
        """Test needs_rehash with same rounds"""
        password = "test_password"
        hashed = password_manager.hash_password(password)

        assert not password_manager.needs_rehash(hashed)

    def test_needs_rehash_different_rounds(self, password_manager):
        """Test needs_rehash with different rounds"""
        password = "test_password"
        hashed = password_manager.hash_password(password)

        # Create new manager with different rounds
        new_manager = PasswordManager(rounds=12)
        assert new_manager.needs_rehash(hashed)

    def test_needs_rehash_invalid_hash(self, password_manager):
        """Test needs_rehash with invalid hash"""
        assert password_manager.needs_rehash("invalid_hash")

    def test_custom_rounds(self):
        """Test custom bcrypt rounds"""
        manager = PasswordManager(rounds=8)
        password = "test_password"
        hashed = manager.hash_password(password)

        assert manager.verify_password(password, hashed)

    def test_password_with_special_characters(self, password_manager):
        """Test password with special characters"""
        password = "P@ssw0rd!#$%^&*()"
        hashed = password_manager.hash_password(password)

        assert password_manager.verify_password(password, hashed)

    def test_long_password(self, password_manager):
        """Test very long password"""
        password = "x" * 1000
        hashed = password_manager.hash_password(password)

        assert password_manager.verify_password(password, hashed)
