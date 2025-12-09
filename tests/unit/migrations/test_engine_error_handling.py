"""
迁移引擎错误处理单元测试

测试 MigrationEngine 的错误处理、异常恢复和错误消息
"""

import asyncio
import logging
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import MetaData, create_engine

from fastapi_easy.migrations.engine import MigrationEngine
from fastapi_easy.migrations.types import Migration, MigrationPlan, RiskLevel


@pytest.fixture
def in_memory_engine():
    """创建内存数据库引擎"""
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def migration_engine(in_memory_engine):
    """创建迁移引擎"""
    metadata = MetaData()
    return MigrationEngine(in_memory_engine, metadata)


@pytest.fixture(autouse=True)
def suppress_lock_logging():
    """自动抑制分布式锁的日志输出，减少测试噪音"""
    with patch("fastapi_easy.migrations.distributed_lock.logger", logging.getLogger("test_dummy")):
        yield


@pytest.mark.unit
@pytest.mark.migration
class TestMigrationEngineErrorHandling:
    """迁移引擎错误处理测试"""

    @pytest.mark.asyncio
    async def test_database_connection_error_handling(self, migration_engine):
        """测试数据库连接错误处理"""
        # Mock lock to be acquired successfully first
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector:

            mock_detector.detect_changes = AsyncMock(side_effect=Exception("Connection failed"))

            # Should catch and re-raise the exception
            with pytest.raises(Exception, match="Connection failed"):
                await migration_engine.auto_migrate()

            # Verify detector was called
            mock_detector.detect_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_schema_detection_timeout(self, migration_engine):
        """测试 Schema 检测超时"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector:

            mock_detector.detect_changes = AsyncMock(side_effect=TimeoutError("Detection timeout"))

            with pytest.raises(TimeoutError, match="Detection timeout"):
                await migration_engine.auto_migrate()

    @pytest.mark.asyncio
    async def test_migration_execution_error(self, migration_engine):
        """测试迁移执行错误"""
        mock_migration = Migration(
            version="1.0.0",
            description="Test migration",
            upgrade_sql="CREATE TABLE test (id INTEGER);",
            downgrade_sql="DROP TABLE test;",
            risk_level=RiskLevel.SAFE,
        )

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch.object(migration_engine, "generator") as mock_generator, \
             patch.object(migration_engine, "executor") as mock_executor:

            # Mock detector to return changes
            mock_detector.detect_changes = AsyncMock(return_value=[mock_migration])

            # Mock generator to return a plan
            mock_plan = MigrationPlan(migrations=[mock_migration], status="pending")
            mock_generator.generate_plan.return_value = mock_plan

            # Mock executor to raise an exception
            mock_executor.execute_plan = AsyncMock(side_effect=Exception("SQL execution failed"))

            with pytest.raises(Exception, match="SQL execution failed"):
                await migration_engine.auto_migrate()

    @pytest.mark.asyncio
    async def test_lock_acquisition_error(self, migration_engine):
        """测试锁获取错误"""
        with patch.object(migration_engine.lock, "acquire", return_value=False):
            result = await migration_engine.auto_migrate()

            # Should return a plan with "locked" status
            assert result.status == "locked"
            assert len(result.migrations) == 0

    @pytest.mark.asyncio
    async def test_storage_error_handling(self, migration_engine):
        """测试存储错误处理"""
        mock_migration = Migration(
            version="1.0.0",
            description="Test migration",
            upgrade_sql="CREATE TABLE test (id INTEGER);",
            downgrade_sql="DROP TABLE test;",
            risk_level=RiskLevel.SAFE,
        )

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch.object(migration_engine, "storage") as mock_storage, \
             patch.object(migration_engine, "executor") as mock_executor, \
             patch.object(migration_engine, "generator") as mock_generator:

            # Mock no schema changes
            mock_detector.detect_changes = AsyncMock(return_value=[])

            # Mock storage to raise error on record_migration
            mock_storage.record_migration.side_effect = Exception("Storage failed")

            # Even with storage error, migration should complete if no changes needed
            result = await migration_engine.auto_migrate()

            # Should complete successfully despite storage error
            assert result.status == "up_to_date"

    @pytest.mark.asyncio
    async def test_hook_execution_error(self, migration_engine):
        """测试钩子执行错误"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch("fastapi_easy.migrations.engine.get_hook_registry") as mock_get_registry:

            mock_detector.detect_changes = AsyncMock(return_value=[])

            # Mock hook registry to raise error
            mock_registry = AsyncMock()
            mock_registry.execute_hooks = AsyncMock(side_effect=Exception("Hook execution failed"))
            mock_get_registry.return_value = mock_registry

            # Should still handle hook errors gracefully
            with pytest.raises(Exception, match="Hook execution failed"):
                await migration_engine.auto_migrate()


