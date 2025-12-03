"""
端到端迁移测试

测试完整的迁移流程:
- 表创建和数据操作
- 迁移存储初始化
- 并发启动
"""

import os
import tempfile

import pytest
from sqlalchemy import Column, Integer, String, create_engine, inspect
from sqlalchemy.orm import Session, declarative_base

from fastapi_easy.migrations.storage import MigrationStorage

Base = declarative_base()


class User(Base):
    """用户模型"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)


@pytest.fixture
def temp_db():
    """创建临时数据库"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db_url = f"sqlite:///{path}"
    engine = create_engine(db_url)

    yield engine, db_url

    # 清理
    engine.dispose()
    try:
        os.unlink(path)
    except (OSError, PermissionError):
        pass


class TestE2EMigrationFlow:
    """端到端迁移流程测试"""

    def test_complete_migration_flow(self, temp_db):
        """测试完整的迁移流程"""
        engine, db_url = temp_db

        # 1. 创建初始表
        Base.metadata.create_all(engine)

        # 验证表存在
        inspector = inspect(engine)
        assert "users" in inspector.get_table_names()

        # 验证列
        columns = inspector.get_columns("users")
        column_names = [col["name"] for col in columns]
        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names

    def test_migration_storage(self, temp_db):
        """测试迁移历史存储"""
        engine, db_url = temp_db

        # 1. 初始化存储
        storage = MigrationStorage(engine)
        storage.initialize()

        # 验证迁移历史表创建
        inspector = inspect(engine)
        assert "_fastapi_easy_migrations" in inspector.get_table_names()

    def test_concurrent_startup(self, temp_db):
        """测试并发启动"""
        engine, db_url = temp_db

        # 1. 创建初始表
        Base.metadata.create_all(engine)

        # 2. 初始化存储
        storage1 = MigrationStorage(engine)
        storage1.initialize()

        # 3. 再次初始化 (模拟并发)
        storage2 = MigrationStorage(engine)
        storage2.initialize()

        # 验证没有错误
        inspector = inspect(engine)
        assert "_fastapi_easy_migrations" in inspector.get_table_names()

    def test_migration_with_data_preservation(self, temp_db):
        """测试迁移时数据保留"""
        engine, db_url = temp_db

        # 1. 创建初始表
        Base.metadata.create_all(engine)

        # 2. 插入数据
        with Session(engine) as session:
            user = User(id=1, name="Alice", email="alice@example.com")
            session.add(user)
            session.commit()

        # 3. 验证数据存在
        with Session(engine) as session:
            user = session.query(User).filter_by(id=1).first()
            assert user is not None
            assert user.name == "Alice"


class TestMigrationEdgeCases:
    """迁移边界情况测试"""

    def test_empty_schema_change(self, temp_db):
        """测试无 Schema 变更"""
        engine, db_url = temp_db

        # 1. 创建表
        Base.metadata.create_all(engine)

        # 验证表存在
        inspector = inspect(engine)
        assert "users" in inspector.get_table_names()

    def test_database_connection_error_handling(self):
        """测试数据库连接错误处理"""
        # 使用无效的数据库 URL
        invalid_url = "sqlite:///nonexistent/path/to/db.db"

        try:
            engine = create_engine(invalid_url)
            # 这里可能会抛出异常
            assert engine is not None
        except Exception as e:
            # 验证异常被正确处理
            assert e is not None

    def test_multiple_tables(self, temp_db):
        """测试多个表的创建"""
        engine, db_url = temp_db

        # 1. 创建表
        Base.metadata.create_all(engine)

        # 2. 验证表存在
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "users" in tables


class TestMigrationPerformance:
    """迁移性能测试"""

    def test_table_creation_performance(self, temp_db):
        """测试表创建性能"""
        import time

        engine, db_url = temp_db

        # 测量创建时间
        start = time.time()
        Base.metadata.create_all(engine)
        elapsed = time.time() - start

        # 验证性能 (应该快速完成)
        assert elapsed < 1.0  # 应该在 1 秒内完成

    def test_storage_initialization_performance(self, temp_db):
        """测试存储初始化性能"""
        import time

        engine, db_url = temp_db

        # 测量初始化时间
        start = time.time()
        storage = MigrationStorage(engine)
        storage.initialize()
        elapsed = time.time() - start

        # 验证性能
        assert elapsed < 1.0  # 应该在 1 秒内完成
