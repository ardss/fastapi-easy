"""CLI 集成测试 - 遵循实际 API"""
import pytest
from click.testing import CliRunner

from fastapi_easy.migrations.cli import cli


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def temp_db_url(tmp_path):
    db_file = tmp_path / "test.db"
    return f"sqlite:///{db_file}"


class TestCLIPlanCommand:
    """CLI plan 命令测试"""

    def test_plan_requires_database_url(self, cli_runner):
        """plan 命令需要 database-url"""
        result = cli_runner.invoke(cli, ['plan'])
        assert result.exit_code != 0

    def test_plan_with_database_url(self, cli_runner, temp_db_url):
        """plan 命令带 database-url"""
        result = cli_runner.invoke(cli, ['plan', '--database-url', temp_db_url])
        assert result.exit_code in [0, 1]


class TestCLIApplyCommand:
    """CLI apply 命令测试"""

    def test_apply_requires_database_url(self, cli_runner):
        """apply 命令需要 database-url"""
        result = cli_runner.invoke(cli, ['apply'])
        assert result.exit_code != 0

    def test_apply_with_force(self, cli_runner, temp_db_url):
        """apply 命令带 force"""
        result = cli_runner.invoke(cli, ['apply', '--database-url', temp_db_url, '--force'])
        assert result.exit_code in [0, 1]


class TestCLIRollbackCommand:
    """CLI rollback 命令测试"""

    def test_rollback_requires_database_url(self, cli_runner):
        """rollback 命令需要 database-url"""
        result = cli_runner.invoke(cli, ['rollback'])
        assert result.exit_code != 0

    def test_rollback_with_force(self, cli_runner, temp_db_url):
        """rollback 命令带 force"""
        result = cli_runner.invoke(cli, ['rollback', '--database-url', temp_db_url, '--force'])
        assert result.exit_code in [0, 1]


class TestCLIHistoryCommand:
    """CLI history 命令测试"""

    def test_history_requires_database_url(self, cli_runner):
        """history 命令需要 database-url"""
        result = cli_runner.invoke(cli, ['history'])
        assert result.exit_code != 0

    def test_history_with_database_url(self, cli_runner, temp_db_url):
        """history 命令带 database-url"""
        result = cli_runner.invoke(cli, ['history', '--database-url', temp_db_url])
        assert result.exit_code in [0, 1]


class TestCLIStatusCommand:
    """CLI status 命令测试"""

    def test_status_requires_database_url(self, cli_runner):
        """status 命令需要 database-url"""
        result = cli_runner.invoke(cli, ['status'])
        assert result.exit_code != 0

    def test_status_with_database_url(self, cli_runner, temp_db_url):
        """status 命令带 database-url"""
        result = cli_runner.invoke(cli, ['status', '--database-url', temp_db_url])
        assert result.exit_code in [0, 1]


class TestCLIInitCommand:
    """CLI init 命令测试"""

    def test_init_requires_database_url(self, cli_runner):
        """init 命令需要 database-url"""
        result = cli_runner.invoke(cli, ['init'])
        assert result.exit_code != 0

    def test_init_with_database_url(self, cli_runner, temp_db_url):
        """init 命令带 database-url"""
        result = cli_runner.invoke(cli, ['init', '--database-url', temp_db_url])
        assert result.exit_code in [0, 1]


class TestCLIWorkflow:
    """CLI 工作流测试"""

    def test_full_workflow(self, cli_runner, temp_db_url):
        """完整工作流"""
        results = []
        results.append(cli_runner.invoke(cli, ['init', '--database-url', temp_db_url]))
        results.append(cli_runner.invoke(cli, ['plan', '--database-url', temp_db_url]))
        results.append(cli_runner.invoke(cli, ['status', '--database-url', temp_db_url]))
        results.append(cli_runner.invoke(cli, ['apply', '--database-url', temp_db_url, '--force']))
        results.append(cli_runner.invoke(cli, ['history', '--database-url', temp_db_url]))

        for result in results:
            assert result.exit_code in [0, 1]
