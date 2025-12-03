"""Tortoise ORM error handling tests"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi_easy.backends.tortoise import TortoiseAdapter
from fastapi_easy.core.errors import AppError, ConflictError, ErrorCode


@pytest.mark.asyncio
class TestTortoiseErrorHandling:
    """Test Tortoise ORM error handling"""

    async def test_get_all_database_error(self, tortoise_adapter):
        """Test get_all with database error"""
        with patch.object(tortoise_adapter.model, 'all') as mock_all:
            mock_all.side_effect = Exception("Database connection error")

            with pytest.raises(AppError) as exc_info:
                await tortoise_adapter.get_all({}, {}, {})

            assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
            assert exc_info.value.status_code == 500

    async def test_get_one_database_error(self, tortoise_adapter):
        """Test get_one with database error"""
        with patch.object(tortoise_adapter.model, 'get_or_none') as mock_get:
            mock_get.side_effect = Exception("Database connection error")

            with pytest.raises(AppError) as exc_info:
                await tortoise_adapter.get_one(1)

            assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
            assert exc_info.value.status_code == 500

    async def test_create_database_error(self, tortoise_adapter):
        """Test create with database error"""
        with patch.object(tortoise_adapter.model, 'create') as mock_create:
            mock_create.side_effect = Exception("Database connection error")

            with pytest.raises(AppError) as exc_info:
                await tortoise_adapter.create({"name": "test"})

            assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
            assert exc_info.value.status_code == 500

    async def test_update_database_error(self, tortoise_adapter):
        """Test update with database error"""
        with patch.object(tortoise_adapter.model, 'get_or_none') as mock_get:
            mock_get.side_effect = Exception("Database connection error")

            with pytest.raises(AppError) as exc_info:
                await tortoise_adapter.update(1, {"name": "test"})

            assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
            assert exc_info.value.status_code == 500

    async def test_delete_one_database_error(self, tortoise_adapter):
        """Test delete_one with database error"""
        with patch.object(tortoise_adapter.model, 'get_or_none') as mock_get:
            mock_get.side_effect = Exception("Database connection error")

            with pytest.raises(AppError) as exc_info:
                await tortoise_adapter.delete_one(1)

            assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
            assert exc_info.value.status_code == 500

    async def test_delete_all_database_error(self, tortoise_adapter):
        """Test delete_all with database error"""
        with patch.object(tortoise_adapter.model, 'all') as mock_all:
            mock_all.side_effect = Exception("Database connection error")

            with pytest.raises(AppError) as exc_info:
                await tortoise_adapter.delete_all()

            assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
            assert exc_info.value.status_code == 500

    async def test_count_database_error(self, tortoise_adapter):
        """Test count with database error"""
        with patch.object(tortoise_adapter.model, 'all') as mock_all:
            mock_all.side_effect = Exception("Database connection error")

            with pytest.raises(AppError) as exc_info:
                await tortoise_adapter.count({})

            assert exc_info.value.code == ErrorCode.INTERNAL_ERROR
            assert exc_info.value.status_code == 500


@pytest.mark.asyncio
class TestTortoiseFilterValidation:
    """Test Tortoise ORM filter validation"""

    async def test_filter_invalid_field_name(self, tortoise_adapter):
        """Test filter with invalid field name"""
        filters = {
            "invalid": {"field": None, "operator": "exact", "value": "test"}
        }

        with pytest.raises(AppError) as exc_info:
            await tortoise_adapter.get_all(filters, {}, {})

        assert "Invalid field name" in str(exc_info.value)

    async def test_filter_invalid_operator(self, tortoise_adapter):
        """Test filter with invalid operator"""
        filters = {
            "test": {"field": "name", "operator": "invalid_op", "value": "test"}
        }

        with pytest.raises(AppError) as exc_info:
            await tortoise_adapter.get_all(filters, {}, {})

        assert "Unsupported operator" in str(exc_info.value)

    async def test_filter_none_value(self, tortoise_adapter):
        """Test filter with None value"""
        filters = {
            "test": {"field": "name", "operator": "exact", "value": None}
        }

        with pytest.raises(AppError) as exc_info:
            await tortoise_adapter.get_all(filters, {}, {})

        assert "Filter value cannot be None" in str(exc_info.value)

    async def test_filter_non_dict_value(self, tortoise_adapter):
        """Test filter with non-dict value (should be skipped)"""
        filters = {
            "test": "not a dict"
        }

        # Should not raise, just skip the invalid filter
        items = await tortoise_adapter.get_all(filters, {}, {"skip": 0, "limit": 10})
        assert isinstance(items, list)
