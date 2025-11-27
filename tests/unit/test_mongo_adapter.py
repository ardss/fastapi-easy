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

@pytest.mark.asyncio
async def test_init_with_string_no_database():
    """Test initialization with string collection name but no database"""
    with pytest.raises(ValueError, match="Database must be provided"):
        MongoAdapter(collection="users")

@pytest.mark.asyncio
async def test_apply_filters_all_operators(mock_collection):
    """Test all filter operators"""
    adapter = MongoAdapter(collection=mock_collection)
    filters = {
        "exact": {"field": "name", "operator": "exact", "value": "John"},
        "ne": {"field": "status", "operator": "ne", "value": "inactive"},
        "gt": {"field": "age", "operator": "gt", "value": 18},
        "gte": {"field": "score", "operator": "gte", "value": 90},
        "lt": {"field": "price", "operator": "lt", "value": 100},
        "lte": {"field": "quantity", "operator": "lte", "value": 50},
        "in": {"field": "category", "operator": "in", "value": ["A", "B"]},
        "like": {"field": "description", "operator": "like", "value": "test"},
        "ilike": {"field": "title", "operator": "ilike", "value": "CASE"},
    }
    
    query = adapter._apply_filters(filters)
    
    assert query["name"] == "John"
    assert query["status"] == {"$ne": "inactive"}
    assert query["age"] == {"$gt": 18}
    assert query["score"] == {"$gte": 90}
    assert query["price"] == {"$lt": 100}
    assert query["quantity"] == {"$lte": 50}
    assert query["category"] == {"$in": ["A", "B"]}
    assert query["description"] == {"$regex": "test"}
    assert query["title"] == {"$regex": "CASE", "$options": "i"}

@pytest.mark.asyncio
async def test_apply_filters_string_in_value(mock_collection):
    """Test 'in' operator with comma-separated string"""
    adapter = MongoAdapter(collection=mock_collection)
    filters = {
        "tags": {"field": "tags", "operator": "in", "value": "a,b,c"}
    }
    
    query = adapter._apply_filters(filters)
    assert query["tags"] == {"$in": ["a", "b", "c"]}

@pytest.mark.asyncio
async def test_apply_filters_skip_non_dict(mock_collection):
    """Test that non-dict filter values are skipped"""
    adapter = MongoAdapter(collection=mock_collection)
    filters = {
        "invalid": "not a dict",
        "valid": {"field": "name", "operator": "exact", "value": "John"}
    }
    
    query = adapter._apply_filters(filters)
    assert "invalid" not in query
    assert query["name"] == "John"

@pytest.mark.asyncio
async def test_apply_filters_skip_no_field(mock_collection):
    """Test that filters without field are skipped"""
    adapter = MongoAdapter(collection=mock_collection)
    filters = {
        "no_field": {"operator": "exact", "value": "test"}
    }
    
    query = adapter._apply_filters(filters)
    assert len(query) == 0

@pytest.mark.asyncio
async def test_get_all_with_sorting_desc(mock_collection):
    """Test get_all with descending sort"""
    adapter = MongoAdapter(collection=mock_collection)
    
    cursor = MagicMock()
    cursor.sort = MagicMock(return_value=cursor)
    cursor.skip = MagicMock(return_value=cursor)
    cursor.limit = MagicMock(return_value=cursor)
    cursor.to_list = AsyncMock(return_value=[{"name": "John"}])
    
    mock_collection.find.return_value = cursor
    
    result = await adapter.get_all(
        filters={},
        sorts={"created_at": "desc"},
        pagination={"skip": 0, "limit": 10}
    )
    
    cursor.sort.assert_called_with([("created_at", -1)])

@pytest.mark.asyncio
async def test_get_all_error_handling(mock_collection):
    """Test error handling in get_all"""
    from fastapi_easy.core.errors import AppError
    
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.find.side_effect = Exception("Database connection failed")
    
    with pytest.raises(AppError, match="Database error"):
        await adapter.get_all(filters={}, sorts={}, pagination={})

@pytest.mark.asyncio
async def test_get_one_error_handling(mock_collection):
    """Test error handling in get_one"""
    from fastapi_easy.core.errors import AppError
    
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.find_one.side_effect = Exception("Database error")
    
    with pytest.raises(AppError, match="Database error"):
        await adapter.get_one("123")

