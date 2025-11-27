import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi_easy.backends.mongo import MongoAdapter

@pytest.fixture
def mock_collection():
    collection = MagicMock()
    # Mock async methods
    collection.find = MagicMock()
    collection.find_one = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.update_one = AsyncMock()
    collection.delete_one = AsyncMock()
    collection.delete_many = AsyncMock()
    collection.count_documents = AsyncMock()
    return collection

@pytest.fixture
def mock_db(mock_collection):
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=mock_collection)
    return db

def test_init_with_string(mock_db):
    adapter = MongoAdapter(collection="users", database=mock_db)
    # Since we mock db["users"], checking identity might be tricky if it returns new mock
    # But we set return_value, so it should be same
    assert adapter.collection == mock_db["users"]

def test_init_with_collection(mock_collection):
    adapter = MongoAdapter(collection=mock_collection)
    assert adapter.collection == mock_collection

def test_apply_filters(mock_collection):
    adapter = MongoAdapter(collection=mock_collection)
    filters = {
        "name": {"field": "name", "operator": "exact", "value": "John"},
        "age": {"field": "age", "operator": "gt", "value": 18},
        "tags": {"field": "tags", "operator": "in", "value": ["a", "b"]},
        "desc": {"field": "desc", "operator": "like", "value": "test"},
    }
    query = adapter._apply_filters(filters)
    assert query["name"] == "John"
    assert query["age"] == {"$gt": 18}
    assert query["tags"] == {"$in": ["a", "b"]}
    assert query["desc"] == {"$regex": "test"}

@pytest.mark.asyncio
async def test_get_all(mock_collection):
    adapter = MongoAdapter(collection=mock_collection)
    
    # Mock cursor
    cursor = MagicMock()
    cursor.sort = MagicMock()
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[{"name": "John"}])
    
    mock_collection.find.return_value = cursor
    
    result = await adapter.get_all(filters={}, sorts={"name": "asc"}, pagination={"skip": 0, "limit": 10})
    
    assert result == [{"name": "John"}]
    mock_collection.find.assert_called_once()
    cursor.sort.assert_called_with([("name", 1)])
    cursor.skip.assert_called_with(0)
    cursor.limit.assert_called_with(10)

@pytest.mark.asyncio
async def test_get_one(mock_collection):
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.find_one.return_value = {"_id": "123", "name": "John"}
    
    result = await adapter.get_one("123")
    assert result == {"_id": "123", "name": "John"}
    mock_collection.find_one.assert_called_with({"_id": "123"})

@pytest.mark.asyncio
async def test_create(mock_collection):
    adapter = MongoAdapter(collection=mock_collection)
    
    mock_collection.insert_one.return_value.inserted_id = "123"
    mock_collection.find_one.return_value = {"_id": "123", "name": "John"}
    
    result = await adapter.create({"name": "John"})
    
    assert result == {"_id": "123", "name": "John"}
    mock_collection.insert_one.assert_called_with({"name": "John"})

@pytest.mark.asyncio
async def test_update(mock_collection):
    adapter = MongoAdapter(collection=mock_collection)
    
    mock_collection.update_one.return_value.matched_count = 1
    mock_collection.find_one.return_value = {"_id": "123", "name": "John Updated"}
    
    result = await adapter.update("123", {"name": "John Updated"})
    
    assert result == {"_id": "123", "name": "John Updated"}
    mock_collection.update_one.assert_called_with({"_id": "123"}, {"$set": {"name": "John Updated"}})

@pytest.mark.asyncio
async def test_delete_one(mock_collection):
    adapter = MongoAdapter(collection=mock_collection)
    
    mock_collection.find_one.return_value = {"_id": "123", "name": "John"}
    
    result = await adapter.delete_one("123")
    
    assert result == {"_id": "123", "name": "John"}
    mock_collection.delete_one.assert_called_with({"_id": "123"})

@pytest.mark.asyncio
async def test_count(mock_collection):
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.count_documents.return_value = 5
    
    count = await adapter.count(filters={})
    assert count == 5
    mock_collection.count_documents.assert_called_with({})
