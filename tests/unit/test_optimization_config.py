"""Tests for optimization configuration"""

import pytest
import json
import tempfile
from pathlib import Path
from fastapi_easy.core.optimization_config import OptimizationConfig, create_optimization_config


class TestOptimizationConfig:
    """Test OptimizationConfig class"""

    def test_default_config(self):
        """Test default configuration"""
        config = OptimizationConfig()

        assert config.enable_cache is True
        assert config.enable_async is True
        assert config.l1_size == 1000
        assert config.l1_ttl == 60
        assert config.l2_size == 10000
        assert config.l2_ttl == 600

    def test_custom_config(self):
        """Test custom configuration"""
        config = OptimizationConfig(
            enable_cache=False,
            l1_size=500,
            l1_ttl=30,
        )

        assert config.enable_cache is False
        assert config.l1_size == 500
        assert config.l1_ttl == 30

    def test_to_dict(self):
        """Test converting to dictionary"""
        config = OptimizationConfig(l1_size=500)
        config_dict = config.to_dict()

        assert config_dict["l1_size"] == 500
        assert config_dict["enable_cache"] is True

    def test_to_json(self):
        """Test converting to JSON"""
        config = OptimizationConfig(l1_size=500)
        json_str = config.to_json()

        parsed = json.loads(json_str)
        assert parsed["l1_size"] == 500

    def test_save_and_load_from_file(self):
        """Test saving and loading from file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            # Save config
            config = OptimizationConfig(l1_size=500, l2_size=5000)
            config.save_to_file(str(config_path))

            # Load config
            loaded_config = OptimizationConfig.from_file(str(config_path))

            assert loaded_config.l1_size == 500
            assert loaded_config.l2_size == 5000

    def test_from_file_not_found(self):
        """Test loading from non-existent file"""
        with pytest.raises(FileNotFoundError):
            OptimizationConfig.from_file("/nonexistent/path.json")

    def test_from_env(self, monkeypatch):
        """Test loading from environment variables"""
        monkeypatch.setenv("FASTAPI_EASY_L1_SIZE", "500")
        monkeypatch.setenv("FASTAPI_EASY_L1_TTL", "30")
        monkeypatch.setenv("FASTAPI_EASY_ENABLE_CACHE", "false")

        config = OptimizationConfig.from_env()

        assert config.l1_size == 500
        assert config.l1_ttl == 30
        assert config.enable_cache is False

    def test_from_env_defaults(self, monkeypatch):
        """Test from_env with default values"""
        # Clear any existing env vars
        monkeypatch.delenv("FASTAPI_EASY_L1_SIZE", raising=False)

        config = OptimizationConfig.from_env()

        assert config.l1_size == 1000  # Default value


class TestFactoryFunction:
    """Test factory function"""

    def test_create_optimization_config(self):
        """Test creating optimization config"""
        config = create_optimization_config(
            enable_cache=False,
            l1_size=500,
        )

        assert isinstance(config, OptimizationConfig)
        assert config.enable_cache is False
        assert config.l1_size == 500
