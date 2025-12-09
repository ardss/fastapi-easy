"""Enhanced JWT authentication with key rotation, blacklisting, and advanced security features"""

from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import jwt

logger = logging.getLogger(__name__)

from .exceptions import InvalidTokenError, TokenExpiredError
from .models import TokenPayload


class TokenBlacklist:
    """JWT token blacklisting mechanism"""

    def __init__(self, redis_client=None, backend_storage=None):
        """Initialize token blacklist

        Args:
            redis_client: Redis client for distributed blacklisting
            backend_storage: Backend storage for persistent blacklisting
        """
        self.redis_client = redis_client
        self.backend_storage = backend_storage
        self.memory_blacklist = set()  # Fallback in-memory storage

    async def blacklist_token(self, token: str, expires_at: datetime) -> bool:
        """Add token to blacklist until expiration

        Args:
            token: JWT token to blacklist
            expires_at: Token expiration time

        Returns:
            True if successfully blacklisted
        """
        try:
            # Calculate TTL
            ttl = int((expires_at - datetime.now(timezone.utc)).total_seconds())
            if ttl <= 0:
                return True  # Token already expired

            # Use Redis if available
            if self.redis_client:
                key = f"blacklist:{token}"
                await self.redis_client.setex(key, ttl, "1")
                return True

            # Use backend storage if available
            elif self.backend_storage:
                await self.backend_storage.store_blacklisted_token(token, expires_at)
                return True

            # Fallback to memory (not recommended for production)
            else:
                self.memory_blacklist.add(token)
                # Note: Memory blacklist doesn't expire automatically
                return True

        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False

    async def is_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted

        Args:
            token: JWT token to check

        Returns:
            True if token is blacklisted
        """
        try:
            # Check Redis
            if self.redis_client:
                key = f"blacklist:{token}"
                return bool(await self.redis_client.exists(key))

            # Check backend storage
            elif self.backend_storage:
                return await self.backend_storage.is_token_blacklisted(token)

            # Check memory
            else:
                return token in self.memory_blacklist

        except Exception as e:
            logger.error(f"Failed to check blacklist status: {e}")
            return False

    async def invalidate_user_tokens(self, user_id: str) -> int:
        """Invalidate all tokens for a user

        Args:
            user_id: User ID whose tokens to invalidate

        Returns:
            Number of tokens invalidated
        """
        try:
            if self.redis_client:
                # Scan for user tokens in Redis
                pattern = f"user_token:{user_id}:*"
                cursor = 0
                invalidated = 0

                while True:
                    cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)
                    if keys:
                        # Add to blacklist
                        for key in keys:
                            token = key.split(":")[-1]
                            # Get expiration from token
                            await self.redis_client.setex(f"blacklist:{token}", 3600, "1")
                            invalidated += 1

                    if cursor == 0:
                        break

                return invalidated

            elif self.backend_storage:
                return await self.backend_storage.invalidate_user_tokens(user_id)

            else:
                # Cannot invalidate user tokens without storage
                logger.warning("Cannot invalidate user tokens without storage backend")
                return 0

        except Exception as e:
            logger.error(f"Failed to invalidate user tokens: {e}")
            return 0

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired blacklisted tokens

        Returns:
            Number of tokens cleaned up
        """
        try:
            if self.backend_storage:
                return await self.backend_storage.cleanup_expired_blacklisted_tokens()

            # Redis handles expiration automatically
            # Memory cleanup would require additional logic
            return 0

        except Exception as e:
            logger.error(f"Failed to cleanup expired tokens: {e}")
            return 0


