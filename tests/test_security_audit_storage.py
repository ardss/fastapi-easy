"""Tests for audit storage"""

import pytest

from fastapi_easy.security.audit_storage import (
    DatabaseAuditStorage,
    MemoryAuditStorage,
)


class TestMemoryAuditStorage:
    """Test memory audit storage"""

    def test_init_valid(self):
        """Test initialization with valid parameters"""
        storage = MemoryAuditStorage(max_logs=1000)
        assert storage.max_logs == 1000
        assert storage.get_count() == 0

    def test_init_default(self):
        """Test initialization with default parameters"""
        storage = MemoryAuditStorage()
        assert storage.max_logs == 10000

    def test_init_invalid_max_logs(self):
        """Test initialization with invalid max_logs"""
        with pytest.raises(ValueError):
            MemoryAuditStorage(max_logs=0)

        with pytest.raises(ValueError):
            MemoryAuditStorage(max_logs=-1)

        with pytest.raises(ValueError):
            MemoryAuditStorage(max_logs="invalid")

    @pytest.mark.asyncio
    async def test_save_valid(self):
        """Test saving valid log"""
        storage = MemoryAuditStorage()
        log = {"user_id": "user1", "action": "login"}

        await storage.save(log)
        assert storage.get_count() == 1

    @pytest.mark.asyncio
    async def test_save_invalid_type(self):
        """Test saving invalid log type"""
        storage = MemoryAuditStorage()

        with pytest.raises(TypeError):
            await storage.save("invalid")

    @pytest.mark.asyncio
    async def test_save_exceeds_max(self):
        """Test saving when exceeds max logs"""
        storage = MemoryAuditStorage(max_logs=3)

        for i in range(5):
            await storage.save({"id": i})

        assert storage.get_count() == 3
        # Oldest logs should be removed
        logs = await storage.query()
        assert logs[0]["id"] == 2

    @pytest.mark.asyncio
    async def test_query_all(self):
        """Test querying all logs"""
        storage = MemoryAuditStorage()

        for i in range(3):
            await storage.save({"id": i, "user_id": "user1"})

        logs = await storage.query()
        assert len(logs) == 3

    @pytest.mark.asyncio
    async def test_query_with_filter(self):
        """Test querying with filter"""
        storage = MemoryAuditStorage()

        await storage.save({"user_id": "user1", "action": "login"})
        await storage.save({"user_id": "user2", "action": "login"})
        await storage.save({"user_id": "user1", "action": "logout"})

        logs = await storage.query(user_id="user1")
        assert len(logs) == 2

    @pytest.mark.asyncio
    async def test_query_with_multiple_filters(self):
        """Test querying with multiple filters"""
        storage = MemoryAuditStorage()

        await storage.save({"user_id": "user1", "action": "login"})
        await storage.save({"user_id": "user1", "action": "logout"})
        await storage.save({"user_id": "user2", "action": "login"})

        logs = await storage.query(user_id="user1", action="login")
        assert len(logs) == 1

    @pytest.mark.asyncio
    async def test_query_no_match(self):
        """Test querying with no matches"""
        storage = MemoryAuditStorage()

        await storage.save({"user_id": "user1"})

        logs = await storage.query(user_id="user2")
        assert len(logs) == 0

    @pytest.mark.asyncio
    async def test_delete_all(self):
        """Test deleting all logs"""
        storage = MemoryAuditStorage()

        for i in range(3):
            await storage.save({"id": i})

        deleted = await storage.delete()
        assert deleted == 3
        assert storage.get_count() == 0

    @pytest.mark.asyncio
    async def test_delete_with_filter(self):
        """Test deleting with filter"""
        storage = MemoryAuditStorage()

        await storage.save({"user_id": "user1"})
        await storage.save({"user_id": "user2"})
        await storage.save({"user_id": "user1"})

        deleted = await storage.delete(user_id="user1")
        assert deleted == 2
        assert storage.get_count() == 1

    @pytest.mark.asyncio
    async def test_delete_no_match(self):
        """Test deleting with no matches"""
        storage = MemoryAuditStorage()

        await storage.save({"user_id": "user1"})

        deleted = await storage.delete(user_id="user2")
        assert deleted == 0
        assert storage.get_count() == 1

    def test_clear(self):
        """Test clearing all logs"""
        storage = MemoryAuditStorage()
        storage.logs = [{"id": 1}, {"id": 2}]

        storage.clear()
        assert storage.get_count() == 0


class TestDatabaseAuditStorage:
    """Test database audit storage"""

    def test_init(self):
        """Test initialization"""
        storage = DatabaseAuditStorage()
        assert storage.db_session is None

    def test_init_with_session(self):
        """Test initialization with session"""
        session = object()
        storage = DatabaseAuditStorage(db_session=session)
        assert storage.db_session is session

    @pytest.mark.asyncio
    async def test_save(self):
        """Test saving log"""
        storage = DatabaseAuditStorage()
        log = {"user_id": "user1", "action": "login"}

        # Should not raise
        await storage.save(log)

    @pytest.mark.asyncio
    async def test_save_invalid_type(self):
        """Test saving invalid log type"""
        storage = DatabaseAuditStorage()

        with pytest.raises(TypeError):
            await storage.save("invalid")

    @pytest.mark.asyncio
    async def test_query(self):
        """Test querying logs"""
        storage = DatabaseAuditStorage()

        logs = await storage.query(user_id="user1")
        assert logs == []

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test deleting logs"""
        storage = DatabaseAuditStorage()

        deleted = await storage.delete(user_id="user1")
        assert deleted == 0
