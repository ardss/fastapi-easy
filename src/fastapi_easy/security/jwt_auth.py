"""JWT authentication for FastAPI-Easy"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    import jwt
except ImportError:
    raise ImportError("PyJWT is required for JWT authentication. Install it with: pip install PyJWT")

from .exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    InvalidCredentialsError,
)
from .models import TokenPayload


class JWTAuth:
    """JWT authentication handler"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
    ):
        """Initialize JWT auth

        Args:
            secret_key: Secret key for signing tokens (default: from env var JWT_SECRET_KEY)
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token expiration time in minutes
            refresh_token_expire_days: Refresh token expiration time in days
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET_KEY")
        if not self.secret_key:
            raise ValueError(
                "JWT_SECRET_KEY environment variable or secret_key parameter is required"
            )

        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        subject: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create access token

        Args:
            subject: Token subject (usually user_id or username)
            roles: User roles
            permissions: User permissions
            expires_delta: Custom expiration time

        Returns:
            JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        now = datetime.utcnow()
        expire = now + expires_delta

        payload = {
            "sub": subject,
            "roles": roles or [],
            "permissions": permissions or [],
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "access",
        }

        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

        return encoded_jwt

    def create_refresh_token(
        self,
        subject: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create refresh token

        Args:
            subject: Token subject (usually user_id or username)
            expires_delta: Custom expiration time

        Returns:
            JWT token
        """
        if expires_delta is None:
            expires_delta = timedelta(days=self.refresh_token_expire_days)

        now = datetime.utcnow()
        expire = now + expires_delta

        payload = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

        return encoded_jwt

    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode token

        Args:
            token: JWT token

        Returns:
            Token payload

        Raises:
            InvalidTokenError: If token is invalid
            TokenExpiredError: If token is expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )

            # Validate token structure
            if "sub" not in payload:
                raise InvalidTokenError("Token missing 'sub' claim")

            if "type" not in payload:
                raise InvalidTokenError("Token missing 'type' claim")

            return TokenPayload(**payload)

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")
        except Exception as e:
            raise InvalidTokenError(f"Token verification failed: {str(e)}")

    def decode_token(self, token: str) -> Dict:
        """Decode token without verification (for debugging only)

        Args:
            token: JWT token

        Returns:
            Token payload
        """
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
            )
            return payload
        except Exception as e:
            raise InvalidTokenError(f"Failed to decode token: {str(e)}")

    def refresh_access_token(
        self,
        refresh_token: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
    ) -> str:
        """Refresh access token using refresh token

        Args:
            refresh_token: Refresh token
            roles: Updated user roles
            permissions: Updated user permissions

        Returns:
            New access token

        Raises:
            InvalidTokenError: If refresh token is invalid
            TokenExpiredError: If refresh token is expired
        """
        payload = self.verify_token(refresh_token)

        # Verify it's a refresh token
        if payload.type != "refresh":
            raise InvalidTokenError("Token is not a refresh token")

        # Create new access token
        return self.create_access_token(
            subject=payload.sub,
            roles=roles,
            permissions=permissions,
        )

    def get_token_expiration(self, token: str) -> Optional[datetime]:
        """Get token expiration time

        Args:
            token: JWT token

        Returns:
            Expiration datetime or None if not found
        """
        try:
            payload = self.decode_token(token)
            if "exp" in payload:
                return datetime.utcfromtimestamp(payload["exp"])
        except Exception:
            pass

        return None

    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired

        Args:
            token: JWT token

        Returns:
            True if token is expired
        """
        try:
            self.verify_token(token)
            return False
        except TokenExpiredError:
            return True
        except Exception:
            return True
