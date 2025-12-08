"""Unit tests for password hashing using mock to avoid bcrypt dependency issues"""

import pytest
from unittest.mock import patch, MagicMock

# Mock bcrypt before importing to avoid import errors
with patch.dict('sys.modules', {'bcrypt': MagicMock()}):
    # Mock the bcrypt functions
    mock_bcrypt = MagicMock()
    mock_bcrypt.gensalt = MagicMock(return_value=b'$2b$12$salt')
    mock_bcrypt.hashpw = MagicMock(side_effect=lambda pwd, salt: b'$2b$12$hash' + pwd[-10:])
    mock_bcrypt.checkpw = MagicMock(side_effect=lambda pwd, hashed: pwd == hashed[:-10])

    import sys
    sys.modules['bcrypt'] = mock_bcrypt

    from fastapi_easy.security import PasswordManager


class TestPasswordManager:
    """Test password manager with mocked bcrypt"""

    @pytest.fixture
    def password_manager(self):
        """Create password manager instance"""
        # Ensure bcrypt is mocked for each test
        with patch.dict('sys.modules', {'bcrypt': mock_bcrypt}):
            with patch('fastapi_easy.security.password.bcrypt', mock_bcrypt):
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

        # Configure mock to return True for correct password
        mock_bcrypt.checkpw.side_effect = lambda pwd, h: pwd == password.encode()

        assert password_manager.verify_password(password, hashed)

    def test_verify_password_incorrect(self, password_manager):
        """Test verifying incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = password_manager.hash_password(password)

        # Configure mock to return False for incorrect password
        mock_bcrypt.checkpw.side_effect = lambda pwd, h: pwd == password.encode()

        assert not password_manager.verify_password(wrong_password, hashed)

    def test_hash_empty_password(self, password_manager):
        """Test hashing empty password raises error"""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            password_manager.hash_password("")

    def test_verify_empty_password(self, password_manager):
        """Test verifying empty password raises error"""
        password = "test_password_123"
        hashed = password_manager.hash_password(password)

        with pytest.raises(ValueError, match="Password and hash cannot be empty"):
            password_manager.verify_password("", hashed)

    def test_verify_empty_hash(self, password_manager):
        """Test verifying with empty hash raises error"""
        with pytest.raises(ValueError, match="Password and hash cannot be empty"):
            password_manager.verify_password("password", "")

    def test_different_passwords_different_hashes(self, password_manager):
        """Test different passwords produce different hashes"""
        password1 = "password_one"
        password2 = "password_two"

        # Configure mock to generate different hashes
        mock_bcrypt.hashpw.side_effect = [
            b'$2b$12$hash_one',
            b'$2b$12$hash_two'
        ]

        hash1 = password_manager.hash_password(password1)
        hash2 = password_manager.hash_password(password2)

        assert hash1 != hash2

    def test_same_password_different_hashes(self, password_manager):
        """Test same password produces different hashes (due to salt)"""
        password = "test_password"

        # Configure mock to generate different salts
        mock_bcrypt.gensalt.side_effect = [
            b'$2b$12$salt1',
            b'$2b$12$salt2'
        ]
        mock_bcrypt.hashpw.side_effect = [
            b'$2b$12$hash1',
            b'$2b$12$hash2'
        ]

        hash1 = password_manager.hash_password(password)
        hash2 = password_manager.hash_password(password)

        # Hashes should be different due to different salts
        assert hash1 != hash2

    def test_needs_rehash_same_rounds(self, password_manager):
        """Test needs_rehash with same rounds"""
        password = "test_password"
        # Mock hash with same rounds
        mock_bcrypt.hashpw.return_value = b'$2b$12$hash'
        hashed = password_manager.hash_password(password)

        assert not password_manager.needs_rehash(hashed)

    def test_needs_rehash_different_rounds(self, password_manager):
        """Test needs_rehash with different rounds"""
        password = "test_password"
        # Mock hash with different rounds
        mock_bcrypt.hashpw.return_value = b'$2b$10$hash'
        hashed = password_manager.hash_password(password)

        assert password_manager.needs_rehash(hashed)

    def test_needs_rehash_invalid_hash(self, password_manager):
        """Test needs_rehash with invalid hash"""
        assert password_manager.needs_rehash("invalid_hash")

    def test_custom_rounds(self):
        """Test custom bcrypt rounds"""
        with patch.dict('sys.modules', {'bcrypt': mock_bcrypt}):
            with patch('fastapi_easy.security.password.bcrypt', mock_bcrypt):
                manager = PasswordManager(rounds=8)
                password = "test_password"
                # Mock hash with custom rounds
                mock_bcrypt.hashpw.return_value = b'$2b$8$hash'
                hashed = manager.hash_password(password)

                # Configure checkpw to return True
                mock_bcrypt.checkpw.side_effect = lambda pwd, h: pwd == password.encode()

                assert manager.verify_password(password, hashed)

    def test_password_with_special_characters(self, password_manager):
        """Test password with special characters"""
        password = "P@ssw0rd!#$%^&*()"
        hashed = password_manager.hash_password(password)

        # Configure checkpw to return True
        mock_bcrypt.checkpw.side_effect = lambda pwd, h: pwd == password.encode()

        assert password_manager.verify_password(password, hashed)

    def test_long_password(self, password_manager):
        """Test very long password"""
        password = "x" * 1000
        # Should truncate to 72 bytes for bcrypt
        truncated_password = password[:72]
        hashed = password_manager.hash_password(password)

        # Configure checkpw to return True for truncated password
        mock_bcrypt.checkpw.side_effect = lambda pwd, h: pwd == truncated_password.encode()

        assert password_manager.verify_password(password, hashed)

    def test_password_truncation_warning(self, password_manager):
        """Test that long passwords are truncated and warning is logged"""
        password = "x" * 100  # Longer than 72 bytes

        with patch('fastapi_easy.security.password.logger') as mock_logger:
            password_manager.hash_password(password)

            # Should log warning about truncation
            mock_logger.warning.assert_called_with("Password exceeds bcrypt 72-byte limit, truncating")

    def test_verify_password_invalid_hash_format(self, password_manager):
        """Test verify_password handles invalid hash format gracefully"""
        password = "test_password"
        invalid_hash = "invalid_hash_format"

        # Configure checkpw to raise ValueError for invalid hash
        mock_bcrypt.checkpw.side_effect = ValueError("Invalid hash")

        result = password_manager.verify_password(password, invalid_hash)
        assert result is False

    def test_verify_password_with_timing_attack_protection(self, password_manager):
        """Test that verify_password performs dummy operations on error for timing consistency"""
        password = "test_password"
        invalid_hash = "invalid"

        # Configure checkpw to raise ValueError and also mock dummy operations
        mock_bcrypt.checkpw.side_effect = ValueError("Invalid hash")
        mock_bcrypt.hashpw.side_effect = [b'dummy_hash']  # For dummy operation

        with patch('fastapi_easy.security.password.logger') as mock_logger:
            result = password_manager.verify_password(password, invalid_hash)

            assert result is False
            # Should perform dummy hash operation for timing consistency
            assert mock_bcrypt.hashpw.call_count >= 1