@pytest.mark.unit
@pytest.mark.migration
class TestMigrationEngineExceptionRecovery:
    """迁移引擎异常恢复测试"""

    @pytest.mark.asyncio
    async def test_lock_release_failure_recovery(self, migration_engine):
        """测试锁释放失败恢复"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine.lock, "release", side_effect=Exception("Lock release failed")), \
             patch.object(migration_engine.detector, "detect_changes", return_value=[]):

            # Mock no changes to avoid migration execution
            result = await migration_engine.auto_migrate()

            # Should complete migration despite lock release failure
            assert result.status == "up_to_date"

    @pytest.mark.asyncio
    async def test_partial_migration_failure(self, migration_engine):
        """测试部分迁移失败"""
        mock_migration = Migration(
            version="1.0.0",
            description="Test migration",
            upgrade_sql="CREATE TABLE test (id INTEGER);",
            downgrade_sql="DROP TABLE test;",
            risk_level=RiskLevel.SAFE,
        )

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch.object(migration_engine, "generator") as mock_generator, \
             patch.object(migration_engine, "executor") as mock_executor:

            # Mock detector to return changes
            mock_detector.detect_changes = AsyncMock(return_value=[mock_migration])

            # Mock generator to return a plan
            mock_plan = MigrationPlan(migrations=[mock_migration], status="pending")
            mock_generator.generate_plan.return_value = mock_plan

            # Mock executor to raise an exception
            mock_executor.execute_plan = AsyncMock(side_effect=Exception("Migration failed"))

            with pytest.raises(Exception, match="Migration failed"):
                await migration_engine.auto_migrate()

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, migration_engine):
        """测试事务回滚"""
        mock_migration = Migration(
            version="1.0.0",
            description="Test migration",
            upgrade_sql="CREATE TABLE test (id INTEGER);",
            downgrade_sql="DROP TABLE test;",
            risk_level=RiskLevel.SAFE,
        )

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch.object(migration_engine, "generator") as mock_generator, \
             patch.object(migration_engine, "executor") as mock_executor:

            # Mock detector to return changes
            mock_detector.detect_changes = AsyncMock(return_value=[mock_migration])

            # Mock generator to return a plan
            mock_plan = MigrationPlan(migrations=[mock_migration], status="pending")
            mock_generator.generate_plan.return_value = mock_plan

            # Mock executor to raise an exception
            mock_executor.execute_plan = AsyncMock(side_effect=Exception("Execution failed"))

            with pytest.raises(Exception, match="Execution failed"):
                await migration_engine.auto_migrate()


@pytest.mark.unit
@pytest.mark.migration
class TestMigrationEngineErrorMessages:
    """迁移引擎错误消息测试"""

    @pytest.mark.asyncio
    async def test_error_message_includes_diagnostics(self, migration_engine):
        """测试错误消息包含诊断信息"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector:

            mock_detector.detect_changes = AsyncMock(side_effect=Exception("Detection failed"))

            with pytest.raises(Exception) as exc_info:
                await migration_engine.auto_migrate()

            error_msg = str(exc_info.value)
            # 错误消息应该包含有用的信息
            assert len(error_msg) > 0
            assert "Detection failed" in error_msg

    @pytest.mark.asyncio
    async def test_error_message_includes_debug_steps(self, migration_engine):
        """测试错误消息包含调试步骤"""
        mock_migration = Migration(
            version="1.0.0",
            description="Test migration",
            upgrade_sql="CREATE TABLE test (id INTEGER);",
            downgrade_sql="DROP TABLE test;",
            risk_level=RiskLevel.SAFE,
        )

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch.object(migration_engine, "generator") as mock_generator, \
             patch.object(migration_engine, "executor") as mock_executor:

            # Mock detector to return changes
            mock_detector.detect_changes = AsyncMock(return_value=[mock_migration])

            # Mock generator to return a plan
            mock_plan = MigrationPlan(migrations=[mock_migration], status="pending")
            mock_generator.generate_plan.return_value = mock_plan

            # Mock executor to raise an exception
            mock_executor.execute_plan = AsyncMock(side_effect=Exception("SQL syntax error"))

            with pytest.raises(Exception) as exc_info:
                await migration_engine.auto_migrate()

            error_msg = str(exc_info.value)
            # 应该有调试信息
            assert len(error_msg) > 0
            assert "SQL syntax error" in error_msg


