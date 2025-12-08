"""Unit tests for rate limiting"""

import pytest

from fastapi_easy.security import LoginAttemptTracker


class TestLoginAttemptTracker:
    """Test login attempt tracker"""

    @pytest.fixture
    def tracker(self):
        """Create tracker instance"""
        return LoginAttemptTracker(
            max_attempts=3,
            lockout_duration_minutes=1,
            reset_duration_minutes=5,
        )

    def test_record_successful_attempt(self, tracker):
        """Test recording successful attempt"""
        tracker.record_attempt("user1", success=True)

        assert tracker.get_attempt_count("user1") == 0
        assert not tracker.is_locked_out("user1")

    def test_record_failed_attempt(self, tracker):
        """Test recording failed attempt"""
        tracker.record_attempt("user1", success=False)

        assert tracker.get_attempt_count("user1") == 1
        assert not tracker.is_locked_out("user1")

    def test_multiple_failed_attempts(self, tracker):
        """Test multiple failed attempts"""
        for _ in range(2):
            tracker.record_attempt("user1", success=False)

        assert tracker.get_attempt_count("user1") == 2
        assert not tracker.is_locked_out("user1")

    def test_lockout_after_max_attempts(self, tracker):
        """Test lockout after max attempts"""
        for _ in range(3):
            tracker.record_attempt("user1", success=False)

        assert tracker.is_locked_out("user1")

    def test_successful_attempt_clears_lockout(self, tracker):
        """Test successful attempt clears lockout"""
        # Lock out user
        for _ in range(3):
            tracker.record_attempt("user1", success=False)

        assert tracker.is_locked_out("user1")

        # Successful attempt should clear lockout
        tracker.record_attempt("user1", success=True)

        assert not tracker.is_locked_out("user1")
        assert tracker.get_attempt_count("user1") == 0

    def test_get_lockout_remaining_seconds(self, tracker):
        """Test getting lockout remaining time"""
        # Lock out user
        for _ in range(3):
            tracker.record_attempt("user1", success=False)

        remaining = tracker.get_lockout_remaining_seconds("user1")
        assert remaining is not None
        assert 0 <= remaining <= 60

    def test_lockout_not_locked_out(self, tracker):
        """Test getting remaining time when not locked out"""
        tracker.record_attempt("user1", success=False)

        remaining = tracker.get_lockout_remaining_seconds("user1")
        assert remaining is None

    def test_reset_user(self, tracker):
        """Test resetting user"""
        # Lock out user
        for _ in range(3):
            tracker.record_attempt("user1", success=False)

        assert tracker.is_locked_out("user1")

        # Reset user
        tracker.reset_user("user1")

        assert not tracker.is_locked_out("user1")
        assert tracker.get_attempt_count("user1") == 0

    def test_reset_all(self, tracker):
        """Test resetting all"""
        # Lock out multiple users
        for i in range(3):
            for _ in range(3):
                tracker.record_attempt(f"user{i}", success=False)

        # All should be locked out
        for i in range(3):
            assert tracker.is_locked_out(f"user{i}")

        # Reset all
        tracker.reset_all()

        # None should be locked out
        for i in range(3):
            assert not tracker.is_locked_out(f"user{i}")

    def test_different_users_independent(self, tracker):
        """Test different users have independent attempt counts"""
        tracker.record_attempt("user1", success=False)
        tracker.record_attempt("user1", success=False)
        tracker.record_attempt("user2", success=False)

        assert tracker.get_attempt_count("user1") == 2
        assert tracker.get_attempt_count("user2") == 1

    def test_custom_max_attempts(self):
        """Test custom max attempts"""
        tracker = LoginAttemptTracker(max_attempts=5)

        for _ in range(4):
            tracker.record_attempt("user1", success=False)

        assert not tracker.is_locked_out("user1")

        tracker.record_attempt("user1", success=False)
        assert tracker.is_locked_out("user1")

    def test_successful_attempt_after_failed(self, tracker):
        """Test successful attempt after failed attempts"""
        tracker.record_attempt("user1", success=False)
        tracker.record_attempt("user1", success=False)

        assert tracker.get_attempt_count("user1") == 2

        # Successful attempt clears all
        tracker.record_attempt("user1", success=True)

        assert tracker.get_attempt_count("user1") == 0

    def test_multiple_lockouts(self, tracker):
        """Test multiple lockouts for same user"""
        # First lockout
        for _ in range(3):
            tracker.record_attempt("user1", success=False)

        assert tracker.is_locked_out("user1")

        # Reset
        tracker.reset_user("user1")

        # Second lockout
        for _ in range(3):
            tracker.record_attempt("user1", success=False)

        assert tracker.is_locked_out("user1")
