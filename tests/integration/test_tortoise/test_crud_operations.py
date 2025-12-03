"""Tortoise ORM CRUD operations integration tests"""

import pytest


@pytest.mark.asyncio
class TestTortoiseCRUD:
    """Test Tortoise ORM CRUD operations"""

    async def test_create_item(self, tortoise_adapter):
        """Test creating an item"""
        data = {"name": "apple", "price": 10.0}

        item = await tortoise_adapter.create(data)

        assert item is not None
        assert item.id is not None
        assert item.name == "apple"
        assert item.price == 10.0

    async def test_get_one_item(self, tortoise_adapter, sample_items):
        """Test getting a single item"""
        item_id = sample_items[0].id

        item = await tortoise_adapter.get_one(item_id)

        assert item is not None
        assert item.id == item_id
        assert item.name == "apple"

    async def test_get_one_not_found(self, tortoise_adapter):
        """Test getting non-existent item"""
        item = await tortoise_adapter.get_one(999)

        assert item is None

    async def test_get_all_items(self, tortoise_adapter, sample_items):
        """Test getting all items"""
        items = await tortoise_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 5
        assert items[0].name == "apple"

    async def test_get_all_with_pagination(self, tortoise_adapter, sample_items):
        """Test getting items with pagination"""
        items = await tortoise_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 2},
        )

        assert len(items) == 2

    async def test_get_all_with_skip(self, tortoise_adapter, sample_items):
        """Test getting items with skip"""
        items = await tortoise_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 2, "limit": 10},
        )

        assert len(items) == 3
        assert items[0].name == "orange"

    async def test_update_item(self, tortoise_adapter, sample_items):
        """Test updating an item"""
        item_id = sample_items[0].id
        data = {"name": "red apple", "price": 12.0}

        updated = await tortoise_adapter.update(item_id, data)

        assert updated is not None
        assert updated.name == "red apple"
        assert updated.price == 12.0

    async def test_update_not_found(self, tortoise_adapter):
        """Test updating non-existent item"""
        data = {"name": "test"}

        result = await tortoise_adapter.update(999, data)

        assert result is None

    async def test_delete_one_item(self, tortoise_adapter, sample_items):
        """Test deleting a single item"""
        item_id = sample_items[0].id

        deleted = await tortoise_adapter.delete_one(item_id)

        assert deleted is not None
        assert deleted.id == item_id

        # Verify it's deleted
        item = await tortoise_adapter.get_one(item_id)
        assert item is None

    async def test_delete_one_not_found(self, tortoise_adapter):
        """Test deleting non-existent item"""
        result = await tortoise_adapter.delete_one(999)

        assert result is None

    async def test_delete_all_items(self, tortoise_adapter, sample_items):
        """Test deleting all items"""
        deleted = await tortoise_adapter.delete_all()

        assert len(deleted) == 5

        # Verify all are deleted
        items = await tortoise_adapter.get_all(
            filters={},
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )
        assert len(items) == 0

    async def test_count_items(self, tortoise_adapter, sample_items):
        """Test counting items"""
        count = await tortoise_adapter.count({})

        assert count == 5

    async def test_count_with_filters(self, tortoise_adapter, sample_items):
        """Test counting with filters"""
        filters = {
            "price__gt": {"field": "price", "operator": "gt", "value": 10}
        }

        count = await tortoise_adapter.count(filters)

        assert count == 2  # grape (15), mango (12) - price > 10


@pytest.mark.asyncio
class TestTortoiseFiltering:
    """Test Tortoise ORM filtering operations"""

    async def test_filter_exact(self, tortoise_adapter, sample_items):
        """Test exact filter"""
        filters = {
            "name": {"field": "name", "operator": "exact", "value": "apple"}
        }

        items = await tortoise_adapter.get_all(
            filters=filters,
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 1
        assert items[0].name == "apple"

    async def test_filter_gt(self, tortoise_adapter, sample_items):
        """Test greater than filter"""
        filters = {
            "price__gt": {"field": "price", "operator": "gt", "value": 10}
        }

        items = await tortoise_adapter.get_all(
            filters=filters,
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 2
        assert all(item.price > 10 for item in items)

    async def test_filter_gte(self, tortoise_adapter, sample_items):
        """Test greater than or equal filter"""
        filters = {
            "price__gte": {"field": "price", "operator": "gte", "value": 10}
        }

        items = await tortoise_adapter.get_all(
            filters=filters,
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 3
        assert all(item.price >= 10 for item in items)

    async def test_filter_lt(self, tortoise_adapter, sample_items):
        """Test less than filter"""
        filters = {
            "price__lt": {"field": "price", "operator": "lt", "value": 10}
        }

        items = await tortoise_adapter.get_all(
            filters=filters,
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 2
        assert all(item.price < 10 for item in items)

    async def test_filter_lte(self, tortoise_adapter, sample_items):
        """Test less than or equal filter"""
        filters = {
            "price__lte": {"field": "price", "operator": "lte", "value": 10}
        }

        items = await tortoise_adapter.get_all(
            filters=filters,
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 3
        assert all(item.price <= 10 for item in items)

    async def test_filter_in(self, tortoise_adapter, sample_items):
        """Test in filter"""
        filters = {
            "name__in": {"field": "name", "operator": "in", "value": ["apple", "banana"]}
        }

        items = await tortoise_adapter.get_all(
            filters=filters,
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 2
        assert all(item.name in ["apple", "banana"] for item in items)

    async def test_filter_like(self, tortoise_adapter, sample_items):
        """Test like filter"""
        filters = {
            "name__like": {"field": "name", "operator": "like", "value": "app"}
        }

        items = await tortoise_adapter.get_all(
            filters=filters,
            sorts={},
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 1
        assert items[0].name == "apple"


@pytest.mark.asyncio
class TestTortoiseSorting:
    """Test Tortoise ORM sorting operations"""

    async def test_sort_ascending(self, tortoise_adapter, sample_items):
        """Test ascending sort"""
        sorts = {"name": "asc"}

        items = await tortoise_adapter.get_all(
            filters={},
            sorts=sorts,
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 5
        assert items[0].name == "apple"
        assert items[-1].name == "orange"

    async def test_sort_descending(self, tortoise_adapter, sample_items):
        """Test descending sort"""
        sorts = {"price": "desc"}

        items = await tortoise_adapter.get_all(
            filters={},
            sorts=sorts,
            pagination={"skip": 0, "limit": 10},
        )

        assert len(items) == 5
        assert items[0].price == 15.0  # grape
        assert items[-1].price == 5.0  # banana
