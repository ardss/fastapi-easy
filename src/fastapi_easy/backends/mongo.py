"""MongoDB (Motor) adapter"""

from typing import Any, Dict, List, Optional, Tuple, Union
from .base import BaseORMAdapter
from ..core.errors import ConflictError, AppError, ErrorCode

try:
    from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
    from pymongo.errors import DuplicateKeyError
except ImportError:
    AsyncIOMotorDatabase = Any  # type: ignore
    AsyncIOMotorCollection = Any  # type: ignore
    DuplicateKeyError = Exception  # type: ignore


class MongoAdapter(BaseORMAdapter):
    """MongoDB adapter using Motor
    
    Supports MongoDB with async/await using Motor driver.
    """
    
    # Supported filter operators
    SUPPORTED_OPERATORS = {"exact", "ne", "gt", "gte", "lt", "lte", "in", "like", "ilike"}
    
    def __init__(
        self,
        collection: Union[str, AsyncIOMotorCollection],
        database: Optional[AsyncIOMotorDatabase] = None,
        pk_field: str = "_id",
    ):
        """Initialize MongoDB adapter
        
        Args:
            collection: Collection name (str) or Motor collection object
            database: Motor database object (required if collection is str)
            pk_field: Primary key field name (default: "_id")
        """
        if isinstance(collection, str):
            if database is None:
                raise ValueError("Database must be provided when collection is a string")
            self.collection = database[collection]
        else:
            self.collection = collection
            
        # We don't use the 'model' and 'session_factory' from base in the same way,
        # but we pass them to super to satisfy interface if needed, or just ignore.
        # BaseORMAdapter stores them as self.model and self.session_factory.
        super().__init__(model=None, session_factory=None)
        self.pk_field = pk_field

    def _apply_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Convert generic filters to MongoDB query
        
        Args:
            filters: Generic filter conditions
            
        Returns:
            MongoDB query dictionary
        """
        query = {}
        
        for filter_key, filter_value in filters.items():
            if not isinstance(filter_value, dict):
                continue
            
            field_name = filter_value.get("field")
            if not field_name:
                continue
                
            operator = filter_value.get("operator", "exact")
            value = filter_value.get("value")
            
            if operator == "exact":
                query[field_name] = value
            elif operator == "ne":
                query[field_name] = {"$ne": value}
            elif operator == "gt":
                query[field_name] = {"$gt": value}
            elif operator == "gte":
                query[field_name] = {"$gte": value}
            elif operator == "lt":
                query[field_name] = {"$lt": value}
            elif operator == "lte":
                query[field_name] = {"$lte": value}
            elif operator == "in":
                values = value.split(",") if isinstance(value, str) else value
                query[field_name] = {"$in": values}
            elif operator == "like":
                query[field_name] = {"$regex": value}
            elif operator == "ilike":
                query[field_name] = {"$regex": value, "$options": "i"}
                
        return query

    async def get_all(
        self,
        filters: Dict[str, Any],
        sorts: Dict[str, Any],
        pagination: Dict[str, Any],
    ) -> List[Any]:
        """Get all items with filtering, sorting, and pagination"""
        try:
            query = self._apply_filters(filters)
            
            cursor = self.collection.find(query)
            
            # Apply sorting
            if sorts:
                sort_list = []
                for field_name, direction in sorts.items():
                    direction_val = 1 if direction == "asc" else -1
                    sort_list.append((field_name, direction_val))
                cursor.sort(sort_list)
            
            # Apply pagination
            skip = pagination.get("skip", 0)
            limit = pagination.get("limit", 10)
            cursor.skip(skip).limit(limit)
            
            items = await cursor.to_list(length=limit)
            
            # Handle _id mapping if needed, or return as is.
            # Usually Pydantic models handle _id -> id mapping if configured.
            return items
            
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                message=f"Database error: {str(e)}"
            )

    async def get_one(self, id: Any) -> Optional[Any]:
        """Get single item by id"""
        try:
            # Note: User is responsible for converting id to ObjectId if needed
            # or we could try to auto-detect. For now, pass as is.
            return await self.collection.find_one({self.pk_field: id})
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                message=f"Database error: {str(e)}"
            )

    async def create(self, data: Dict[str, Any]) -> Any:
        """Create new item"""
        try:
            result = await self.collection.insert_one(data)
            # Fetch the created item to return it
            created_item = await self.collection.find_one({"_id": result.inserted_id})
            return created_item
        except DuplicateKeyError as e:
            raise ConflictError(f"Item already exists: {str(e)}")
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                message=f"Database error: {str(e)}"
            )

    async def update(self, id: Any, data: Dict[str, Any]) -> Any:
        """Update item"""
        try:
            # Don't update the pk_field
            if self.pk_field in data:
                del data[self.pk_field]
                
            result = await self.collection.update_one(
                {self.pk_field: id},
                {"$set": data}
            )
            
            if result.matched_count == 0:
                return None
                
            return await self.collection.find_one({self.pk_field: id})
        except DuplicateKeyError as e:
            raise ConflictError(f"Update conflict: {str(e)}")
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                message=f"Database error: {str(e)}"
            )

    async def delete_one(self, id: Any) -> Any:
        """Delete single item"""
        try:
            item = await self.collection.find_one({self.pk_field: id})
            if not item:
                return None
                
            await self.collection.delete_one({self.pk_field: id})
            return item
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                message=f"Database error: {str(e)}"
            )

    async def delete_all(self) -> List[Any]:
        """Delete all items"""
        try:
            # Get all items first with a reasonable limit to avoid memory issues
            # Default limit of 10000 items to prevent memory overflow
            MAX_DELETE_ITEMS = 10000
            items = await self.collection.find().to_list(length=MAX_DELETE_ITEMS)
            
            # If there are more items than the limit, log a warning
            if len(items) >= MAX_DELETE_ITEMS:
                if hasattr(self, 'logger'):
                    self.logger.warning(f"delete_all returned {MAX_DELETE_ITEMS} items (limit reached)")
            
            await self.collection.delete_many({})
            return items
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                message=f"Database error: {str(e)}"
            )

    async def count(self, filters: Dict[str, Any]) -> int:
        """Count items"""
        try:
            query = self._apply_filters(filters)
            return await self.collection.count_documents(query)
        except Exception as e:
            raise AppError(
                code=ErrorCode.INTERNAL_ERROR,
                status_code=500,
                message=f"Database error: {str(e)}"
            )
