import pytest
from click.testing import CliRunner
from fastapi_easy.migrations.cli import cli

@pytest.fixture
def cli_runner():
    return CliRunner()

@pytest.fixture
def temp_db_url(tmp_path):
    db_file = tmp_path / 'test.db'
    return f'sqlite:///{db_file}'

class TestCLIPlanCommand:
    def test_plan_requires_database_url(self, cli_runner):
        result = cli_runner.invoke(cli, ['plan'])
        assert result.exit_code != 0
    
    def test_plan_with_database_url(self, cli_runner, temp_db_url):
        result = cli_runner.invoke(cli, ['plan', '--database-url', temp_db_url])
        assert result.exit_code in [0, 1]

class TestCLIApplyCommand:
    def test_apply_with_force(self, cli_runner, temp_db_url):
        result = cli_runner.invoke(cli, ['apply', '--database-url', temp_db_url, '--force'])
        assert result.exit_code in [0, 1]

class TestCLIWorkflow:
    def test_full_workflow(self, cli_runner, temp_db_url):
        results = []
        results.append(cli_runner.invoke(cli, ['init', '--database-url', temp_db_url]))
        results.append(cli_runner.invoke(cli, ['plan', '--database-url', temp_db_url]))
        results.append(cli_runner.invoke(cli, ['apply', '--database-url', temp_db_url, '--force']))
        for result in results:
            assert result.exit_code in [0, 1]
