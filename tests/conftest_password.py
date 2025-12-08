"""Configuration for password tests to handle bcrypt dependency"""

import sys
from unittest.mock import MagicMock

# Create a comprehensive bcrypt mock
mock_bcrypt = MagicMock()
mock_bcrypt.gensalt = MagicMock(return_value=b'$2b$12$salt')
mock_bcrypt.hashpw = MagicMock(side_effect=lambda pwd, salt: b'$2b$12$hash')
mock_bcrypt.checkpw = MagicMock(side_effect=lambda pwd, hashed: pwd == hashed)

# Add the mock to sys.modules before any import
sys.modules['bcrypt'] = mock_bcrypt

# Expose the mock for test files to use
bcrypt_mock = mock_bcrypt