@pytest.mark.asyncio
async def test_create_duplicate_key_error(mock_collection):
    """Test create with duplicate key error"""
    from fastapi_easy.core.errors import ConflictError
    from pymongo.errors import DuplicateKeyError
    
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.insert_one.side_effect = DuplicateKeyError("Duplicate key")
    
    with pytest.raises(ConflictError, match="Item already exists"):
        await adapter.create({"name": "John"})

@pytest.mark.asyncio
async def test_create_general_error(mock_collection):
    """Test create with general error"""
    from fastapi_easy.core.errors import AppError
    
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.insert_one.side_effect = Exception("Database error")
    
    with pytest.raises(AppError, match="Database error"):
        await adapter.create({"name": "John"})

@pytest.mark.asyncio
async def test_update_removes_pk_field(mock_collection):
    """Test that update removes pk_field from data"""
    adapter = MongoAdapter(collection=mock_collection)
    
    mock_collection.update_one.return_value.matched_count = 1
    mock_collection.find_one.return_value = {"_id": "123", "name": "Updated"}
    
    data = {"_id": "123", "name": "Updated"}
    result = await adapter.update("123", data)
    
    # Verify _id was removed from the update data
    mock_collection.update_one.assert_called_with(
        {"_id": "123"},
        {"$set": {"name": "Updated"}}
    )

@pytest.mark.asyncio
async def test_update_not_found(mock_collection):
    """Test update when item not found"""
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.update_one.return_value.matched_count = 0
    
    result = await adapter.update("999", {"name": "Updated"})
    assert result is None

@pytest.mark.asyncio
async def test_update_duplicate_key_error(mock_collection):
    """Test update with duplicate key error"""
    from fastapi_easy.core.errors import ConflictError
    from pymongo.errors import DuplicateKeyError
    
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.update_one.side_effect = DuplicateKeyError("Duplicate")
    
    with pytest.raises(ConflictError, match="Update conflict"):
        await adapter.update("123", {"name": "John"})

@pytest.mark.asyncio
async def test_update_general_error(mock_collection):
    """Test update with general error"""
    from fastapi_easy.core.errors import AppError
    
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.update_one.side_effect = Exception("Database error")
    
    with pytest.raises(AppError, match="Database error"):
        await adapter.update("123", {"name": "John"})

@pytest.mark.asyncio
async def test_delete_one_not_found(mock_collection):
    """Test delete_one when item not found"""
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.find_one.return_value = None
    
    result = await adapter.delete_one("999")
    assert result is None
    mock_collection.delete_one.assert_not_called()

@pytest.mark.asyncio
async def test_delete_one_error_handling(mock_collection):
    """Test error handling in delete_one"""
    from fastapi_easy.core.errors import AppError
    
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.find_one.side_effect = Exception("Database error")
    
    with pytest.raises(AppError, match="Database error"):
        await adapter.delete_one("123")

@pytest.mark.asyncio
async def test_delete_all(mock_collection):
    """Test delete_all"""
    adapter = MongoAdapter(collection=mock_collection)
    
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[{"_id": "1"}, {"_id": "2"}])
    mock_collection.find.return_value = cursor
    
    result = await adapter.delete_all()
    
    assert len(result) == 2
    mock_collection.delete_many.assert_called_with({})

@pytest.mark.asyncio
async def test_delete_all_error_handling(mock_collection):
    """Test error handling in delete_all"""
    from fastapi_easy.core.errors import AppError
    
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.find.side_effect = Exception("Database error")
    
    with pytest.raises(AppError, match="Database error"):
        await adapter.delete_all()

@pytest.mark.asyncio
async def test_count_with_filters(mock_collection):
    """Test count with filters"""
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.count_documents.return_value = 3
    
    filters = {"age": {"field": "age", "operator": "gt", "value": 18}}
    count = await adapter.count(filters=filters)
    
    assert count == 3
    mock_collection.count_documents.assert_called_with({"age": {"$gt": 18}})

@pytest.mark.asyncio
async def test_count_error_handling(mock_collection):
    """Test error handling in count"""
    from fastapi_easy.core.errors import AppError
    
    adapter = MongoAdapter(collection=mock_collection)
    mock_collection.count_documents.side_effect = Exception("Database error")
    
    with pytest.raises(AppError, match="Database error"):
        await adapter.count(filters={})
