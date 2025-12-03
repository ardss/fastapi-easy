"""性能测试 - 迁移系统性能基准"""
import time

import pytest
from sqlalchemy import MetaData, create_engine

from fastapi_easy.migrations.engine import MigrationEngine
from fastapi_easy.migrations.storage import MigrationStorage


@pytest.fixture
def in_memory_engine():
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def migration_engine(in_memory_engine):
    metadata = MetaData()
    engine = MigrationEngine(in_memory_engine, metadata)
    engine.storage.initialize()
    return engine


class TestMigrationPerformance:
    """迁移系统性能测试"""

    def test_single_migration_record_performance(self, migration_engine):
        """单个迁移记录性能"""
        start = time.time()
        migration_engine.storage.record_migration("001", "Test", "ROLLBACK", "SAFE")
        elapsed = time.time() - start

        # 应该在 100ms 内完成
        assert elapsed < 0.1

    def test_bulk_migration_record_performance(self, migration_engine):
        """批量迁移记录性能"""
        start = time.time()
        for i in range(1, 101):
            migration_engine.storage.record_migration(
                f"{i:03d}",
                f"Migration {i}",
                "ROLLBACK",
                "SAFE"
            )
        elapsed = time.time() - start

        # 100 个迁移应该在 5 秒内完成
        assert elapsed < 5.0

    def test_history_retrieval_performance(self, migration_engine):
        """历史检索性能"""
        # 先记录一些迁移
        for i in range(1, 51):
            migration_engine.storage.record_migration(
                f"{i:03d}",
                f"Migration {i}",
                "ROLLBACK",
                "SAFE"
            )

        # 测试检索性能
        start = time.time()
        history = migration_engine.storage.get_migration_history(limit=50)
        elapsed = time.time() - start

        # 检索应该在 100ms 内完成
        assert elapsed < 0.1
        assert len(history) == 50

    def test_large_batch_performance(self, migration_engine):
        """大批量性能"""
        start = time.time()
        for i in range(1, 501):
            migration_engine.storage.record_migration(
                f"{i:04d}",
                f"Migration {i}",
                "ROLLBACK",
                "SAFE"
            )
        elapsed = time.time() - start

        # 500 个迁移应该在 30 秒内完成
        assert elapsed < 30.0

    def test_concurrent_storage_performance(self, in_memory_engine):
        """并发存储性能"""
        storage1 = MigrationStorage(in_memory_engine)
        storage1.initialize()

        storage2 = MigrationStorage(in_memory_engine)

        start = time.time()
        for i in range(1, 26):
            storage1.record_migration(f"{i:03d}", f"Mig {i}", "ROLLBACK", "SAFE")
            history = storage2.get_migration_history(limit=100)
        elapsed = time.time() - start

        # 应该在 2 秒内完成
        assert elapsed < 2.0


class TestMigrationMemoryUsage:
    """迁移系统内存使用测试"""

    def test_memory_efficient_bulk_operations(self, migration_engine):
        """内存高效的批量操作"""
        # 记录大量迁移而不应该导致内存溢出
        for i in range(1, 1001):
            migration_engine.storage.record_migration(
                f"{i:04d}",
                f"Migration {i}",
                "ROLLBACK",
                "SAFE"
            )

        # 应该能够检索所有记录
        history = migration_engine.storage.get_migration_history(limit=1000)
        assert len(history) == 1000

    def test_history_limit_performance(self, migration_engine):
        """历史限制性能"""
        # 记录 100 个迁移
        for i in range(1, 101):
            migration_engine.storage.record_migration(
                f"{i:03d}",
                f"Migration {i}",
                "ROLLBACK",
                "SAFE"
            )

        # 测试不同限制的性能
        start = time.time()
        history = migration_engine.storage.get_migration_history(limit=10)
        elapsed = time.time() - start

        assert elapsed < 0.1
        assert len(history) <= 10


class TestMigrationThroughput:
    """迁移系统吞吐量测试"""

    def test_records_per_second(self, migration_engine):
        """每秒记录数"""
        start = time.time()
        count = 0

        while time.time() - start < 1.0:
            migration_engine.storage.record_migration(
                f"{count:05d}",
                f"Migration {count}",
                "ROLLBACK",
                "SAFE"
            )
            count += 1

        # 应该至少能处理 100 条/秒
        assert count >= 100

    def test_queries_per_second(self, migration_engine):
        """每秒查询数"""
        # 先记录一些迁移
        for i in range(1, 51):
            migration_engine.storage.record_migration(
                f"{i:03d}",
                f"Migration {i}",
                "ROLLBACK",
                "SAFE"
            )

        start = time.time()
        count = 0

        while time.time() - start < 1.0:
            migration_engine.storage.get_migration_history(limit=50)
            count += 1

        # 应该至少能处理 1000 次查询/秒
        assert count >= 1000
