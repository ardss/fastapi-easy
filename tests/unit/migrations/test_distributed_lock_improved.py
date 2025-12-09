"""
Improved distributed lock tests with better mocking and edge case coverage.
"""

import asyncio
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import pytest

from fastapi_easy.migrations.distributed_lock import FileLock, MemoryLock, get_lock_provider
from fastapi_easy.migrations.engine import MigrationEngine
from fastapi_easy.migrations.types import Migration, RiskLevel
from sqlalchemy import create_engine, MetaData


@pytest.fixture
def temp_lock_file():
    """Create a temporary lock file for testing"""
    fd, path = tempfile.mkstemp(suffix=".lock")
    os.close(fd)
    try:
        yield path
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.fixture
def isolated_memory_lock():
    """Create an isolated memory lock for testing"""
    return MemoryLock()


@pytest.fixture
def isolated_file_lock():
    """Create an isolated file lock for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".lock") as f:
        lock_path = f.name

    try:
        lock = FileLock(lock_path)
        yield lock
    finally:
        # Cleanup
        if os.path.exists(lock_path):
            os.remove(lock_path)


@pytest.fixture
async def async_migration_with_mock_lock():
    """Create migration engine with mocked lock"""
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()
    migration_engine = MigrationEngine(engine, metadata)

    # Mock all lock operations
    mock_lock = AsyncMock()
    mock_lock.acquire = AsyncMock(return_value=True)
    mock_lock.release = AsyncMock(return_value=True)
    mock_lock.force_release = Mock(return_value=True)

    migration_engine.lock = mock_lock
    yield migration_engine, mock_lock


@pytest.mark.unit
@pytest.mark.migration
class TestDistributedLockEdgeCases:
    """Test distributed lock edge cases and error conditions"""

    @pytest.mark.asyncio
    async def test_concurrent_lock_acquisition(self, isolated_file_lock):
        """Test concurrent lock acquisition"""
        results = []

        async def acquire_lock(worker_id):
            """Acquire lock from a worker"""
            try:
                acquired = await isolated_file_lock.acquire()
                if acquired:
                    await asyncio.sleep(0.1)  # Hold lock briefly
                    await isolated_file_lock.release()
                    results.append(f"worker_{worker_id}_success")
                else:
                    results.append(f"worker_{worker_id}_failed")
            except Exception as e:
                results.append(f"worker_{worker_id}_error: {e}")

        # Try to acquire from multiple workers concurrently
        tasks = [acquire_lock(i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Only one should succeed
        success_count = sum(1 for r in results if "success" in r)
        assert success_count == 1

    @pytest.mark.asyncio
    async def test_lock_timeout_handling(self, temp_lock_file):
        """Test lock timeout handling"""
        # Create a lock with very short timeout
        lock = FileLock(temp_lock_file, timeout=0.1)

        # Acquire lock from first worker
        acquired = await lock.acquire()
        assert acquired is True

        # Try to acquire from second worker - should timeout
        lock2 = FileLock(temp_lock_file, timeout=0.1)
        acquired2 = await lock2.acquire()
        assert acquired2 is False

        # Cleanup
        await lock.release()

    @pytest.mark.asyncio
    async def test_lock_release_failure_handling(self):
        """Test handling of lock release failures"""
        lock = MemoryLock()

        # Mock release to fail
        original_release = lock.release
        call_count = 0

        async def failing_release():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("Release failed")
            return await original_release()

        lock.release = failing_release

        # Should acquire lock successfully
        acquired = await lock.acquire()
        assert acquired is True

        # Should handle release failures gracefully
        # In MemoryLock, release just removes from the set, so it won't fail
        # but the mock above tests the retry logic
        await lock.release()

        # Verify the lock was eventually released
        acquired2 = await lock.acquire()
        assert acquired2 is True

    @pytest.mark.asyncio
    async def test_lock_with_corrupted_file(self, temp_lock_file):
        """Test lock handling with corrupted lock file"""
        # Write corrupted data to lock file
        with open(temp_lock_file, "w") as f:
            f.write("corrupted lock data")

        lock = FileLock(temp_lock_file)

        # Should handle corrupted file gracefully
        acquired = await lock.acquire()
        assert acquired is True

        await lock.release()

    @pytest.mark.asyncio
    async def test_lock_force_release(self, temp_lock_file):
        """Test force release functionality"""
        lock = FileLock(temp_lock_file)

        # Acquire lock
        acquired = await lock.acquire()
        assert acquired is True

        # Force release should work even without proper release
        force_released = lock.force_release()
        assert force_released is True

        # Should be able to acquire again
        lock2 = FileLock(temp_lock_file)
        acquired2 = await lock2.acquire()
        assert acquired2 is True

    def test_memory_lock_isolation(self):
        """Test that memory locks are properly isolated"""
        lock1 = MemoryLock()
        lock2 = MemoryLock()

        # They should be independent
        assert lock1 != lock2
        assert lock1.locks is not lock2.locks

    @pytest.mark.asyncio
    async def test_lock_with_no_filesystem_access(self):
        """Test memory lock when filesystem is unavailable"""
        lock = MemoryLock()

        # Should work without filesystem
        acquired = await lock.acquire()
        assert acquired is True

        await lock.release()

    @pytest.mark.asyncio
    async def test_lock_cleanup_on_process_exit(self, temp_lock_file):
        """Test lock cleanup behavior"""
        lock = FileLock(temp_lock_file)

        # Acquire lock
        acquired = await lock.acquire()
        assert acquired is True

        # Simulate process exit by deleting lock file
        if os.path.exists(temp_lock_file):
            os.remove(temp_lock_file)

        # Should be able to acquire from new instance
        lock2 = FileLock(temp_lock_file)
        acquired2 = await lock2.acquire()
        assert acquired2 is True

    @pytest.mark.asyncio
    async def test_lock_provider_selection(self):
        """Test lock provider selection logic"""
        # Test with SQLite engine
        sqlite_engine = create_engine("sqlite:///:memory:")
        lock = get_lock_provider(sqlite_engine)
        assert isinstance(lock, FileLock)

        # Test with in-memory SQLite
        memory_engine = create_engine("sqlite:///:memory:")
        memory_lock = get_lock_provider(memory_engine)
        # Should prefer FileLock but fallback to MemoryLock if issues

    @pytest.mark.asyncio
    async def test_migration_engine_with_lock_timeout(self):
        """Test migration engine behavior with lock timeout"""
        engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()

        # Create engine with custom lock timeout
        migration_engine = MigrationEngine(engine, metadata)

        # Mock lock to simulate timeout
        async def mock_acquire():
            return False  # Simulate timeout

        migration_engine.lock.acquire = mock_acquire

        # Should return skipped status
        result = await migration_engine.auto_migrate()
        assert result.status == "skipped"
        assert len(result.migrations) == 0

    @pytest.mark.asyncio
    async def test_lock_with_high_concurrency(self):
        """Test lock behavior under high concurrency"""
        lock = MemoryLock()
        results = []
        successful_acquisitions = 0

        async def worker(worker_id):
            nonlocal successful_acquisitions
            try:
                if await lock.acquire():
                    successful_acquisitions += 1
                    await asyncio.sleep(0.01)  # Very short hold
                    await lock.release()
                    results.append(f"worker_{worker_id}_success")
                else:
                    results.append(f"worker_{worker_id}_failed")
            except Exception as e:
                results.append(f"worker_{worker_id}_error: {e}")

        # Run many workers
        tasks = [worker(i) for i in range(50)]
        await asyncio.gather(*tasks)

        # Should have had some successful acquisitions
        assert successful_acquisitions > 0
        # Should have no errors
        error_count = sum(1 for r in results if "error" in r)
        assert error_count == 0

    @pytest.mark.asyncio
    async def test_lock_retries_on_transient_failure(self, temp_lock_file):
        """Test lock retry behavior on transient failures"""
        call_count = 0

        # Mock file operations to fail initially
        original_open = open
        failing_locks = set()

        class FailingFile:
            def __init__(self, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise OSError("Simulated filesystem error")
                self.file = original_open(*args, **kwargs)

            def __enter__(self):
                return self.file.__enter__()

            def __exit__(self, *args):
                return self.file.__exit__(*args)

            def write(self, data):
                return self.file.write(data)

            def close(self):
                return self.file.close()

        with patch("builtins.open", FailingFile):
            lock = FileLock(temp_lock_file, retry_delay=0.01)

            # Should eventually succeed after retries
            acquired = await lock.acquire()
            assert acquired is True

            await lock.release()

    @pytest.mark.asyncio
    async def test_lock_with_zero_timeout(self, temp_lock_file):
        """Test lock with zero timeout (non-blocking)"""
        lock = FileLock(temp_lock_file, timeout=0)

        # Acquire from first worker
        acquired1 = await lock.acquire()
        assert acquired1 is True

        # Second worker should fail immediately with zero timeout
        lock2 = FileLock(temp_lock_file, timeout=0)
        acquired2 = await lock2.acquire()
        assert acquired2 is False

        await lock.release()

    @pytest.mark.asyncio
    async def test_lock_stress_test(self):
        """Stress test for lock under various conditions"""
        lock = MemoryLock()
        results = []
        errors = []

        async def stress_worker(worker_id):
            try:
                for _ in range(10):
                    if await lock.acquire():
                        await asyncio.sleep(0.001)  # Very short hold
                        await lock.release()
                    else:
                        # Lock was busy, that's OK
                        pass
                results.append(f"worker_{worker_id}_completed")
            except Exception as e:
                errors.append(f"worker_{worker_id}_error: {e}")

        # Run stress test
        tasks = [stress_worker(i) for i in range(20)]
        await asyncio.gather(*tasks)

        # All workers should complete without errors
        assert len(errors) == 0
        assert len(results) == 20


@pytest.mark.unit
@pytest.mark.migration
class TestMigrationEngineWithImprovedLocking:
    """Test migration engine with improved lock handling"""

    @pytest.mark.asyncio
    async def test_migration_handles_lock_cleanup(self, async_migration_with_mock_lock):
        """Test that migration engine properly cleans up locks"""
        migration_engine, mock_lock = async_migration_with_mock_lock

        # Mock detector to return no changes
        async def mock_detect_changes():
            return []

        migration_engine.detector.detect_changes = mock_detect_changes

        # Run migration
        result = await migration_engine.auto_migrate()

        # Should complete successfully
        assert result.status == "up_to_date"

        # Lock operations should have been called
        mock_lock.acquire.assert_called_once()
        mock_lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_migration_handles_lock_failure_gracefully(self, async_migration_with_mock_lock):
        """Test migration engine handles lock failure gracefully"""
        migration_engine, mock_lock = async_migration_with_mock_lock

        # Mock lock acquisition to fail
        mock_lock.acquire = AsyncMock(return_value=False)

        # Run migration
        result = await migration_engine.auto_migrate()

        # Should return skipped status
        assert result.status == "skipped"

        # Lock acquire should be called, but not release
        mock_lock.acquire.assert_called_once()
        mock_lock.release.assert_not_called()

    @pytest.mark.asyncio
    async def test_migration_handles_lock_release_error(self, async_migration_with_mock_lock):
        """Test migration engine handles lock release errors"""
        migration_engine, mock_lock = async_migration_with_mock_lock

        # Mock lock release to fail
        mock_lock.release = AsyncMock(side_effect=Exception("Lock release failed"))

        # Mock detector to return no changes
        async def mock_detect_changes():
            return []

        migration_engine.detector.detect_changes = mock_detect_changes

        # Should still complete migration despite release error
        result = await migration_engine.auto_migrate()
        assert result.status == "up_to_date"

        # Lock operations should have been attempted
        mock_lock.acquire.assert_called_once()
        mock_lock.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_migration_with_storage_and_lock_errors(self, async_migration_with_mock_lock):
        """Test migration with both storage and lock errors"""
        migration_engine, mock_lock = async_migration_with_mock_lock

        # Mock storage to fail
        migration_engine.storage.record_migration = Mock(side_effect=Exception("Storage error"))

        # Mock detector to return no changes
        async def mock_detect_changes():
            return []

        migration_engine.detector.detect_changes = mock_detect_changes

        # Should handle storage error gracefully
        result = await migration_engine.auto_migrate()
        assert result.status == "up_to_date"

        # Lock should still be properly managed
        mock_lock.acquire.assert_called_once()
        mock_lock.release.assert_called_once()
