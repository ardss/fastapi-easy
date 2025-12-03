"""SQLite 外键和磁盘空间测试"""
import pytest
from sqlalchemy import MetaData, create_engine

from fastapi_easy.migrations.disk_space_checker import DiskSpaceChecker
from fastapi_easy.migrations.sqlite_fk_handler import SQLiteForeignKeyHandler


@pytest.fixture
def sqlite_engine():
    return create_engine("sqlite:///:memory:")


class TestSQLiteForeignKeyHandler:
    """SQLite 外键处理测试"""

    def test_disable_foreign_keys(self, sqlite_engine):
        """测试禁用外键"""
        handler = SQLiteForeignKeyHandler(sqlite_engine)
        result = handler.disable_foreign_keys()
        assert result is True

    def test_enable_foreign_keys(self, sqlite_engine):
        """测试启用外键"""
        handler = SQLiteForeignKeyHandler(sqlite_engine)
        handler.disable_foreign_keys()
        result = handler.enable_foreign_keys()
        assert result is True

    def test_get_foreign_keys(self, sqlite_engine):
        """测试获取外键"""
        from sqlalchemy import text
        handler = SQLiteForeignKeyHandler(sqlite_engine)
        # 创建一个表
        with sqlite_engine.begin() as conn:
            conn.execute(text("CREATE TABLE test (id INTEGER PRIMARY KEY)"))

        fks = handler.get_foreign_keys("test")
        assert isinstance(fks, list)

    def test_check_foreign_key_integrity(self, sqlite_engine):
        """测试外键完整性检查"""
        handler = SQLiteForeignKeyHandler(sqlite_engine)
        result = handler.check_foreign_key_integrity()
        assert isinstance(result, bool)


class TestDiskSpaceChecker:
    """磁盘空间检查测试"""

    def test_get_database_size(self, sqlite_engine):
        """测试获取数据库大小"""
        checker = DiskSpaceChecker(sqlite_engine)
        size = checker.get_database_size()
        assert isinstance(size, int)
        assert size >= 0

    def test_estimate_copy_swap_space(self, sqlite_engine):
        """测试估算 Copy-Swap 空间"""
        checker = DiskSpaceChecker(sqlite_engine)
        space = checker.estimate_copy_swap_space()
        assert isinstance(space, int)
        assert space >= 0

    def test_get_available_space(self, sqlite_engine):
        """测试获取可用空间"""
        checker = DiskSpaceChecker(sqlite_engine)
        space = checker.get_available_space()
        assert isinstance(space, int)
        assert space > 0

    def test_check_space_available(self, sqlite_engine):
        """测试空间可用性检查"""
        checker = DiskSpaceChecker(sqlite_engine)
        result = checker.check_space_available()
        assert isinstance(result, bool)

    def test_get_space_info(self, sqlite_engine):
        """测试获取空间信息"""
        checker = DiskSpaceChecker(sqlite_engine)
        info = checker.get_space_info()
        assert isinstance(info, dict)
        assert "database_size_mb" in info
        assert "estimated_required_mb" in info
        assert "available_mb" in info
        assert "min_free_mb" in info

    def test_custom_min_free_space(self, sqlite_engine):
        """测试自定义最小保留空间"""
        checker = DiskSpaceChecker(sqlite_engine, min_free_space_mb=500)
        assert checker.min_free_space_mb == 500
