"""Password hashing and verification for FastAPI-Easy"""

import logging

logger = logging.getLogger(__name__)

try:
    import bcrypt
except ImportError:
    raise ImportError(
        "bcrypt is required for password hashing. Install it with: pip install bcrypt"
    )


class PasswordManager:
    """Password hashing and verification manager"""

    def __init__(self, rounds: int = 12):
        """Initialize password manager

        Args:
            rounds: Number of bcrypt rounds (default: 12)
        """
        self.rounds = rounds

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password

        Raises:
            ValueError: If password is empty
        """
        if not password:
            logger.warning("Attempt to hash empty password")
            raise ValueError("Password cannot be empty")

        try:
            # Generate salt and hash password
            salt = bcrypt.gensalt(rounds=self.rounds)
            hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
            logger.debug("Password hashed successfully")
            return hashed.decode("utf-8")
        except (ValueError, TypeError) as e:
            logger.error(f"Password encoding error: {e}")
            raise
        except Exception as e:
            logger.error(f"Password hashing failed: {e}")
            raise

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash with constant time comparison

        Args:
            password: Plain text password
            hashed_password: Hashed password

        Returns:
            True if password matches hash

        Raises:
            ValueError: If password or hash is empty
        """
        if not password or not hashed_password:
            logger.warning("Attempt to verify with empty password or hash")
            raise ValueError("Password and hash cannot be empty")

        try:
            # bcrypt.checkpw uses constant time comparison
            result = bcrypt.checkpw(
                password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
            if result:
                logger.debug("Password verification successful")
            else:
                logger.debug("Password verification failed - incorrect password")
            return result
        except (ValueError, TypeError) as e:
            # Invalid hash format - still perform dummy operation for timing consistency
            logger.warning(f"Invalid hash format: {e}")
            try:
                dummy_hash = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=4))
                bcrypt.checkpw(b"dummy", dummy_hash)
            except Exception:
                pass
            return False
        except Exception as e:
            # Other errors - perform dummy operation
            logger.error(f"Password verification error: {e}")
            try:
                dummy_hash = bcrypt.hashpw(b"dummy", bcrypt.gensalt(rounds=4))
                bcrypt.checkpw(b"dummy", dummy_hash)
            except Exception:
                pass
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        """Check if password hash needs to be rehashed

        Args:
            hashed_password: Hashed password

        Returns:
            True if hash needs to be rehashed (e.g., rounds changed)
        """
        try:
            # Extract rounds from hash
            # bcrypt hash format: $2b$rounds$...
            parts = hashed_password.split("$")
            if len(parts) < 3:
                return True

            current_rounds = int(parts[2])
            return current_rounds != self.rounds
        except Exception:
            return True
