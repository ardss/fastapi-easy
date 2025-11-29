"""
CLI 辅助模块单元测试

测试 CLIErrorHandler, CLIFormatter, CLIConfirm, CLIProgress 等辅助类
"""

import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from fastapi_easy.migrations.cli_helpers import (
    CLIConfirm,
    CLIErrorHandler,
    CLIFormatter,
    CLIProgress,
)
from fastapi_easy.migrations.exceptions import MigrationError
from fastapi_easy.migrations.types import Migration, MigrationPlan, RiskLevel


class TestCLIErrorHandler:
    """CLI 错误处理器测试"""

    def test_handle_migration_error(self, capsys):
        """测试处理 MigrationError"""
        error = MigrationError("Test error", "Test suggestion")
        CLIErrorHandler.handle_error(error)
        captured = capsys.readouterr()
        assert "Test error" in captured.err
        assert "Test suggestion" in captured.err

    def test_handle_generic_error(self, capsys):
        """测试处理普通异常"""
        error = ValueError("Generic error")
        CLIErrorHandler.handle_error(error, "Context")
        captured = capsys.readouterr()
        assert "Context" in captured.err
        assert "Generic error" in captured.err

    def test_handle_error_without_context(self, capsys):
        """测试不带 context 的错误处理"""
        error = RuntimeError("Runtime error")
        CLIErrorHandler.handle_error(error)
        captured = capsys.readouterr()
        assert "Runtime error" in captured.err

    @patch('sys.exit')
    def test_exit_with_error(self, mock_exit, capsys):
        """测试带错误退出"""
        CLIErrorHandler.exit_with_error("Fatal error", 2)
        mock_exit.assert_called_once_with(2)
        captured = capsys.readouterr()
        assert "Fatal error" in captured.err

    @patch('sys.exit')
    def test_exit_with_default_code(self, mock_exit, capsys):
        """测试默认退出码"""
        CLIErrorHandler.exit_with_error("Error")
        mock_exit.assert_called_once_with(1)


class TestCLIFormatter:
    """CLI 格式化器测试"""

    def test_format_migration_safe(self):
        """测试格式化安全迁移"""
        migration = Migration(
            version="001",
            description="Add table",
            upgrade_sql="CREATE TABLE",
            downgrade_sql="DROP TABLE",
            risk_level=RiskLevel.SAFE,
        )
        result = CLIFormatter.format_migration(migration)
        assert "✅" in result
        assert "safe" in result.lower()
        assert "001" in result

    def test_format_migration_medium(self):
        """测试格式化中等风险迁移"""
        migration = Migration(
            version="002",
            description="Add column",
            upgrade_sql="ALTER TABLE",
            downgrade_sql="ALTER TABLE",
            risk_level=RiskLevel.MEDIUM,
        )
        result = CLIFormatter.format_migration(migration)
        assert "⚠️" in result
        assert "medium" in result.lower()

    def test_format_migration_high(self):
        """测试格式化高风险迁移"""
        migration = Migration(
            version="003",
            description="Drop column",
            upgrade_sql="ALTER TABLE",
            downgrade_sql="ALTER TABLE",
            risk_level=RiskLevel.HIGH,
        )
        result = CLIFormatter.format_migration(migration)
        assert "🔴" in result
        assert "high" in result.lower()

    def test_format_plan_empty(self):
        """测试格式化空计划"""
        plan = MigrationPlan(migrations=[], status="completed")
        result = CLIFormatter.format_plan(plan)
        assert "无待处理的迁移" in result or "0" in result

    def test_format_plan_with_migrations(self):
        """测试格式化有迁移的计划"""
        migration = Migration(
            version="001",
            description="Add table",
            upgrade_sql="CREATE TABLE",
            downgrade_sql="DROP TABLE",
            risk_level=RiskLevel.SAFE,
        )
        plan = MigrationPlan(migrations=[migration], status="completed")
        result = CLIFormatter.format_plan(plan)
        assert "001" in result
        assert "Add table" in result

    def test_format_plan_multiple_migrations(self):
        """测试格式化多个迁移"""
        migrations = [
            Migration(
                version="001",
                description="Add table",
                upgrade_sql="CREATE TABLE",
                downgrade_sql="DROP TABLE",
                risk_level=RiskLevel.SAFE,
            ),
            Migration(
                version="002",
                description="Add column",
                upgrade_sql="ALTER TABLE",
                downgrade_sql="ALTER TABLE",
                risk_level=RiskLevel.MEDIUM,
            ),
        ]
        plan = MigrationPlan(migrations=migrations, status="completed")
        result = CLIFormatter.format_plan(plan)
        assert "001" in result
        assert "002" in result


