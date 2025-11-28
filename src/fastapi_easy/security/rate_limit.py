"""Rate limiting and brute force protection for FastAPI-Easy"""

import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


class LoginAttemptTracker:
    """Track login attempts and enforce rate limiting"""

    def __init__(
        self,
        max_attempts: int = 5,
        lockout_duration_minutes: int = 15,
        reset_duration_minutes: int = 60,
    ):
        """Initialize login attempt tracker

        Args:
            max_attempts: Maximum login attempts before lockout
            lockout_duration_minutes: Duration of lockout in minutes
            reset_duration_minutes: Duration after which attempts are reset
        """
        self.max_attempts = max_attempts
        self.lockout_duration = timedelta(minutes=lockout_duration_minutes)
        self.reset_duration = timedelta(minutes=reset_duration_minutes)

        # Thread safety
        self._lock = threading.RLock()

        # Track attempts per username
        self.attempts: Dict[str, list] = defaultdict(list)
        # Track lockout status
        self.lockouts: Dict[str, datetime] = {}

    def record_attempt(self, username: str, success: bool = False) -> None:
        """Record a login attempt

        Args:
            username: Username
            success: Whether the attempt was successful
        """
        # Validate input
        if not isinstance(username, str):
            raise TypeError("username must be a string")
        
        if len(username) > 255:
            raise ValueError("username too long (max 255 characters)")
        
        if not username.strip():
            raise ValueError("username cannot be empty")

        with self._lock:
            now = datetime.now(timezone.utc)

            # If successful, clear attempts
            if success:
                self.attempts[username] = []
                self.lockouts.pop(username, None)
                return

            # Record failed attempt
            self.attempts[username].append(now)

            # Clean up old attempts
            self._cleanup_old_attempts(username)

            # Check if should lock out
            if len(self.attempts[username]) >= self.max_attempts:
                self.lockouts[username] = now

    def is_locked_out(self, username: str) -> bool:
        """Check if user is locked out

        Args:
            username: Username

        Returns:
            True if user is locked out
        """
        with self._lock:
            if username not in self.lockouts:
                return False

            lockout_time = self.lockouts[username]
            now = datetime.now(timezone.utc)

            # Check if lockout has expired
            if now - lockout_time > self.lockout_duration:
                self.lockouts.pop(username, None)
                self.attempts[username] = []
                return False

            return True

    def get_lockout_remaining_seconds(self, username: str) -> Optional[int]:
        """Get remaining lockout time in seconds

        Args:
            username: Username

        Returns:
            Remaining seconds or None if not locked out
        """
        if not self.is_locked_out(username):
            return None

        lockout_time = self.lockouts[username]
        now = datetime.now(timezone.utc)
        remaining = self.lockout_duration - (now - lockout_time)

        return max(0, int(remaining.total_seconds()))

    def get_attempt_count(self, username: str) -> int:
        """Get current attempt count

        Args:
            username: Username

        Returns:
            Number of failed attempts
        """
        with self._lock:
            self._cleanup_old_attempts(username)
            return len(self.attempts[username])

    def _cleanup_old_attempts(self, username: str) -> None:
        """Clean up attempts older than reset duration

        Args:
            username: Username
        """
        now = datetime.now(timezone.utc)
        attempts = self.attempts[username]

        # Remove attempts older than reset duration
        self.attempts[username] = [
            attempt for attempt in attempts
            if now - attempt < self.reset_duration
        ]

    def reset_user(self, username: str) -> None:
        """Reset attempts for a user

        Args:
            username: Username
        """
        with self._lock:
            self.attempts.pop(username, None)
            self.lockouts.pop(username, None)

    def reset_all(self) -> None:
        """Reset all attempts and lockouts"""
        with self._lock:
            self.attempts.clear()
            self.lockouts.clear()
