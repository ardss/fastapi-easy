"""Unit tests for CLI tools"""

import pytest
from click.testing import CliRunner
from fastapi_easy.cli import cli


class TestCLI:
    """Test CLI commands"""
    
    def test_version_command(self):
        """Test version command"""
        runner = CliRunner()
        result = runner.invoke(cli, ['version'])
        
        assert result.exit_code == 0
        assert 'FastAPI-Easy' in result.output or '0.1.0' in result.output
    
    def test_info_command(self):
        """Test info command"""
        runner = CliRunner()
        result = runner.invoke(cli, ['info'])
        
        assert result.exit_code == 0
        assert 'FastAPI-Easy' in result.output
    
    def test_status_command(self):
        """Test status command"""
        runner = CliRunner()
        result = runner.invoke(cli, ['status'])
        
        assert result.exit_code == 0
    
    def test_init_command_help(self):
        """Test init command help"""
        runner = CliRunner()
        result = runner.invoke(cli, ['init', '--help'])
        
        assert result.exit_code == 0
        assert 'init' in result.output.lower()
    
    def test_generate_command_help(self):
        """Test generate command help"""
        runner = CliRunner()
        result = runner.invoke(cli, ['generate', '--help'])
        
        assert result.exit_code == 0
        assert 'generate' in result.output.lower()
    
    def test_cli_help(self):
        """Test CLI help"""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'Commands' in result.output or 'commands' in result.output.lower()
