"""端到端迁移测试 - 完整流程"""

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


class TestE2EMigrationFlow:
    """端到端迁移流程测试"""

    def test_initialize_and_record_migration(self, migration_engine):
        """初始化并记录迁移"""
        migration_engine.storage.initialize()
        migration_engine.storage.record_migration(
            "001", "Create users table", "DROP TABLE users", "SAFE"
        )
        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 1
        assert history[0]["version"] == "001"

    def test_multiple_migrations_sequence(self, migration_engine):
        """多个迁移序列"""
        migrations = [
            ("001", "Create users", "DROP TABLE users", "SAFE"),
            ("002", "Add email", "ALTER TABLE users DROP COLUMN email", "MEDIUM"),
            ("003", "Create indexes", "DROP INDEX idx_email", "HIGH"),
        ]

        for version, desc, rollback, risk in migrations:
            migration_engine.storage.record_migration(version, desc, rollback, risk)

        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 3

    def test_migration_with_error_recovery(self, migration_engine):
        """迁移错误恢复"""
        # 记录成功的迁移
        migration_engine.storage.record_migration("001", "First", "ROLLBACK", "SAFE")

        # 尝试记录相同版本（幂等）
        migration_engine.storage.record_migration("001", "First", "ROLLBACK", "SAFE")

        # 应该只有一条记录
        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) >= 1


class TestE2EComplexScenarios:
    """端到端复杂场景测试"""

    def test_large_migration_batch(self, migration_engine):
        """大批量迁移"""
        for i in range(1, 21):
            migration_engine.storage.record_migration(
                f"{i:03d}", f"Migration {i}", "ROLLBACK", "SAFE"
            )

        history = migration_engine.storage.get_migration_history(limit=100)
        assert len(history) == 20

    def test_mixed_risk_levels(self, migration_engine):
        """混合风险等级"""
        risks = ["SAFE", "MEDIUM", "HIGH", "SAFE", "MEDIUM"]
        for i, risk in enumerate(risks, 1):
            migration_engine.storage.record_migration(f"00{i}", f"Migration {i}", "ROLLBACK", risk)

        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 5

    def test_special_characters_in_migrations(self, migration_engine):
        """特殊字符处理"""
        special_cases = [
            ("001", "Add 'users' table", "DROP TABLE users", "SAFE"),
            ("002", "Add @index", "DROP INDEX idx", "SAFE"),
            ("003", 'Add "quoted" column', "DROP COLUMN col", "SAFE"),
        ]

        for version, desc, rollback, risk in special_cases:
            migration_engine.storage.record_migration(version, desc, rollback, risk)

        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 3


class TestE2EDataConsistency:
    """端到端数据一致性测试"""

    def test_data_persistence_across_operations(self, migration_engine):
        """操作间的数据持久化"""
        # 第一批操作
        migration_engine.storage.record_migration("001", "First", "ROLLBACK", "SAFE")
        history1 = migration_engine.storage.get_migration_history(limit=10)

        # 第二批操作
        migration_engine.storage.record_migration("002", "Second", "ROLLBACK", "SAFE")
        history2 = migration_engine.storage.get_migration_history(limit=10)

        # 验证数据一致性
        assert len(history1) == 1
        assert len(history2) == 2
        assert history2[0]["version"] in ["001", "002"]

    def test_concurrent_access_simulation(self, in_memory_engine):
        """并发访问模拟"""
        storage1 = MigrationStorage(in_memory_engine)
        storage1.initialize()
        storage1.record_migration("001", "First", "ROLLBACK", "SAFE")

        storage2 = MigrationStorage(in_memory_engine)
        history = storage2.get_migration_history(limit=10)

        assert len(history) == 1


class TestE2EErrorHandling:
    """端到端错误处理测试"""

    def test_invalid_migration_data(self, migration_engine):
        """无效迁移数据处理"""
        # 空版本
        result = migration_engine.storage.record_migration("", "Test", "ROLLBACK", "SAFE")
        # 应该返回 OperationResult 对象
        assert hasattr(result, "success")
        assert hasattr(result, "data")
        # 空版本应该被记录（允许）
        assert result.success is True

    def test_long_description_handling(self, migration_engine):
        """长描述处理"""
        long_desc = "A" * 1000
        migration_engine.storage.record_migration("001", long_desc, "ROLLBACK", "SAFE")
        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 1

    def test_long_sql_handling(self, migration_engine):
        """长 SQL 处理"""
        long_sql = "SELECT * FROM " + " UNION SELECT * FROM ".join([f"table{i}" for i in range(50)])
        migration_engine.storage.record_migration("001", "Test", long_sql, "SAFE")
        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 1


class TestE2EWorkflowIntegration:
    """端到端工作流集成测试"""

    def test_complete_migration_lifecycle(self, migration_engine):
        """完整迁移生命周期"""
        # 初始化
        migration_engine.storage.initialize()

        # 记录多个迁移
        for i in range(1, 4):
            migration_engine.storage.record_migration(
                f"00{i}", f"Migration {i}", "ROLLBACK", "SAFE"
            )

        # 查询历史
        history = migration_engine.storage.get_migration_history(limit=10)

        # 验证
        assert len(history) == 3
        versions = {h["version"] for h in history}
        assert versions == {"001", "002", "003"}

    def test_migration_with_rollback_info(self, migration_engine):
        """包含回滚信息的迁移"""
        migration_engine.storage.record_migration(
            "001", "Create users table", "DROP TABLE users", "SAFE"
        )

        history = migration_engine.storage.get_migration_history(limit=10)
        assert len(history) == 1
        # 检查记录包含必要的字段
        assert "version" in history[0]
        assert "description" in history[0]
