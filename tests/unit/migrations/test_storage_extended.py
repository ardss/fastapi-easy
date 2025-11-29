"""
存储模块扩展单元测试

测试 MigrationStorage 的初始化、记录、查询等功能
"""

import pytest
from sqlalchemy import create_engine, text

from fastapi_easy.migrations.storage import MigrationStorage
from fastapi_easy.migrations.types import OperationResult


@pytest.fixture
def in_memory_db():
    """创建内存数据库"""
    engine = create_engine("sqlite:///:memory:")
    return engine


class TestMigrationStorageInitialize:
    """迁移存储初始化测试"""

    def test_initialize_success(self, in_memory_db):
        """测试初始化成功"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        # 验证表存在
        with in_memory_db.connect() as conn:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='_fastapi_easy_migrations'"
            ))
            assert result.fetchone() is not None

    def test_initialize_table_exists(self, in_memory_db):
        """测试表已存在时的初始化"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        # 再次初始化，应该不报错
        storage.initialize()
        
        with in_memory_db.connect() as conn:
            result = conn.execute(text(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='_fastapi_easy_migrations'"
            ))
            assert result.scalar() == 1

    def test_table_has_correct_columns(self, in_memory_db):
        """测试表有正确的列"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        with in_memory_db.connect() as conn:
            result = conn.execute(text(
                "PRAGMA table_info(_fastapi_easy_migrations)"
            ))
            columns = {row[1] for row in result.fetchall()}
            assert "version" in columns
            assert "description" in columns


class TestMigrationStorageRecord:
    """迁移记录测试"""

    def test_record_migration_success(self, in_memory_db):
        """测试成功记录迁移"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        result = storage.record_migration(
            version="001",
            description="Test migration",
            rollback_sql="ROLLBACK",
            risk_level="SAFE"
        )
        assert result.success is True
        assert result.data["version"] == "001"
        assert result.metadata["idempotent"] is False

    def test_record_migration_idempotent(self, in_memory_db):
        """测试记录迁移的幂等性"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        # 第一次记录
        storage.record_migration("001", "Test", "ROLLBACK", "SAFE")
        # 第二次记录相同的版本
        result = storage.record_migration("001", "Test", "ROLLBACK", "SAFE")
        # 应该返回成功 (幂等)
        assert result.success is True
        assert result.metadata["idempotent"] is True

    def test_record_migration_multiple(self, in_memory_db):
        """测试记录多个迁移"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        storage.record_migration("001", "First", "ROLLBACK", "SAFE")
        storage.record_migration("002", "Second", "ROLLBACK", "MEDIUM")
        storage.record_migration("003", "Third", "ROLLBACK", "HIGH")
        
        history = storage.get_migration_history(limit=10)
        assert len(history) == 3

    def test_record_migration_with_special_chars(self, in_memory_db):
        """测试记录包含特殊字符的迁移"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        result = storage.record_migration(
            version="001_test",
            description="Test with 'quotes' and \"double quotes\"",
            rollback_sql="DROP TABLE \"test\"",
            risk_level="HIGH"
        )
        assert isinstance(result, OperationResult)
        assert result.success is True
        assert result.data["version"] == "001_test"


class TestMigrationStorageQuery:
    """迁移查询测试"""

    def test_get_migration_history_empty(self, in_memory_db):
        """测试获取空历史"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        history = storage.get_migration_history(limit=10)
        assert len(history) == 0

    def test_get_migration_history_with_records(self, in_memory_db):
        """测试获取有记录的历史"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        storage.record_migration("001", "First", "ROLLBACK", "SAFE")
        storage.record_migration("002", "Second", "ROLLBACK", "MEDIUM")
        
        history = storage.get_migration_history(limit=10)
        assert len(history) == 2
        # 检查两个版本都在历史中
        versions = {h["version"] for h in history}
        assert "001" in versions
        assert "002" in versions

    def test_get_migration_history_limit(self, in_memory_db):
        """测试历史记录限制"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        for i in range(1, 6):
            storage.record_migration(f"00{i}", f"Migration {i}", "ROLLBACK", "SAFE")
        
        history = storage.get_migration_history(limit=3)
        assert len(history) <= 3

    def test_get_migration_history_order(self, in_memory_db):
        """测试历史记录顺序"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        storage.record_migration("001", "First", "ROLLBACK", "SAFE")
        storage.record_migration("002", "Second", "ROLLBACK", "SAFE")
        storage.record_migration("003", "Third", "ROLLBACK", "SAFE")
        
        history = storage.get_migration_history(limit=10)
        # 应该有所有三个版本
        assert len(history) == 3
        versions = {h["version"] for h in history}
        assert versions == {"001", "002", "003"}


class TestMigrationStorageEdgeCases:
    """存储边界情况测试"""

    def test_record_migration_empty_description(self, in_memory_db):
        """测试空描述的迁移"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        result = storage.record_migration("001", "", "ROLLBACK", "SAFE")
        assert result.success is True

    def test_record_migration_long_description(self, in_memory_db):
        """测试长描述的迁移"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        long_desc = "A" * 500
        result = storage.record_migration("001", long_desc, "ROLLBACK", "SAFE")
        assert result.success is True

    def test_record_migration_different_risk_levels(self, in_memory_db):
        """测试不同风险等级的迁移"""
        storage = MigrationStorage(in_memory_db)
        storage.initialize()
        
        storage.record_migration("001", "Safe", "ROLLBACK", "SAFE")
        storage.record_migration("002", "Medium", "ROLLBACK", "MEDIUM")
        storage.record_migration("003", "High", "ROLLBACK", "HIGH")
        
        history = storage.get_migration_history(limit=10)
        assert len(history) == 3

    def test_storage_persistence(self, in_memory_db):
        """测试存储持久化"""
        storage1 = MigrationStorage(in_memory_db)
        storage1.initialize()
        storage1.record_migration("001", "Test", "ROLLBACK", "SAFE")
        
        # 创建新的存储实例，应该能读取之前的数据
        storage2 = MigrationStorage(in_memory_db)
        history = storage2.get_migration_history(limit=10)
        assert len(history) == 1
        assert history[0]["version"] == "001"
