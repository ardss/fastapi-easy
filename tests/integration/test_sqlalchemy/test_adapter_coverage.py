"""Additional coverage tests for SQLAlchemy adapter"""

import pytest
from unittest.mock import MagicMock

from fastapi_easy.core.errors import AppError


@pytest.mark.asyncio
class TestSQLAlchemyAdapterCoverage:
    """Additional coverage tests for SQLAlchemy adapter"""

    async def test_apply_filters_with_invalid_field_name(self, sqlalchemy_adapter):
        """Test _apply_filters with invalid field name"""
        query = MagicMock()
        filters = {
            "test": {"field": None, "operator": "exact", "value": "test"}  # Invalid field name
        }

        with pytest.raises(ValueError, match="Invalid field name"):
            sqlalchemy_adapter._apply_filters(query, filters)

    async def test_apply_filters_with_unsupported_operator(self, sqlalchemy_adapter):
        """Test _apply_filters with unsupported operator"""
        query = MagicMock()
        filters = {
            "test": {
                "field": "name",
                "operator": "invalid_op",  # Unsupported operator
                "value": "test",
            }
        }

        with pytest.raises(ValueError, match="Unsupported operator"):
            sqlalchemy_adapter._apply_filters(query, filters)

    async def test_apply_filters_with_none_value(self, sqlalchemy_adapter):
        """Test _apply_filters with None value"""
        query = MagicMock()
        filters = {"test": {"field": "name", "operator": "exact", "value": None}}  # None value

        with pytest.raises(ValueError, match="Filter value cannot be None"):
            sqlalchemy_adapter._apply_filters(query, filters)

    async def test_apply_filters_with_nonexistent_field(self, sqlalchemy_adapter):
        """Test _apply_filters with nonexistent field"""
        query = MagicMock()
        filters = {"test": {"field": "nonexistent_field", "operator": "exact", "value": "test"}}

        with pytest.raises(ValueError, match="Field not found on model"):
            sqlalchemy_adapter._apply_filters(query, filters)

    async def test_apply_filters_with_non_dict_filter(self, sqlalchemy_adapter):
        """Test _apply_filters skips non-dict filters"""
        query = MagicMock()
        filters = {"test": "not_a_dict"}  # Non-dict filter

        query.where = MagicMock(return_value=query)
        result = sqlalchemy_adapter._apply_filters(query, filters)

        # Should return query unchanged
        assert result == query

    async def test_get_all_with_invalid_sort_field(self, sqlalchemy_adapter, sample_items):
        """Test get_all with invalid sort field"""
        result = await sqlalchemy_adapter.get_all(
            filters={},
            sorts={"nonexistent_field": "asc"},  # Invalid sort field
            pagination={"skip": 0, "limit": 10},
        )

        # Should still return results, skipping invalid sort
        assert len(result) > 0

    async def test_get_all_with_desc_sort(self, sqlalchemy_adapter, sample_items):
        """Test get_all with descending sort"""
        result = await sqlalchemy_adapter.get_all(
            filters={}, sorts={"price": "desc"}, pagination={"skip": 0, "limit": 10}
        )

        # Should return sorted results
        assert len(result) > 0
        if len(result) > 1:
            # Verify descending order
            assert result[0].price >= result[-1].price

    async def test_get_all_with_asc_sort(self, sqlalchemy_adapter, sample_items):
        """Test get_all with ascending sort"""
        result = await sqlalchemy_adapter.get_all(
            filters={}, sorts={"price": "asc"}, pagination={"skip": 0, "limit": 10}
        )

        # Should return sorted results
        assert len(result) > 0
        if len(result) > 1:
            # Verify ascending order
            assert result[0].price <= result[-1].price

    async def test_get_all_with_filter_error(self, sqlalchemy_adapter):
        """Test get_all with filter that causes error"""
        with pytest.raises(AppError):
            await sqlalchemy_adapter.get_all(
                filters={
                    "test": {"field": None, "operator": "exact", "value": "test"}  # Invalid field
                },
                sorts={},
                pagination={"skip": 0, "limit": 10},
            )

    async def test_get_all_with_multiple_sorts(self, sqlalchemy_adapter, sample_items):
        """Test get_all with multiple sort fields"""
        result = await sqlalchemy_adapter.get_all(
            filters={}, sorts={"price": "asc", "name": "desc"}, pagination={"skip": 0, "limit": 10}
        )

        # Should return results with multiple sorts applied
        assert len(result) > 0

    async def test_get_all_with_pagination_offset(self, sqlalchemy_adapter, sample_items):
        """Test get_all with pagination offset"""
        # Get first page
        page1 = await sqlalchemy_adapter.get_all(
            filters={}, sorts={}, pagination={"skip": 0, "limit": 2}
        )

        # Get second page
        page2 = await sqlalchemy_adapter.get_all(
            filters={}, sorts={}, pagination={"skip": 2, "limit": 2}
        )

        # Pages should be different
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id