class JWTKeyManager:
    """Manage JWT key rotation and multiple keys"""

    def __init__(self, primary_key: str, rotation_interval_days: int = 30):
        """Initialize key manager

        Args:
            primary_key: Primary signing key
            rotation_interval_days: Key rotation interval in days
        """
        self.rotation_interval_days = rotation_interval_days
        self.keys: Dict[str, Dict[str, datetime]] = {}
        self.current_key_id = "1"

        # Add primary key
        self.add_key("1", primary_key)

    def add_key(self, key_id: str, key: str, created_at: Optional[datetime] = None) -> None:
        """Add a new key

        Args:
            key_id: Unique key identifier
            key: JWT signing key
            created_at: Key creation timestamp
        """
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        self.keys[key_id] = {
            "key": key,
            "created_at": created_at,
            "is_active": True,
        }

    def get_current_key(self) -> str:
        """Get current active signing key"""
        if self.current_key_id not in self.keys:
            raise ValueError("Current key not found")
        return self.keys[self.current_key_id]["key"]

    def get_key(self, key_id: str) -> Optional[str]:
        """Get key by ID"""
        key_data = self.keys.get(key_id)
        return key_data["key"] if key_data else None

    def rotate_key(self) -> str:
        """Rotate to a new key

        Returns:
            New key ID
        """
        # Generate new key
        new_key_id = str(int(self.current_key_id) + 1)
        new_key = self._generate_key()

        # Add new key
        self.add_key(new_key_id, new_key)

        # Update current key
        self.current_key_id = new_key_id

        logger.info(f"JWT key rotated to {new_key_id}")
        return new_key_id

    def _generate_key(self) -> str:
        """Generate a new secure key"""
        return secrets.token_urlsafe(64)

    def cleanup_old_keys(self, keep_last_n: int = 3) -> None:
        """Clean up old keys, keeping only the last N keys

        Args:
            keep_last_n: Number of recent keys to keep
        """
        if len(self.keys) <= keep_last_n:
            return

        # Sort keys by creation time
        sorted_keys = sorted(
            self.keys.items(),
            key=lambda x: x[1]["created_at"],
        )

        # Remove oldest keys
        keys_to_remove = sorted_keys[:-keep_last_n]
        for key_id, _ in keys_to_remove:
            if key_id != self.current_key_id:  # Don't remove current key
                del self.keys[key_id]
                logger.info(f"Removed old JWT key: {key_id}")

    def needs_rotation(self) -> bool:
        """Check if key needs rotation"""
        current_key_data = self.keys.get(self.current_key_id)
        if not current_key_data:
            return True

        days_since_creation = (datetime.now(timezone.utc) - current_key_data["created_at"]).days

        return days_since_creation >= self.rotation_interval_days


