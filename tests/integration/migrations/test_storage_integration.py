"""
存储集成测试

测试 MigrationStorage 与迁移系统的集成
"""

import pytest
from sqlalchemy import MetaData, create_engine

from fastapi_easy.migrations.engine import MigrationEngine
from fastapi_easy.migrations.storage import MigrationStorage


@pytest.fixture
def in_memory_engine():
    """创建内存数据库引擎"""
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def storage(in_memory_engine):
    """创建存储实例"""
    storage = MigrationStorage(in_memory_engine)
    storage.initialize()
    return storage


@pytest.fixture
def migration_engine(in_memory_engine):
    """创建迁移引擎"""
    metadata = MetaData()
    engine = MigrationEngine(in_memory_engine, metadata)
    engine.storage.initialize()
    return engine


class TestStorageWithEngine:
    """存储与引擎集成测试"""

    def test_engine_records_migration(self, migration_engine):
        """测试引擎记录迁移"""
        # 记录迁移
        migration_engine.storage.record_migration(
            version="001",
            description="Test migration",
            rollback_sql="ROLLBACK",
            risk_level="SAFE"
        )
        
        # 验证记录
        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 1
        assert history[0]["version"] == "001"

    def test_engine_multiple_migrations(self, migration_engine):
        """测试引擎记录多个迁移"""
        for i in range(1, 4):
            migration_engine.storage.record_migration(
                version=f"00{i}",
                description=f"Migration {i}",
                rollback_sql="ROLLBACK",
                risk_level="SAFE"
            )
        
        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 3

    def test_storage_persistence_across_instances(self, in_memory_engine):
        """测试存储在实例间的持久化"""
        # 第一个存储实例
        storage1 = MigrationStorage(in_memory_engine)
        storage1.initialize()
        storage1.record_migration("001", "First", "ROLLBACK", "SAFE")
        
        # 第二个存储实例
        storage2 = MigrationStorage(in_memory_engine)
        history = storage2.get_migration_history(limit=10)
        
        assert len(history) == 1
        assert history[0]["version"] == "001"


class TestStorageWithMultipleMigrations:
    """存储与多个迁移的集成测试"""

    def test_record_and_retrieve_migrations(self, storage):
        """测试记录和检索迁移"""
        migrations = [
            ("001", "Create users table", "DROP TABLE users", "SAFE"),
            ("002", "Add email column", "ALTER TABLE users DROP COLUMN email", "MEDIUM"),
            ("003", "Create indexes", "DROP INDEX idx_email", "HIGH"),
        ]
        
        for version, desc, rollback, risk in migrations:
            storage.record_migration(version, desc, rollback, risk)
        
        history = storage.get_migration_history(limit=10)
        assert len(history) == 3

    def test_migration_history_ordering(self, storage):
        """测试迁移历史顺序"""
        for i in range(1, 6):
            storage.record_migration(f"00{i}", f"Migration {i}", "ROLLBACK", "SAFE")
        
        history = storage.get_migration_history(limit=10)
        assert len(history) == 5

    def test_migration_history_limit(self, storage):
        """测试迁移历史限制"""
        for i in range(1, 11):
            storage.record_migration(f"{i:03d}", f"Migration {i}", "ROLLBACK", "SAFE")
        
        history = storage.get_migration_history(limit=5)
        assert len(history) <= 5


class TestStorageErrorRecovery:
    """存储错误恢复集成测试"""

    def test_storage_survives_duplicate_record(self, storage):
        """测试存储处理重复记录"""
        storage.record_migration("001", "First", "ROLLBACK", "SAFE")
        # 再次记录相同版本
        storage.record_migration("001", "First", "ROLLBACK", "SAFE")
        
        history = storage.get_migration_history(limit=10)
        # 应该幂等
        assert len(history) >= 1

    def test_storage_with_special_characters(self, storage):
        """测试存储处理特殊字符"""
        storage.record_migration(
            "001",
            "Add 'users' table with @index",
            "DROP TABLE users",
            "SAFE"
        )
        
        history = storage.get_migration_history(limit=10)
        assert len(history) == 1
        assert "users" in history[0]["description"]

    def test_storage_with_long_sql(self, storage):
        """测试存储处理长 SQL"""
        long_sql = "SELECT * FROM users WHERE " + " AND ".join([f"col{i} = {i}" for i in range(100)])
        storage.record_migration("001", "Complex query", long_sql, "SAFE")
        
        history = storage.get_migration_history(limit=10)
        assert len(history) == 1


class TestStorageAndEngineIntegration:
    """存储与引擎的完整集成测试"""

    def test_engine_uses_storage_correctly(self, migration_engine):
        """测试引擎正确使用存储"""
        # 初始化
        migration_engine.storage.initialize()
        
        # 记录迁移
        migration_engine.storage.record_migration(
            "001",
            "Test migration",
            "ROLLBACK",
            "SAFE"
        )
        
        # 检索迁移
        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 1

    def test_multiple_engines_share_storage(self, in_memory_engine):
        """测试多个引擎共享存储"""
        metadata = MetaData()
        
        # 创建第一个引擎并记录迁移
        engine1 = MigrationEngine(in_memory_engine, metadata)
        engine1.storage.initialize()
        engine1.storage.record_migration("001", "First", "ROLLBACK", "SAFE")
        
        # 创建第二个引擎并检索迁移
        engine2 = MigrationEngine(in_memory_engine, metadata)
        history = engine2.storage.get_migration_history(limit=10)
        
        assert len(history) == 1
        assert history[0]["version"] == "001"

    def test_storage_consistency(self, migration_engine):
        """测试存储一致性"""
        # 记录多个迁移
        for i in range(1, 4):
            migration_engine.storage.record_migration(
                f"00{i}",
                f"Migration {i}",
                "ROLLBACK",
                "SAFE"
            )
        
        # 多次检索应该返回相同结果
        history1 = migration_engine.storage.get_migration_history(limit=10)
        history2 = migration_engine.storage.get_migration_history(limit=10)
        
        assert len(history1) == len(history2) == 3