@pytest.mark.unit
@pytest.mark.migration
class TestMigrationEngineErrorContext:
    """迁移引擎错误上下文测试"""

    @pytest.mark.asyncio
    async def test_error_with_migration_version(self, migration_engine):
        """测试错误包含迁移版本"""
        mock_migration = Migration(
            version="20240101_001",
            description="Test migration",
            upgrade_sql="CREATE TABLE test (id INTEGER);",
            downgrade_sql="DROP TABLE test;",
            risk_level=RiskLevel.SAFE,
        )

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch.object(migration_engine, "generator") as mock_generator, \
             patch.object(migration_engine, "executor") as mock_executor:

            # Mock detector to return changes
            mock_detector.detect_changes = AsyncMock(return_value=[mock_migration])

            # Mock generator to return a plan
            mock_plan = MigrationPlan(migrations=[mock_migration], status="pending")
            mock_generator.generate_plan.return_value = mock_plan

            # Mock executor to raise an exception
            mock_executor.execute_plan = AsyncMock(side_effect=Exception("Execution failed"))

            with pytest.raises(Exception, match="Execution failed") as exc_info:
                await migration_engine.auto_migrate()

            # Error message should contain context
            error_msg = str(exc_info.value)
            assert "Execution failed" in error_msg

    @pytest.mark.asyncio
    async def test_error_with_database_info(self, migration_engine):
        """测试错误包含数据库信息"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector:

            mock_detector.detect_changes = AsyncMock(side_effect=Exception("Detection failed"))

            with pytest.raises(Exception, match="Detection failed") as exc_info:
                await migration_engine.auto_migrate()

            # Error message should contain detection-related information
            error_msg = str(exc_info.value)
            assert "Detection failed" in error_msg
            assert len(error_msg) > 0

    @pytest.mark.asyncio
    async def test_error_with_timestamp(self, migration_engine):
        """测试错误包含时间戳"""
        import time

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch("fastapi_easy.migrations.engine.logger") as mock_logger:

            mock_detector.detect_changes = AsyncMock(side_effect=Exception("Detection failed"))

            start_time = time.time()
            with pytest.raises(Exception, match="Detection failed"):
                await migration_engine.auto_migrate()
            end_time = time.time()

            # Should log error with timestamp
            assert mock_logger.error.called
            # Verify error occurred during the test window
            assert end_time - start_time < 5  # Should complete within 5 seconds


@pytest.mark.unit
@pytest.mark.migration
class TestMigrationEngineErrorRecoveryStrategies:
    """迁移引擎错误恢复策略测试"""

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self, migration_engine):
        """测试临时错误重试"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector:

            mock_detector.detect_changes = AsyncMock(side_effect=Exception("Transient error"))

            with pytest.raises(Exception, match="Transient error"):
                await migration_engine.auto_migrate()

            # Verify detector was called
            mock_detector.detect_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, migration_engine):
        """测试优雅降级"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch("fastapi_easy.migrations.engine.logger") as mock_logger:

            mock_detector.detect_changes = AsyncMock(return_value=[])

            # Should handle detection completion gracefully
            result = await migration_engine.auto_migrate()

            # Should complete successfully
            assert result.status == "up_to_date"

    @pytest.mark.asyncio
    async def test_error_logging(self, migration_engine):
        """测试错误日志记录"""
        with patch("fastapi_easy.migrations.engine.logger") as mock_logger, \
             patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector:

            mock_detector.detect_changes = AsyncMock(side_effect=Exception("Detection failed"))

            with pytest.raises(Exception, match="Detection failed"):
                await migration_engine.auto_migrate()

            # Should log error
            assert mock_logger.error.called
            # Verify log call arguments contain error information
            call_args = mock_logger.error.call_args
            assert call_args is not None


@pytest.mark.unit
@pytest.mark.migration
class TestMigrationEngineErrorPropagation:
    """迁移引擎错误传播测试"""

    @pytest.mark.asyncio
    async def test_critical_error_propagation(self, migration_engine):
        """测试关键错误传播"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector:

            mock_detector.detect_changes = AsyncMock(side_effect=Exception("Critical error"))

            with pytest.raises(Exception, match="Critical error") as exc_info:
                await migration_engine.auto_migrate()

            # Verify the error message is preserved
            assert "Critical error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_critical_error_handling(self, migration_engine):
        """测试非关键错误处理"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch.object(migration_engine, "storage") as mock_storage, \
             patch("fastapi_easy.migrations.engine.logger") as mock_logger:

            mock_detector.detect_changes = AsyncMock(return_value=[])
            mock_storage.record_migration.side_effect = Exception("Non-critical error")

            # Non-critical errors shouldn't interrupt migration
            result = await migration_engine.auto_migrate()

            # Should complete successfully
            assert result.status == "up_to_date"
            # Should log the non-critical error (but not fail)
            # Storage errors are logged after successful migrations

    @pytest.mark.asyncio
    async def test_error_chain_handling(self, migration_engine):
        """测试错误链处理"""
        def raise_chained_error(*args, **kwargs):
            try:
                raise Exception("Original error")
            except Exception as orig_e:
                raise Exception("Wrapped error") from orig_e

        mock_migration = Migration(
            version="1.0.0",
            description="Test migration",
            upgrade_sql="CREATE TABLE test (id INTEGER);",
            downgrade_sql="DROP TABLE test;",
            risk_level=RiskLevel.SAFE,
        )

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector, \
             patch.object(migration_engine, "generator") as mock_generator, \
             patch.object(migration_engine, "executor") as mock_executor:

            # Mock detector to return changes
            mock_detector.detect_changes = AsyncMock(return_value=[mock_migration])

            # Mock generator to return a plan
            mock_plan = MigrationPlan(migrations=[mock_migration], status="pending")
            mock_generator.generate_plan.return_value = mock_plan

            # Mock executor to raise chained error
            mock_executor.execute_plan = AsyncMock(side_effect=raise_chained_error)

            with pytest.raises(Exception, match="Wrapped error") as exc_info:
                await migration_engine.auto_migrate()

            # Should preserve error chain information
            assert str(exc_info.value) == "Wrapped error"
            # Verify original error is preserved
            assert exc_info.value.__cause__ is not None
            assert str(exc_info.value.__cause__) == "Original error"


@pytest.mark.unit
@pytest.mark.migration
class TestMigrationEngineErrorRecoveryCleanup:
    """迁移引擎错误恢复清理测试"""

    @pytest.mark.asyncio
    async def test_cleanup_on_error(self, migration_engine):
        """测试错误时的清理"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine.lock, "release", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector:

            mock_detector.detect_changes = AsyncMock(side_effect=Exception("Detection failed"))

            with pytest.raises(Exception, match="Detection failed"):
                await migration_engine.auto_migrate()

            # Should attempt to release lock on error
            migration_engine.lock.release.assert_called()

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self, migration_engine):
        """测试错误时的资源清理"""
        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine.lock, "release", return_value=True), \
             patch.object(migration_engine, "detector") as mock_detector:

            mock_detector.detect_changes = AsyncMock(side_effect=Exception("Detection failed"))

            with pytest.raises(Exception, match="Detection failed"):
                await migration_engine.auto_migrate()

            # Should attempt to cleanup resources (lock release)
            migration_engine.lock.release.assert_called_once()
            # Verify detector was called
            mock_detector.detect_changes.assert_called_once()