class EnhancedJWTAuth:
    """Enhanced JWT authentication with key rotation and blacklisting"""

    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 15,
        refresh_token_expire_days: int = 7,
        key_rotation_days: int = 30,
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        token_blacklist: Optional[TokenBlacklist] = None,
        require_jti: bool = True,
    ):
        """Initialize enhanced JWT auth

        Args:
            secret_key: Primary secret key
            algorithm: JWT algorithm
            access_token_expire_minutes: Access token expiration
            refresh_token_expire_days: Refresh token expiration
            key_rotation_days: Key rotation interval
            issuer: Token issuer
            audience: Token audience
            token_blacklist: Token blacklist instance
            require_jti: Require JWT ID claim
        """
        # Initialize key management
        primary_key = secret_key or os.getenv("JWT_SECRET_KEY")
        if not primary_key:
            raise ValueError(
                "JWT_SECRET_KEY environment variable or secret_key parameter is required"
            )

        self.key_manager = JWTKeyManager(primary_key, key_rotation_days)
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.issuer = issuer
        self.audience = audience
        self.require_jti = require_jti
        self.token_blacklist = token_blacklist or TokenBlacklist()

    def create_access_token(
        self,
        subject: str,
        roles: Optional[List[str]] = None,
        permissions: Optional[List[str]] = None,
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, str]:
        """Create access token with enhanced security

        Args:
            subject: Token subject
            roles: User roles
            permissions: User permissions
            expires_delta: Custom expiration
            additional_claims: Additional claims

        Returns:
            Tuple of (token, jti)
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        jti = secrets.token_urlsafe(32)

        payload = {
            "sub": subject,
            "roles": roles or [],
            "permissions": permissions or [],
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "access",
            "jti": jti,
            "kid": self.key_manager.current_key_id,  # Key ID for rotation
        }

        # Add additional claims
        if additional_claims:
            payload.update(additional_claims)

        # Add optional claims
        if self.issuer:
            payload["iss"] = self.issuer
        if self.audience:
            payload["aud"] = self.audience

        # Sign with current key
        token = jwt.encode(
            payload,
            self.key_manager.get_current_key(),
            algorithm=self.algorithm,
        )

        # Store token in user token list (for invalidation)
        if self.token_blacklist.redis_client:
            # This needs to be awaited in async context - for now store synchronously
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If in async context, we need to handle this differently
                    asyncio.create_task(
                        self.token_blacklist.redis_client.setex(
                            f"user_token:{subject}:{jti}", int(expires_delta.total_seconds()), "1"
                        )
                    )
                else:
                    # If not in async context, run in loop
                    loop.run_until_complete(
                        self.token_blacklist.redis_client.setex(
                            f"user_token:{subject}:{jti}", int(expires_delta.total_seconds()), "1"
                        )
                    )
            except RuntimeError:
                # No event loop, skip Redis storage for now
                pass

        return token, jti

    def create_refresh_token(
        self,
        subject: str,
        expires_delta: Optional[timedelta] = None,
    ) -> Tuple[str, str]:
        """Create refresh token

        Args:
            subject: Token subject
            expires_delta: Custom expiration

        Returns:
            Tuple of (token, jti)
        """
        if expires_delta is None:
            expires_delta = timedelta(days=self.refresh_token_expire_days)

        now = datetime.now(timezone.utc)
        expire = now + expires_delta
        jti = secrets.token_urlsafe(32)

        payload = {
            "sub": subject,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "refresh",
            "jti": jti,
            "kid": self.key_manager.current_key_id,
        }

        if self.issuer:
            payload["iss"] = self.issuer
        if self.audience:
            payload["aud"] = self.audience

        token = jwt.encode(
            payload,
            self.key_manager.get_current_key(),
            algorithm=self.algorithm,
        )

        return token, jti

    async def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode token with blacklist checking

        Args:
            token: JWT token

        Returns:
            Token payload

        Raises:
            InvalidTokenError: If token is invalid or blacklisted
            TokenExpiredError: If token is expired
        """
        # Check blacklist first
        if await self.token_blacklist.is_blacklisted(token):
            logger.warning("Blacklisted token attempted")
            raise InvalidTokenError("Token has been revoked")

        try:
            # Decode without verification to get key ID
            unverified_header = jwt.get_unverified_header(token)
            key_id = unverified_header.get("kid")

            # Try current key first, then other keys
            verification_keys = []
            if key_id:
                verification_key = self.key_manager.get_key(key_id)
                if verification_key:
                    verification_keys.append(verification_key)

            # Always try current key as fallback
            verification_keys.append(self.key_manager.get_current_key())

            # Try each key
            payload = None
            last_error = None

            for key in verification_keys:
                try:
                    payload = jwt.decode(
                        token,
                        key,
                        algorithms=[self.algorithm],
                        issuer=self.issuer,
                        audience=self.audience,
                    )
                    break
                except jwt.InvalidSignatureError as e:
                    last_error = e
                    continue
                except jwt.ExpiredSignatureError:
                    raise TokenExpiredError("Token has expired")
                except jwt.InvalidTokenError as e:
                    raise InvalidTokenError(f"Invalid token: {e!s}")

            if payload is None:
                raise InvalidTokenError(f"Invalid token signature: {last_error}")

            # Validate token structure
            if "sub" not in payload:
                raise InvalidTokenError("Token missing 'sub' claim")

            if "type" not in payload:
                raise InvalidTokenError("Token missing 'type' claim")

            if self.require_jti and "jti" not in payload:
                raise InvalidTokenError("Token missing 'jti' claim")

            logger.debug(f"Token verified for user: {payload.get('sub')}")
            return TokenPayload(**payload)

        except Exception as e:
            if isinstance(e, (InvalidTokenError, TokenExpiredError)):
                raise
            logger.error(f"Token verification failed: {e}")
            raise InvalidTokenError(f"Token verification failed: {e!s}")

    async def refresh_access_token(
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
        payload = await self.verify_token(refresh_token)

        # Verify it's a refresh token
        if payload.type != "refresh":
            raise InvalidTokenError("Token is not a refresh token")

        # Create new access token
        new_token, _ = self.create_access_token(
            subject=payload.sub,
            roles=roles,
            permissions=permissions,
        )

        return new_token

    async def revoke_token(self, token: str) -> bool:
        """Revoke a token by adding it to blacklist

        Args:
            token: Token to revoke

        Returns:
            True if successfully revoked
        """
        try:
            # Get expiration from token
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
            )
            exp = payload.get("exp")
            if exp:
                expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
                return await self.token_blacklist.blacklist_token(token, expires_at)
            return True
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    async def revoke_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a user

        Args:
            user_id: User ID

        Returns:
            Number of tokens revoked
        """
        return await self.token_blacklist.invalidate_user_tokens(user_id)

    def rotate_keys(self) -> str:
        """Rotate signing keys

        Returns:
            New key ID
        """
        new_key_id = self.key_manager.rotate_key()
        self.key_manager.cleanup_old_keys()
        return new_key_id

    async def cleanup_expired_tokens(self) -> int:
        """Clean up expired blacklisted tokens

        Returns:
            Number of tokens cleaned up
        """
        return await self.token_blacklist.cleanup_expired_tokens()

    def get_key_info(self) -> Dict[str, Any]:
        """Get key management information

        Returns:
            Key information dictionary
        """
        return {
            "current_key_id": self.key_manager.current_key_id,
            "total_keys": len(self.key_manager.keys),
            "needs_rotation": self.key_manager.needs_rotation(),
            "rotation_interval_days": self.key_manager.rotation_interval_days,
            "keys": [
                {
                    "id": key_id,
                    "created_at": data["created_at"].isoformat(),
                    "is_current": key_id == self.key_manager.current_key_id,
                }
                for key_id, data in self.key_manager.keys.items()
            ],
        }
