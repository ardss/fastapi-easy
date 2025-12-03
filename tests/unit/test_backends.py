"""Unit tests for ORM backends"""

import pytest
from unittest.mock import MagicMock
from fastapi_easy.backends.base import BaseORMAdapter


class TestBaseORMAdapter:
    """Test BaseORMAdapter"""

    def test_adapter_initialization(self):
        """Test adapter initialization"""
        model = MagicMock()
        session_factory = MagicMock()
        adapter = BaseORMAdapter(model, session_factory)

        assert adapter.model == model
        assert adapter.session_factory == session_factory

    @pytest.mark.asyncio
    async def test_get_all_not_implemented(self):
        """Test get_all not implemented"""
        model = MagicMock()
        session_factory = MagicMock()
        adapter = BaseORMAdapter(model, session_factory)

        with pytest.raises(NotImplementedError):
            await adapter.get_all({}, {}, {})

    @pytest.mark.asyncio
    async def test_get_one_not_implemented(self):
        """Test get_one not implemented"""
        model = MagicMock()
        session_factory = MagicMock()
        adapter = BaseORMAdapter(model, session_factory)

        with pytest.raises(NotImplementedError):
            await adapter.get_one(1)

    @pytest.mark.asyncio
    async def test_create_not_implemented(self):
        """Test create not implemented"""
        model = MagicMock()
        session_factory = MagicMock()
        adapter = BaseORMAdapter(model, session_factory)

        with pytest.raises(NotImplementedError):
            await adapter.create({})

    @pytest.mark.asyncio
    async def test_update_not_implemented(self):
        """Test update not implemented"""
        model = MagicMock()
        session_factory = MagicMock()
        adapter = BaseORMAdapter(model, session_factory)

        with pytest.raises(NotImplementedError):
            await adapter.update(1, {})

    @pytest.mark.asyncio
    async def test_delete_one_not_implemented(self):
        """Test delete_one not implemented"""
        model = MagicMock()
        session_factory = MagicMock()
        adapter = BaseORMAdapter(model, session_factory)

        with pytest.raises(NotImplementedError):
            await adapter.delete_one(1)

    @pytest.mark.asyncio
    async def test_delete_all_not_implemented(self):
        """Test delete_all not implemented"""
        model = MagicMock()
        session_factory = MagicMock()
        adapter = BaseORMAdapter(model, session_factory)

        with pytest.raises(NotImplementedError):
            await adapter.delete_all()

    @pytest.mark.asyncio
    async def test_count_not_implemented(self):
        """Test count not implemented"""
        model = MagicMock()
        session_factory = MagicMock()
        adapter = BaseORMAdapter(model, session_factory)

        with pytest.raises(NotImplementedError):
            await adapter.count({})
