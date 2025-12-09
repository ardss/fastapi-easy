"""State persistence for FastAPI applications to handle hot reload scenarios"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Platform-specific imports
if os.name == "posix":
    import fcntl

    FCNTL_MODULE = fcntl
else:
    # Windows compatibility - fcntl not available
    fcntl = None
    FCNTL_MODULE = None

# Mock fcntl operations for Windows
import os
import msvcrt


logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages application state that persists across hot reloads.

    This class provides a way to store and retrieve state that survives
    FastAPI's hot reload mechanism by persisting to disk.

    Features:
    - Automatic state persistence to disk
    - Lock-based concurrent access protection
    - TTL support for cached state
    - Type-safe state retrieval
    - Custom serialization support
    """

    def __init__(
        self,
        state_dir: str = ".fastapi_state",
        default_ttl: int = 3600,  # 1 hour
        use_pickle: bool = False,  # Use JSON by default for better debugging
    ):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        self.default_ttl = default_ttl
        self.use_pickle = use_pickle
        self._lock_file = self.state_dir / ".state.lock"
        self._memory_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}

    def _get_lock(self) -> Optional[int]:
        """Get file lock for thread-safe operations"""
        try:
            if FCNTL_MODULE:  # Unix-like systems
                lock_fd = os.open(str(self._lock_file), os.O_CREAT | os.O_WRONLY)
                FCNTL_MODULE.flock(lock_fd, FCNTL_MODULE.LOCK_EX)
                return lock_fd
            else:
                # Windows fallback - use thread lock
                if not hasattr(self, "_thread_lock"):
                    self._thread_lock = threading.Lock()
                self._thread_lock.acquire()
                return None
        except Exception as e:
            logger.warning(f"Could not acquire lock: {e}")
            return None

    def _release_lock(self, lock_fd: Optional[int]) -> None:
        """Release file lock"""
        try:
            if lock_fd is not None and FCNTL_MODULE:
                FCNTL_MODULE.flock(lock_fd, FCNTL_MODULE.LOCK_UN)
                os.close(lock_fd)
            elif hasattr(self, "_thread_lock"):
                self._thread_lock.release()
        except Exception as e:
            logger.warning(f"Could not release lock: {e}")

    def _get_state_file(self, key: str) -> Path:
        """Get the file path for a state key"""
        # Hash the key to avoid filesystem issues
        safe_key = hashlib.md5(key.encode()).hexdigest()
        ext = "json"  # Always use secure JSON serialization
        return self.state_dir / f"{safe_key}.{ext}"

    def _serialize(self, data: Any) -> str:
        """Serialize data for storage using secure JSON"""

        # JSON serialization with comprehensive type handling
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, (set, frozenset)):
                return list(obj)
            elif hasattr(obj, "__dict__"):
                # For objects with attributes, try to serialize as dict
                return obj.__dict__
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(data, default=json_serializer)

    def _deserialize(self, data: str) -> Any:
        """Deserialize data from storage using secure JSON"""
        return json.loads(data)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a state value

        Args:
            key: State key
            value: Value to store
            ttl: Time to live in seconds (None for no expiration)

        Returns:
            True if successful, False otherwise
        """
        try:
            lock_fd = self._get_lock()
            state_file = self._get_state_file(key)

            # Prepare metadata
            metadata = {
                "value": value,
                "created_at": datetime.now().isoformat(),
                "expires_at": (
                    (datetime.now() + timedelta(seconds=ttl or self.default_ttl)).isoformat()
                    if ttl
                    else None
                ),
                "ttl": ttl or self.default_ttl,
            }

            # Write to file
            with open(state_file, "wb" if self.use_pickle else "w") as f:
                if self.use_pickle:
                    f.write(self._serialize(metadata))
                else:
                    f.write(self._serialize(metadata))

            # Update memory cache
            self._memory_cache[key] = value
            self._cache_timestamps[key] = datetime.now()

            logger.debug(f"State set: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to set state {key}: {e}")
            return False
        finally:
            self._release_lock(lock_fd)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a state value

        Args:
            key: State key
            default: Default value if key not found or expired

        Returns:
            Stored value or default
        """
        # Check memory cache first
        if key in self._memory_cache:
            if key in self._cache_timestamps:
                age = datetime.now() - self._cache_timestamps[key]
                if age.total_seconds() < self.default_ttl:
                    logger.debug(f"State hit (memory): {key}")
                    return self._memory_cache[key]

        # Check disk storage
        try:
            lock_fd = self._get_lock()
            state_file = self._get_state_file(key)

            if not state_file.exists():
                logger.debug(f"State miss (file not found): {key}")
                return default

            # Read from file
            with open(state_file, "rb" if self.use_pickle else "r") as f:
                data = f.read()

            metadata = self._deserialize(data)

            # Check expiration
            if metadata.get("expires_at"):
                expires_at = datetime.fromisoformat(metadata["expires_at"])
                if datetime.now() > expires_at:
                    logger.debug(f"State miss (expired): {key}")
                    self.delete(key)
                    return default

            value = metadata["value"]

            # Update memory cache
            self._memory_cache[key] = value
            self._cache_timestamps[key] = datetime.now()

            logger.debug(f"State hit (disk): {key}")
            return value

        except Exception as e:
            logger.error(f"Failed to get state {key}: {e}")
            return default
        finally:
            self._release_lock(lock_fd)

    def delete(self, key: str) -> bool:
        """Delete a state value"""
        try:
            lock_fd = self._get_lock()
            state_file = self._get_state_file(key)

            # Remove file
            if state_file.exists():
                state_file.unlink()

            # Remove from memory cache
            self._memory_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)

            logger.debug(f"State deleted: {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete state {key}: {e}")
            return False
        finally:
            self._release_lock(lock_fd)

    def clear_expired(self) -> int:
        """Clear all expired state entries"""
        cleared = 0
        try:
            lock_fd = self._get_lock()
            current_time = datetime.now()

            for state_file in self.state_dir.glob("*.json"):
                try:
                    with open(state_file) as f:
                        data = json.load(f)
                    expires_at = data.get("expires_at")
                    if expires_at:
                        expires_at = datetime.fromisoformat(expires_at)
                        if current_time > expires_at:
                            state_file.unlink()
                            cleared += 1
                except Exception:
                    continue

            logger.info(f"Cleared {cleared} expired state entries")
            return cleared

        except Exception as e:
            logger.error(f"Failed to clear expired state: {e}")
            return 0
        finally:
            self._release_lock(lock_fd)

    def get_all_keys(self) -> List[str]:
        """Get all non-expired state keys"""
        keys = []
        try:
            lock_fd = self._get_lock()
            current_time = datetime.now()

            for state_file in self.state_dir.glob("*.json"):
                try:
                    with open(state_file) as f:
                        data = json.load(f)
                    expires_at = data.get("expires_at")
                    if not expires_at or datetime.fromisoformat(expires_at) > current_time:
                        keys.append(state_file.stem)
                except Exception:
                    continue

            return keys

        except Exception as e:
            logger.error(f"Failed to get state keys: {e}")
            return []
        finally:
            self._release_lock(lock_fd)