class TestCLIConfirm:
    """CLI 确认对话框测试"""

    @patch('click.confirm', return_value=True)
    def test_confirm_migration_yes(self, mock_confirm):
        """测试用户确认迁移"""
        plan = MigrationPlan(migrations=[], status="completed")
        result = CLIConfirm.confirm_migration(plan, force=False)
        assert result is True
        mock_confirm.assert_called_once()

    @patch('click.confirm', return_value=False)
    def test_confirm_migration_no(self, mock_confirm):
        """测试用户拒绝迁移"""
        plan = MigrationPlan(migrations=[], status="completed")
        result = CLIConfirm.confirm_migration(plan, force=False)
        assert result is False

    def test_confirm_migration_force(self):
        """测试强制迁移"""
        plan = MigrationPlan(migrations=[], status="completed")
        result = CLIConfirm.confirm_migration(plan, force=True)
        assert result is True

    @patch('click.confirm', return_value=True)
    def test_confirm_rollback_yes(self, mock_confirm):
        """测试用户确认回滚"""
        result = CLIConfirm.confirm_rollback(steps=2, force=False)
        assert result is True

    @patch('click.confirm', return_value=False)
    def test_confirm_rollback_no(self, mock_confirm):
        """测试用户拒绝回滚"""
        result = CLIConfirm.confirm_rollback(steps=2, force=False)
        assert result is False

    def test_confirm_rollback_force(self):
        """测试强制回滚"""
        result = CLIConfirm.confirm_rollback(steps=2, force=True)
        assert result is True

    @patch('click.confirm', return_value=True)
    def test_confirm_clear_cache_yes(self, mock_confirm):
        """测试用户确认清理缓存"""
        result = CLIConfirm.confirm_clear_cache(force=False)
        assert result is True

    @patch('click.confirm', return_value=False)
    def test_confirm_clear_cache_no(self, mock_confirm):
        """测试用户拒绝清理缓存"""
        result = CLIConfirm.confirm_clear_cache(force=False)
        assert result is False

    def test_confirm_clear_cache_force(self):
        """测试强制清理缓存"""
        result = CLIConfirm.confirm_clear_cache(force=True)
        assert result is True


class TestCLIProgress:
    """CLI 进度显示测试"""

    def test_show_step(self, capsys):
        """测试显示步骤"""
        CLIProgress.show_step(1, 3, "Connecting to database")
        captured = capsys.readouterr()
        assert "1" in captured.out or "Connecting" in captured.out

    def test_show_success(self, capsys):
        """测试显示成功消息"""
        CLIProgress.show_success("Migration completed")
        captured = capsys.readouterr()
        assert "Migration completed" in captured.out
        assert "✅" in captured.out or "success" in captured.out.lower()

    def test_show_warning(self, capsys):
        """测试显示警告消息"""
        CLIProgress.show_warning("This is a warning")
        captured = capsys.readouterr()
        assert "This is a warning" in captured.out
        assert "⚠️" in captured.out or "warning" in captured.out.lower()

    def test_show_info(self, capsys):
        """测试显示信息消息"""
        CLIProgress.show_info("This is info")
        captured = capsys.readouterr()
        assert "This is info" in captured.out



class TestCLIFormatterIntegration:
    """CLI 格式化器集成测试"""

    def test_format_history_empty(self):
        """测试格式化空历史"""
        result = CLIFormatter.format_history([])
        assert "无迁移历史" in result or "0" in result or "empty" in result.lower()

    def test_format_history_with_records(self):
        """测试格式化有记录的历史"""
        history = [
            {
                "version": "001",
                "description": "Initial migration",
                "executed_at": "2025-01-01 10:00:00",
            },
            {
                "version": "002",
                "description": "Add users table",
                "executed_at": "2025-01-01 10:05:00",
            },
        ]
        result = CLIFormatter.format_history(history)
        assert "001" in result
        assert "002" in result



class TestCLIHelpersCombined:
    """CLI 辅助类组合测试"""

    def test_error_handler_with_formatter(self, capsys):
        """测试错误处理器与格式化器的组合"""
        error = MigrationError("Migration failed", "Check database connection")
        CLIErrorHandler.handle_error(error)
        captured = capsys.readouterr()
        assert "Migration failed" in captured.err

    @patch('click.confirm', return_value=True)
    def test_confirm_then_progress(self, mock_confirm, capsys):
        """测试确认后显示进度"""
        plan = MigrationPlan(migrations=[], status="completed")
        result = CLIConfirm.confirm_migration(plan, force=False)
        assert result is True
        CLIProgress.show_step(1, 3, "Starting migration")
        captured = capsys.readouterr()
        assert "Starting migration" in captured.out or "1" in captured.out

    def test_format_and_display_migration(self, capsys):
        """测试格式化并显示迁移"""
        migration = Migration(
            version="001",
            description="Test migration",
            upgrade_sql="CREATE TABLE",
            downgrade_sql="DROP TABLE",
            risk_level=RiskLevel.SAFE,
        )
        formatted = CLIFormatter.format_migration(migration)
        assert "001" in formatted
        assert "Test migration" in formatted


class TestCLIHelpersEdgeCases:
    """CLI 辅助类边界情况测试"""

    def test_format_migration_with_special_characters(self):
        """测试格式化包含特殊字符的迁移"""
        migration = Migration(
            version="001",
            description="Add 'users' table with @index",
            upgrade_sql="CREATE TABLE",
            downgrade_sql="DROP TABLE",
            risk_level=RiskLevel.SAFE,
        )
        result = CLIFormatter.format_migration(migration)
        assert "001" in result

    def test_format_plan_with_long_description(self):
        """测试格式化长描述的计划"""
        migration = Migration(
            version="001",
            description="A" * 100,  # 很长的描述
            upgrade_sql="CREATE TABLE",
            downgrade_sql="DROP TABLE",
            risk_level=RiskLevel.SAFE,
        )
        plan = MigrationPlan(migrations=[migration], status="completed")
        result = CLIFormatter.format_plan(plan)
        assert "001" in result

    def test_error_handler_with_none_context(self, capsys):
        """测试处理 None context 的错误"""
        error = ValueError("Test error")
        CLIErrorHandler.handle_error(error, None)
        captured = capsys.readouterr()
        assert "Test error" in captured.err

    def test_confirm_with_empty_message(self):
        """测试空消息的确认"""
        with patch('click.confirm', return_value=True):
            plan = MigrationPlan(migrations=[], status="completed")
            result = CLIConfirm.confirm_migration(plan, force=False)
            assert result is True
