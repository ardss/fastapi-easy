#!/usr/bin/env python3
"""
FastAPI-Easy Main Application

This is a sample FastAPI application demonstrating FastAPI-Easy framework capabilities.
Run with: uvicorn main:app --reload
"""

import asyncio
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from fastapi_easy import CRUDRouter, SQLAlchemyAdapter
from fastapi_easy.security import require_role

# Database setup
DATABASE_URL = "sqlite+aiosqlite:///./fastapi_easy_demo.db"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    """Database dependency"""
    async with AsyncSessionLocal() as session:
        yield session

# Database models
Base = declarative_base()

class UserDB(Base):
    """User database model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)

# Pydantic schemas
class UserCreate(BaseModel):
    """Create user schema"""
    name: str
    email: str

class UserResponse(BaseModel):
    """User response schema"""
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

# FastAPI app
app = FastAPI(
    title="FastAPI-Easy Demo",
    description="Demonstration of FastAPI-Easy framework capabilities",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include CRUD router for users
app.include_router(
    CRUDRouter(
        schema=UserCreate,
        adapter=SQLAlchemyAdapter(UserDB, get_db),
        prefix="/users",
        tags=["users"]
    )
)

# Custom endpoints
@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to FastAPI-Easy Demo!",
        "docs": "/docs",
        "users": "/users"
    }

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "framework": "FastAPI-Easy"}

@app.get("/protected", tags=["protected"])
@require_role("admin")
async def protected_endpoint():
    """Protected endpoint requiring admin role"""
    return {"message": "This is a protected endpoint for admins only"}

@app.get("/stats", tags=["stats"])
async def get_stats() -> dict:
    """Get application statistics"""
    return {
        "framework": "FastAPI-Easy",
        "version": "0.1.6",
        "features": [
            "Auto CRUD generation",
            "Multi-ORM support",
            "Security & authentication",
            "Migration system",
            "Performance monitoring"
        ]
    }

# Example of using advanced features
@app.post("/bulk-users", tags=["advanced"])
async def create_bulk_users(users: List[UserCreate]) -> dict:
    """Example of bulk operations (would use optimized CRUD router)"""
    return {
        "message": f"Would create {len(users)} users in bulk",
        "count": len(users),
        "users": [{"name": u.name, "email": u.email} for u in users]
    }

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )