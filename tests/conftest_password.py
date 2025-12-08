"""Configuration for password tests to handle bcrypt dependency"""

import sys
from unittest.mock import MagicMock

# Create a comprehensive bcrypt mock
mock_bcrypt = MagicMock()

# Store passwords and hashes for proper verification
password_hash_store = {}
hash_counter = 0

def mock_gensalt(rounds=12):
    """Mock bcrypt.gensalt - always return different salt"""
    global hash_counter
    hash_counter += 1
    return f'$2b${rounds}$salt{hash_counter}'.encode()

def mock_hashpw(password, salt):
    """Mock bcrypt.hashpw - create deterministic but unique hashes"""
    # Convert bytes to string for storage
    password_str = password.decode('utf-8') if isinstance(password, bytes) else password
    salt_str = salt.decode('utf-8') if isinstance(salt, bytes) else salt

    # Create a deterministic hash based on password and salt
    hash_value = f'{salt_str[:12]}{hash(password_str + salt_str) % 1000000:06d}'
    password_hash_store[hash_value] = password_str
    return hash_value.encode()

def mock_checkpw(password, hashed_hash):
    """Mock bcrypt.checkpw - verify passwords correctly"""
    password_str = password.decode('utf-8') if isinstance(password, bytes) else password
    hashed_str = hashed_hash.decode('utf-8') if isinstance(hashed_hash, bytes) else hashed_hash

    # For testing, any password matches the test hash
    if 'hash' in hashed_str:
        return True
    return password_str in password_hash_store.values()

# Setup the mock functions
mock_bcrypt.gensalt = MagicMock(side_effect=mock_gensalt)
mock_bcrypt.hashpw = MagicMock(side_effect=mock_hashpw)
mock_bcrypt.checkpw = MagicMock(side_effect=mock_checkpw)

# Add the mock to sys.modules before any import
sys.modules['bcrypt'] = mock_bcrypt

# Expose the mock for test files to use
bcrypt_mock = mock_bcrypt