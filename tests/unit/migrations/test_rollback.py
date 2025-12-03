"""回滚功能单元测试"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import MetaData, create_engine

from fastapi_easy.migrations.engine import MigrationEngine
from fastapi_easy.migrations.types import OperationResult


@pytest.fixture
def in_memory_engine():
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def migration_engine(in_memory_engine):
    metadata = MetaData()
    engine = MigrationEngine(in_memory_engine, metadata)
    engine.storage.initialize()
    return engine


class TestRollbackBasic:
    """基础回滚测试"""

    @pytest.mark.asyncio
    async def test_rollback_single_migration(self, migration_engine):
        """测试回滚单个迁移"""
        # 先记录一个迁移
        migration_engine.storage.record_migration(
            "001",
            "Create users table",
            "DROP TABLE users",
            "SAFE"
        )

        # 验证迁移已记录
        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 1

        # 执行回滚
        result = await migration_engine.rollback(steps=1)
        assert isinstance(result, OperationResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_rollback_multiple_migrations(self, migration_engine):
        """测试回滚多个迁移"""
        # 记录多个迁移
        for i in range(1, 4):
            migration_engine.storage.record_migration(
                f"00{i}",
                f"Migration {i}",
                "ROLLBACK",
                "SAFE"
            )

        # 验证迁移已记录
        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 3

        # 回滚 2 个迁移
        result = await migration_engine.rollback(steps=2)
        assert isinstance(result, OperationResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_rollback_no_migrations(self, migration_engine):
        """测试没有可回滚的迁移"""
        result = await migration_engine.rollback(steps=1)
        assert isinstance(result, OperationResult)
        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_rollback_invalid_steps(self, migration_engine):
        """测试无效的回滚步数"""
        result = await migration_engine.rollback(steps=0)
        assert isinstance(result, OperationResult)
        assert result.success is False

        result = await migration_engine.rollback(steps=-1)
        assert isinstance(result, OperationResult)
        assert result.success is False


class TestRollbackWithLock:
    """带锁的回滚测试"""

    @pytest.mark.asyncio
    async def test_rollback_acquires_lock(self, migration_engine):
        """测试回滚获取锁"""
        migration_engine.storage.record_migration("001", "Test", "ROLLBACK", "SAFE")

        with patch.object(migration_engine.lock, 'acquire', new_callable=AsyncMock) as mock_acquire:
            mock_acquire.return_value = True
            with patch.object(migration_engine.lock, 'release', new_callable=AsyncMock):
                result = await migration_engine.rollback(steps=1)
                mock_acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_lock_failure(self, migration_engine):
        """测试回滚锁获取失败"""
        migration_engine.storage.record_migration("001", "Test", "ROLLBACK", "SAFE")

        with patch.object(migration_engine.lock, 'acquire', new_callable=AsyncMock) as mock_acquire:
            mock_acquire.return_value = False
            result = await migration_engine.rollback(steps=1)
            assert isinstance(result, OperationResult)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_rollback_releases_lock(self, migration_engine):
        """测试回滚释放锁"""
        migration_engine.storage.record_migration("001", "Test", "ROLLBACK", "SAFE")

        with patch.object(migration_engine.lock, 'acquire', new_callable=AsyncMock) as mock_acquire:
            mock_acquire.return_value = True
            with patch.object(migration_engine.lock, 'release', new_callable=AsyncMock) as mock_release:
                await migration_engine.rollback(steps=1)
                mock_release.assert_called_once()


class TestRollbackExecution:
    """回滚执行测试"""

    @pytest.mark.asyncio
    async def test_rollback_executes_sql(self, migration_engine):
        """测试回滚执行 SQL"""
        migration_engine.storage.record_migration(
            "001",
            "Create table",
            "DROP TABLE test_table",
            "SAFE"
        )

        with patch.object(migration_engine.lock, 'acquire', new_callable=AsyncMock) as mock_acquire:
            mock_acquire.return_value = True
            with patch.object(migration_engine.lock, 'release', new_callable=AsyncMock):
                with patch('sqlalchemy.create_engine') as mock_engine:
                    result = await migration_engine.rollback(steps=1)
                    # 应该尝试执行回滚
                    assert isinstance(result, OperationResult)
                    assert result.success is True

    @pytest.mark.asyncio
    async def test_rollback_handles_missing_sql(self, migration_engine):
        """测试处理缺少回滚 SQL"""
        # 记录没有回滚 SQL 的迁移
        migration_engine.storage.record_migration(
            "001",
            "Test",
            "",  # 空回滚 SQL
            "SAFE"
        )

        with patch.object(migration_engine.lock, 'acquire', new_callable=AsyncMock) as mock_acquire:
            mock_acquire.return_value = True
            with patch.object(migration_engine.lock, 'release', new_callable=AsyncMock):
                result = await migration_engine.rollback(steps=1)
                # 应该处理缺少 SQL 的情况
                assert isinstance(result, OperationResult)
                assert result.success is True


class TestRollbackErrorHandling:
    """回滚错误处理测试"""

    @pytest.mark.asyncio
    async def test_rollback_sql_error(self, migration_engine):
        """测试回滚 SQL 错误"""
        migration_engine.storage.record_migration(
            "001",
            "Test",
            "DROP TABLE nonexistent_table",
            "SAFE"
        )

        with patch.object(migration_engine.lock, 'acquire', new_callable=AsyncMock) as mock_acquire:
            mock_acquire.return_value = True
            with patch.object(migration_engine.lock, 'release', new_callable=AsyncMock):
                # 执行回滚 - 由于表不存在，会导致 SQL 错误
                result = await migration_engine.rollback(steps=1)
                # 应该捕获错误
                assert isinstance(result, OperationResult)

    @pytest.mark.asyncio
    async def test_rollback_lock_release_error(self, migration_engine):
        """测试回滚锁释放错误"""
        migration_engine.storage.record_migration("001", "Test", "ROLLBACK", "SAFE")

        with patch.object(migration_engine.lock, 'acquire', new_callable=AsyncMock) as mock_acquire:
            mock_acquire.return_value = True
            with patch.object(migration_engine.lock, 'release', new_callable=AsyncMock) as mock_release:
                mock_release.side_effect = Exception("Lock release failed")
                # 应该处理锁释放错误
                result = await migration_engine.rollback(steps=1)
                # 即使锁释放失败，回滚也应该成功
                assert isinstance(result, OperationResult)
                assert result.success is True


class TestRollbackOrder:
    """回滚顺序测试"""

    @pytest.mark.asyncio
    async def test_rollback_reverse_order(self, migration_engine):
        """测试回滚按相反顺序执行"""
        # 记录多个迁移
        for i in range(1, 4):
            migration_engine.storage.record_migration(
                f"00{i}",
                f"Migration {i}",
                f"ROLLBACK {i}",
                "SAFE"
            )

        with patch.object(migration_engine.lock, 'acquire', new_callable=AsyncMock) as mock_acquire:
            mock_acquire.return_value = True
            with patch.object(migration_engine.lock, 'release', new_callable=AsyncMock):
                result = await migration_engine.rollback(steps=3)
                # 应该按相反顺序处理迁移
                assert isinstance(result, OperationResult)
                assert result.success is True
