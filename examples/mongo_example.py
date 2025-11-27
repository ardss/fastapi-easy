"""
MongoDB Example for FastAPI-Easy

This example demonstrates how to use FastAPI-Easy with MongoDB (via Motor).
"""

import asyncio
import os
from typing import Optional, List
from fastapi import FastAPI
from pydantic import BaseModel, Field, BeforeValidator
from typing_extensions import Annotated

try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from fastapi_easy import CRUDRouter
    from fastapi_easy.backends.mongo import MongoAdapter
except ImportError:
    print("Please install 'motor' and 'fastapi-easy' to run this example.")
    exit(1)

# 1. Define Pydantic models
# Helper to handle ObjectId as string
PyObjectId = Annotated[str, BeforeValidator(str)]

class UserSchema(BaseModel):
    """User API schema"""
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    name: str
    email: str
    age: int
    
    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "name": "Alice",
                "email": "alice@example.com",
                "age": 30
            }
        }

# 2. Setup MongoDB connection
# Use a local MongoDB instance or a mock for demonstration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "fastapi_easy_demo"

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
collection = db["users"]

# 3. Create FastAPI app
app = FastAPI(
    title="FastAPI-Easy MongoDB Example",
    description="Demonstration of MongoDB support",
    version="1.0.0"
)

# 4. Create CRUD router
adapter = MongoAdapter(
    collection=collection,
    pk_field="_id"
)

user_router = CRUDRouter(
    schema=UserSchema,
    adapter=adapter,
    prefix="/users",
    tags=["Users"],
    id_type=str  # Important: MongoDB IDs are strings (ObjectIds)
)

# 5. Include router
app.include_router(user_router)

@app.on_event("startup")
async def startup():
    print("Connected to MongoDB")

@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI-Easy MongoDB Example"}

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI-Easy MongoDB Example...")
    print("Make sure you have a MongoDB instance running at localhost:27017")
    uvicorn.run(app, host="0.0.0.0", port=8002)