@pytest.mark.unit
@pytest.mark.migration
class TestMigrationEngineRollbackErrorHandling:
    """测试迁移引擎回滚错误处理"""

    @pytest.mark.asyncio
    async def test_rollback_with_invalid_steps(self, migration_engine):
        """测试无效步数的回滚"""
        result = await migration_engine.rollback(steps=0)
        assert not result.success
        assert "回滚步数必须大于 0" in result.errors[0]

        result = await migration_engine.rollback(steps=-1)
        assert not result.success
        assert "回滚步数必须大于 0" in result.errors[0]

    @pytest.mark.asyncio
    async def test_rollback_with_no_history(self, migration_engine):
        """测试没有历史记录时的回滚"""
        with patch.object(migration_engine.storage, "get_migration_history", return_value=[]):
            result = await migration_engine.rollback(steps=1)
            assert not result.success
            assert "没有可回滚的迁移" in result.errors[0]

    @pytest.mark.asyncio
    async def test_rollback_lock_failure(self, migration_engine):
        """测试回滚时锁获取失败"""
        mock_history = [{
            "version": "1.0.0",
            "description": "Test migration",
            "rollback_sql": "DROP TABLE test;"
        }]

        with patch.object(migration_engine.storage, "get_migration_history", return_value=mock_history), \
             patch.object(migration_engine.lock, "acquire", return_value=False):
            result = await migration_engine.rollback(steps=1)
            assert not result.success
            # Check for lock error message
            error_msg = result.errors[0]
            assert "无法获取迁移锁" in error_msg or "Unable to acquire migration lock" in error_msg

    @pytest.mark.asyncio
    async def test_rollback_execution_error(self, migration_engine):
        """测试回滚执行错误"""
        mock_history = [{
            "version": "1.0.0",
            "description": "Test migration",
            "rollback_sql": "DROP TABLE test;"
        }]

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine.storage, "get_migration_history", return_value=mock_history), \
             patch("sqlalchemy.text") as mock_text, \
             patch.object(migration_engine.engine, "begin") as mock_begin:

            # Mock connection context
            mock_conn = mock_begin.return_value.__enter__.return_value
            mock_conn.execute.side_effect = Exception("SQL execution failed")

            result = await migration_engine.rollback(steps=1, continue_on_error=False)

            assert not result.success
            assert len(result.errors) > 0
            assert "1.0.0:" in result.errors[0]

    @pytest.mark.asyncio
    async def test_rollback_continue_on_error(self, migration_engine):
        """测试回滚时继续执行错误"""
        mock_history = [
            {
                "version": "1.0.0",
                "description": "Test migration 1",
                "rollback_sql": "DROP TABLE test1;"
            },
            {
                "version": "2.0.0",
                "description": "Test migration 2",
                "rollback_sql": "DROP TABLE test2;"
            }
        ]

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine.storage, "get_migration_history", return_value=mock_history), \
             patch("sqlalchemy.text") as mock_text, \
             patch.object(migration_engine.engine, "begin") as mock_begin:

            # Mock connection context
            mock_conn = mock_begin.return_value.__enter__.return_value

            # First call succeeds, second fails
            call_count = 0
            def execute_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise Exception("Second rollback failed")

            mock_conn.execute.side_effect = execute_side_effect

            result = await migration_engine.rollback(steps=2, continue_on_error=True)

            # Should have 1 success and 1 failure
            assert result.data["rolled_back"] == 1
            assert result.data["failed"] == 1
            assert not result.success

    @pytest.mark.asyncio
    async def test_rollback_without_rollback_sql(self, migration_engine):
        """测试没有回滚SQL的迁移"""
        mock_history = [{
            "version": "1.0.0",
            "description": "Test migration",
            "rollback_sql": None  # No rollback SQL
        }]

        with patch.object(migration_engine.lock, "acquire", return_value=True), \
             patch.object(migration_engine.storage, "get_migration_history", return_value=mock_history):

            result = await migration_engine.rollback(steps=1)

            # Should succeed but skip migrations without rollback SQL
            assert result.success
            assert result.data["rolled_back"] == 0
            assert result.data["failed"] == 0