# Global state manager instance
_global_state_manager: Optional[StateManager] = None


def get_state_manager(**kwargs: Any) -> StateManager:
    """Get or create the global state manager"""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = StateManager(**kwargs)
    return _global_state_manager


def persistent_state(key: str, ttl: Optional[int] = None, manager: Optional[StateManager] = None):
    """
    Decorator to persist function return values across hot reloads

    Usage:
        @persistent_state("user_tokens", ttl=3600)
        def get_valid_tokens():
            return [...]
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            state_mgr = manager or get_state_manager()

            # Try to get from state first
            cached_value = state_mgr.get(key)
            if cached_value is not None:
                logger.debug(f"Using cached value for {key}")
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            state_mgr.set(key, result, ttl=ttl)
            logger.debug(f"Cached result for {key}")
            return result

        return wrapper

    return decorator


class TokenStore:
    """
    Token store that persists across hot reloads

    Example usage for JWT tokens:
        token_store = TokenStore()

        # Store token
        token_store.add_token("user123", "jwt_token_here")

        # Validate token
        if token_store.is_valid("user123", "jwt_token_here"):
            # Token is valid
    """

    def __init__(self, state_manager: Optional[StateManager] = None):
        self.state_manager = state_manager or get_state_manager()
        self.token_key = "fastapi_tokens"

    def add_token(self, user_id: str, token: str, expires_in: int = 3600) -> None:
        """Add a token for a user"""
        tokens = self.state_manager.get(self.token_key, {})
        tokens[user_id] = {
            "token": token,
            "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
        }
        self.state_manager.set(self.token_key, tokens, ttl=expires_in)

    def is_valid(self, user_id: str, token: str) -> bool:
        """Check if a token is valid"""
        tokens = self.state_manager.get(self.token_key, {})
        user_tokens = tokens.get(user_id)

        if not user_tokens:
            return False

        # Check token match
        if user_tokens["token"] != token:
            return False

        # Check expiration
        expires_at = datetime.fromisoformat(user_tokens["expires_at"])
        if datetime.now() > expires_at:
            self.remove_token(user_id)
            return False

        return True

    def remove_token(self, user_id: str) -> None:
        """Remove a token"""
        tokens = self.state_manager.get(self.token_key, {})
        tokens.pop(user_id, None)
        self.state_manager.set(self.token_key, tokens)

    def clear_expired_tokens(self) -> None:
        """Clear all expired tokens"""
        tokens = self.state_manager.get(self.token_key, {})
        current_time = datetime.now()

        expired_users = []
        for user_id, token_data in tokens.items():
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if current_time > expires_at:
                expired_users.append(user_id)

        for user_id in expired_users:
            tokens.pop(user_id, None)

        if expired_users:
            self.state_manager.set(self.token_key, tokens)
            logger.info(f"Cleared {len(expired_users)} expired tokens")


# Example usage
if __name__ == "__main__":
    import time

    # Create state manager
    state = StateManager(state_dir="test_state")

    # Test basic functionality
    state.set("test_key", {"data": "test_value"}, ttl=5)
    logger.info(f"Retrieved: {state.get('test_key')}")

    # Test token store
    token_store = TokenStore(state)
    token_store.add_token("user1", "token123", expires_in=10)
    logger.info(f"Token valid: {token_store.is_valid('user1', 'token123')}")

    # Test persistence decorator
    @persistent_state("api_response", ttl=30)
    def expensive_api_call():
        logger.debug("Making expensive API call...")
        return {"data": "expensive_result"}

    logger.info(f"API call result: {expensive_api_call()}")
    logger.info(f"Cached API call result: {expensive_api_call()}")

    # Cleanup
    time.sleep(6)
    logger.info(f"After TTL - Retrieved: {state.get('test_key', 'expired')}")
