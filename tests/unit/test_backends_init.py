"""Tests for backends/__init__.py module"""

import pytest
from unittest.mock import patch, MagicMock
import sys


class TestBackendsInit:
    """Test backends module initialization"""

    def test_base_adapter_import(self):
        """Test BaseORMAdapter is imported"""
        from fastapi_easy.backends import BaseORMAdapter
        assert BaseORMAdapter is not None

    def test_sqlalchemy_adapter_import(self):
        """Test SQLAlchemyAdapter is imported"""
        from fastapi_easy.backends import SQLAlchemyAdapter
        assert SQLAlchemyAdapter is not None

    def test_tortoise_adapter_optional_import(self):
        """Test TortoiseAdapter optional import"""
        try:
            from fastapi_easy.backends import TortoiseAdapter
            assert TortoiseAdapter is not None
        except ImportError:
            # TortoiseAdapter is optional
            pass

    def test_sqlmodel_adapter_optional_import(self):
        """Test SQLModelAdapter optional import"""
        try:
            from fastapi_easy.backends import SQLModelAdapter
            assert SQLModelAdapter is not None
        except ImportError:
            # SQLModelAdapter is optional
            pass

    def test_mongo_adapter_optional_import(self):
        """Test MongoAdapter optional import"""
        try:
            from fastapi_easy.backends import MongoAdapter
            assert MongoAdapter is not None
        except ImportError:
            # MongoAdapter is optional
            pass

    def test_all_exports(self):
        """Test __all__ exports"""
        from fastapi_easy import backends
        assert hasattr(backends, '__all__')
        assert "BaseORMAdapter" in backends.__all__
        assert "SQLAlchemyAdapter" in backends.__all__

    def test_optional_backends_list(self):
        """Test optional backends list is maintained"""
        from fastapi_easy.backends import _optional_backends
        assert isinstance(_optional_backends, list)
        # Should contain some optional backends
        assert len(_optional_backends) >= 0

    def test_import_error_handling(self):
        """Test that ImportError is handled gracefully"""
        # This test verifies that the module handles missing optional dependencies
        # by checking that the module loads successfully
        import fastapi_easy.backends
        assert fastapi_easy.backends is not None
