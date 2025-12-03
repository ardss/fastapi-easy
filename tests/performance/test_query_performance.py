"""Performance tests for query operations"""

import pytest


@pytest.mark.asyncio
class TestQueryPerformance:
    """Performance tests for query operations"""

    async def test_large_dataset_retrieval(self, perf_sqlalchemy_adapter, large_dataset):
        """Test retrieval of large dataset (5000+ items)"""
        result = await perf_sqlalchemy_adapter.get_all(
            filters={}, sorts={}, pagination={"skip": 0, "limit": 5000}
        )
        assert len(result) == 5000

    async def test_filtered_query_performance(self, perf_sqlalchemy_adapter, large_dataset):
        """Test filtered query performance"""
        result = await perf_sqlalchemy_adapter.get_all(
            filters={"price_filter": {"field": "price", "operator": "gte", "value": 500.0}},
            sorts={},
            pagination={"skip": 0, "limit": 1000},
        )
        assert len(result) > 0

    async def test_sorted_query_performance(self, perf_sqlalchemy_adapter, large_dataset):
        """Test sorted query performance"""
        result = await perf_sqlalchemy_adapter.get_all(
            filters={}, sorts={"price": "desc"}, pagination={"skip": 0, "limit": 1000}
        )
        assert len(result) == 1000

    async def test_paginated_query_performance(self, perf_sqlalchemy_adapter, large_dataset):
        """Test paginated query performance"""
        results = []
        for page in range(5):
            result = await perf_sqlalchemy_adapter.get_all(
                filters={}, sorts={}, pagination={"skip": page * 1000, "limit": 1000}
            )
            results.extend(result)
        assert len(results) == 5000

    async def test_single_item_retrieval_performance(self, perf_sqlalchemy_adapter, large_dataset):
        """Test single item retrieval performance"""
        result = await perf_sqlalchemy_adapter.get_one(2500)
        assert result is not None

    async def test_count_performance(self, perf_sqlalchemy_adapter, large_dataset):
        """Test count operation performance"""
        result = await perf_sqlalchemy_adapter.count({})
        assert result == 5000

    async def test_create_performance(self, perf_sqlalchemy_adapter):
        """Test create operation performance"""
        result = await perf_sqlalchemy_adapter.create(
            {"name": "test_item", "description": "Test description", "price": 99.99, "quantity": 10}
        )
        assert result is not None
        assert result.name == "test_item"

    async def test_update_performance(self, perf_sqlalchemy_adapter, large_dataset):
        """Test update operation performance"""
        result = await perf_sqlalchemy_adapter.update(2500, {"price": 199.99, "quantity": 50})
        assert result is not None
        assert result.price == 199.99

    async def test_delete_performance(self, perf_sqlalchemy_adapter, large_dataset):
        """Test delete operation performance"""
        result = await perf_sqlalchemy_adapter.delete_one(4999)
        assert result is not None
