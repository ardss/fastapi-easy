"""Tortoise ORM conflict error tests"""

import pytest
from tortoise.exceptions import IntegrityError
from unittest.mock import patch
from fastapi_easy.backends.tortoise import TortoiseAdapter
from fastapi_easy.core.errors import ConflictError


@pytest.mark.asyncio
class TestTortoiseConflictErrors:
    """Test Tortoise ORM conflict error handling"""
    
    async def test_create_integrity_error(self, tortoise_adapter):
        """Test create with integrity error (duplicate key)"""
        with patch.object(tortoise_adapter.model, 'create') as mock_create:
            mock_create.side_effect = IntegrityError("Duplicate key")
            
            with pytest.raises(ConflictError) as exc_info:
                await tortoise_adapter.create({"name": "duplicate"})
            
            assert "Item already exists" in str(exc_info.value)
    
    async def test_update_integrity_error_with_unique_constraint(self, unique_item_adapter):
        """Test update with integrity error (unique constraint violation)"""
        # Create two items with unique names
        item1 = await unique_item_adapter.create({"name": "apple", "price": 10.0})
        item2 = await unique_item_adapter.create({"name": "banana", "price": 5.0})
        
        # Try to update item2 to have the same name as item1 (should fail)
        with pytest.raises(ConflictError) as exc_info:
            await unique_item_adapter.update(item2.id, {"name": "apple"})
        
        assert "Update conflict" in str(exc_info.value)


@pytest.mark.asyncio
class TestTortoiseNEFilter:
    """Test Tortoise ORM 'ne' (not equal) filter"""
    
    async def test_filter_ne(self, tortoise_adapter, sample_items):
        """Test not equal filter"""
        filters = {
            "name__ne": {"field": "name", "operator": "ne", "value": "apple"}
        }
        
        items = await tortoise_adapter.get_all(
            filters=filters,
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )
        
        # Should return all items except apple
        assert len(items) == 4
        assert all(item.name != "apple" for item in items)
