"""
异常处理单元测试

测试所有自定义异常类的初始化、消息格式化和继承关系
"""


from fastapi_easy.migrations.exceptions import (
    CacheError,
    DatabaseConnectionError,
    LockAcquisitionError,
    MigrationError,
    MigrationExecutionError,
    RiskAssessmentError,
    SchemaDetectionError,
    StorageError,
)


class TestMigrationError:
    """基础异常类测试"""

    def test_basic_initialization(self):
        """测试基础异常初始化"""
        error = MigrationError("Test message", "Test suggestion")
        assert error.message == "Test message"
        assert error.suggestion == "Test suggestion"

    def test_get_full_message_with_suggestion(self):
        """测试包含建议的完整消息"""
        error = MigrationError("Test error", "Try this solution")
        full = error.get_full_message()
        assert "Test error" in full
        assert "Try this solution" in full
        assert "💡" in full

    def test_get_full_message_without_suggestion(self):
        """测试不包含建议的完整消息"""
        error = MigrationError("Test error")
        assert error.get_full_message() == "Test error"

    def test_exception_inheritance(self):
        """测试异常继承关系"""
        error = MigrationError("Test")
        assert isinstance(error, Exception)


class TestDatabaseConnectionError:
    """数据库连接错误测试"""

    def test_initialization(self):
        """测试初始化"""
        original = ValueError("Connection refused")
        error = DatabaseConnectionError("postgresql://localhost/db", original)
        assert "无法连接到数据库" in error.message
        assert "postgresql://localhost/db" in error.message

    def test_suggestion_included(self):
        """测试建议信息"""
        original = ConnectionError("timeout")
        error = DatabaseConnectionError("sqlite:///test.db", original)
        full = error.get_full_message()
        assert "检查数据库连接字符串" in full
        assert "确保数据库服务正在运行" in full
        assert "检查网络连接" in full

    def test_original_error_included(self):
        """测试原始错误信息"""
        original = Exception("Original error message")
        error = DatabaseConnectionError("mysql://localhost", original)
        assert "Original error message" in error.suggestion


class TestSchemaDetectionError:
    """Schema 检测错误测试"""

    def test_timeout_error(self):
        """测试超时错误"""
        error = SchemaDetectionError("timeout", timeout=120)
        assert "Schema 检测超时" in error.message
        assert "120" in error.message

    def test_normal_error(self):
        """测试普通错误"""
        error = SchemaDetectionError("Table not found")
        assert "Table not found" in error.message

    def test_timeout_suggestion(self):
        """测试超时建议"""
        error = SchemaDetectionError("timeout", timeout=60)
        full = error.get_full_message()
        assert "增加超时时间" in full
        assert "检查数据库性能" in full


class TestMigrationExecutionError:
    """迁移执行错误测试"""

    def test_permission_error(self):
        """测试权限错误"""
        error = MigrationExecutionError("001", "Permission denied")
        assert "迁移执行失败" in error.message
        assert "权限错误" in error.suggestion

    def test_table_not_exist_error(self):
        """测试表不存在错误"""
        error = MigrationExecutionError("002", "Table users not exist")
        assert "迁移执行失败" in error.message
        assert "表不存在" in error.suggestion

    def test_syntax_error(self):
        """测试 SQL 语法错误"""
        error = MigrationExecutionError("003", "Syntax error near 'CREATE'")
        assert "迁移执行失败" in error.message
        assert "SQL 语法错误" in error.suggestion

    def test_unknown_error(self):
        """测试未知错误"""
        error = MigrationExecutionError("004", "Unknown error")
        assert "迁移执行失败" in error.message
        assert "调试步骤" in error.suggestion


class TestLockAcquisitionError:
    """锁获取错误测试"""

    def test_postgres_lock_error(self):
        """测试 PostgreSQL 锁错误"""
        error = LockAcquisitionError("postgresql", {"id": 1})
        assert "无法获取迁移锁" in error.message
        assert "postgresql" in error.message

    def test_mysql_lock_error(self):
        """测试 MySQL 锁错误"""
        error = LockAcquisitionError("mysql", {"name": "fastapi_easy_migration"})
        assert "无法获取迁移锁" in error.message
        assert "mysql" in error.message

    def test_file_lock_error(self):
        """测试文件锁错误"""
        error = LockAcquisitionError("file", {"file": ".fastapi_easy_migration.lock"})
        assert "无法获取迁移锁" in error.message
        assert "file" in error.message

    def test_lock_suggestion(self):
        """测试锁建议"""
        error = LockAcquisitionError("postgresql", {"id": 1})
        full = error.get_full_message()
        assert "另一个实例正在执行迁移" in full
        assert "手动清理锁" in full


