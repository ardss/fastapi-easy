"""SQLAlchemy CRUD operations integration tests"""

import pytest


@pytest.mark.asyncio
class TestSQLAlchemyCRUD:
    """Test SQLAlchemy CRUD operations"""
    
    async def test_create_item(self, sqlalchemy_adapter):
        """Test creating an item"""
        data = {"name": "apple", "price": 10.0}
        
        item = await sqlalchemy_adapter.create(data)
        
        assert item is not None
        assert item.id is not None
        assert item.name == "apple"
        assert item.price == 10.0
    
    async def test_get_one_item(self, sqlalchemy_adapter, sample_items):
        """Test getting a single item"""
        item_id = sample_items[0].id
        
        item = await sqlalchemy_adapter.get_one(item_id)
        
        assert item is not None
        assert item.id == item_id
        assert item.name == "apple"
    
    async def test_get_one_not_found(self, sqlalchemy_adapter):
        """Test getting non-existent item"""
        item = await sqlalchemy_adapter.get_one(999)
        
        assert item is None
    
    async def test_get_all_items(self, sqlalchemy_adapter, sample_items):
        """Test getting all items"""
        items = await sqlalchemy_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )
        
        assert len(items) == 5
        assert items[0].name == "apple"
    
    async def test_get_all_with_pagination(self, sqlalchemy_adapter, sample_items):
        """Test getting items with pagination"""
        items = await sqlalchemy_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 2},
        )
        
        assert len(items) == 2
    
    async def test_get_all_with_skip(self, sqlalchemy_adapter, sample_items):
        """Test getting items with skip"""
        items = await sqlalchemy_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 2, "limit": 10},
        )
        
        assert len(items) == 3
        assert items[0].name == "orange"
    
    async def test_update_item(self, sqlalchemy_adapter, sample_items):
        """Test updating an item"""
        item_id = sample_items[0].id
        data = {"name": "red apple", "price": 12.0}
        
        updated = await sqlalchemy_adapter.update(item_id, data)
        
        assert updated is not None
        assert updated.name == "red apple"
        assert updated.price == 12.0
    
    async def test_update_not_found(self, sqlalchemy_adapter):
        """Test updating non-existent item"""
        data = {"name": "test"}
        
        result = await sqlalchemy_adapter.update(999, data)
        
        assert result is None
    
    async def test_delete_one_item(self, sqlalchemy_adapter, sample_items):
        """Test deleting a single item"""
        item_id = sample_items[0].id
        
        deleted = await sqlalchemy_adapter.delete_one(item_id)
        
        assert deleted is not None
        assert deleted.id == item_id
        
        # Verify it's deleted
        item = await sqlalchemy_adapter.get_one(item_id)
        assert item is None
    
    async def test_delete_all_items(self, sqlalchemy_adapter, sample_items):
        """Test deleting all items"""
        deleted = await sqlalchemy_adapter.delete_all()
        
        assert len(deleted) == 5
        
        # Verify all are deleted
        items = await sqlalchemy_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )
        assert len(items) == 0
    
    async def test_count_items(self, sqlalchemy_adapter, sample_items):
        """Test counting items"""
        count = await sqlalchemy_adapter.count({})
        
        assert count == 5
    
    async def test_count_with_filters(self, sqlalchemy_adapter, sample_items):
        """Test counting with filters"""
        filters = {
            "price__gt": {"field": "price", "operator": "gt", "value": 10}
        }
        
        count = await sqlalchemy_adapter.count(filters)
        
        assert count == 3  # apple (10), grape (15), mango (12)