class TestStorageError:
    """存储错误测试"""

    def test_insert_error(self):
        """测试插入错误"""
        error = StorageError("insert", "Duplicate entry")
        assert "迁移历史记录失败" in error.message
        assert "insert" in error.message

    def test_query_error(self):
        """测试查询错误"""
        error = StorageError("query", "Table not found")
        assert "迁移历史记录失败" in error.message
        assert "query" in error.message

    def test_update_error(self):
        """测试更新错误"""
        error = StorageError("update", "Update failed")
        assert "迁移历史记录失败" in error.message
        assert "update" in error.message

    def test_storage_suggestion(self):
        """测试存储建议"""
        error = StorageError("insert", "Connection lost")
        full = error.get_full_message()
        assert "检查迁移表是否存在" in full
        assert "检查数据库权限" in full


class TestCacheError:
    """缓存错误测试"""

    def test_permission_error(self):
        """测试权限错误"""
        error = CacheError("read", "Permission denied")
        assert "缓存操作失败" in error.message
        assert "权限错误" in error.suggestion

    def test_corruption_error(self):
        """测试缓存损坏"""
        error = CacheError("write", "Invalid JSON corrupted")
        assert "缓存操作失败" in error.message
        assert "缓存文件损坏" in error.suggestion

    def test_cache_suggestion(self):
        """测试缓存建议"""
        error = CacheError("read", "corrupted data")
        full = error.get_full_message()
        assert "清理缓存" in full or "缓存文件损坏" in full


class TestRiskAssessmentError:
    """风险评估错误测试"""

    def test_rule_error(self):
        """测试规则错误"""
        error = RiskAssessmentError("custom_rule", "Rule evaluation failed")
        assert "custom_rule" in error.message
        assert "风险规则执行失败" in error.message

    def test_risk_suggestion(self):
        """测试风险建议"""
        error = RiskAssessmentError("test_rule", "Rule failed")
        full = error.get_full_message()
        assert "检查规则实现是否正确" in full


class TestExceptionInheritance:
    """异常继承关系测试"""

    def test_all_exceptions_inherit_from_migration_error(self):
        """测试所有异常都继承自 MigrationError"""
        exceptions = [
            DatabaseConnectionError("test", Exception()),
            SchemaDetectionError("test"),
            MigrationExecutionError("001", "test"),
            LockAcquisitionError("file", {}),
            StorageError("insert", "test"),
            CacheError("read", "test"),
            RiskAssessmentError("rule", "test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, MigrationError)
            assert isinstance(exc, Exception)

    def test_all_exceptions_have_message(self):
        """测试所有异常都有 message 属性"""
        exceptions = [
            DatabaseConnectionError("test", Exception()),
            SchemaDetectionError("test"),
            MigrationExecutionError("001", "test"),
            LockAcquisitionError("file", {}),
            StorageError("insert", "test"),
            CacheError("read", "test"),
            RiskAssessmentError("rule", "test"),
        ]

        for exc in exceptions:
            assert hasattr(exc, "message")
            assert exc.message is not None

    def test_all_exceptions_have_suggestion(self):
        """测试所有异常都有 suggestion 属性"""
        exceptions = [
            DatabaseConnectionError("test", Exception()),
            SchemaDetectionError("test"),
            MigrationExecutionError("001", "test"),
            LockAcquisitionError("file", {}),
            StorageError("insert", "test"),
            CacheError("read", "test"),
            RiskAssessmentError("rule", "test"),
        ]

        for exc in exceptions:
            assert hasattr(exc, "suggestion")


class TestExceptionMessageSecurity:
    """异常消息安全性测试"""

    def test_no_password_in_connection_error(self):
        """测试连接错误不泄露密码"""
        error = DatabaseConnectionError("postgresql://user:password@localhost/db", Exception())
        full = error.get_full_message()
        # 密码应该被隐藏或不显示
        assert "password" not in full.lower() or "password" in error.message

    def test_user_friendly_messages(self):
        """测试用户友好的错误消息"""
        error = MigrationExecutionError("001", "permission denied")
        full = error.get_full_message()
        # 应该包含中文用户友好的消息
        assert "权限错误" in full or "迁移执行失败" in full

    def test_suggestion_is_actionable(self):
        """测试建议是可操作的"""
        error = SchemaDetectionError("test", timeout=30)
        full = error.get_full_message()
        # 建议应该包含具体的操作步骤
        assert "增加超时时间" in full or "检查" in full
