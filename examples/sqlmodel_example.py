"""
SQLModel Example for FastAPI-Easy

This example demonstrates how to use FastAPI-Easy with SQLModel.
It showcases the "Deep Integration" features like separate Create/Read/Update schemas.
"""

import asyncio
from typing import Optional, List
from fastapi import FastAPI
from contextlib import asynccontextmanager

try:
    from sqlmodel import Field, SQLModel, select
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    
    from fastapi_easy import CRUDRouter
    from fastapi_easy.backends.sqlmodel import SQLModelAdapter
except ImportError:
    print("Please install 'sqlmodel' and 'aiosqlite' to run this example.")
    exit(1)

# 1. Define SQLModel Models (Best Practices)
class HeroBase(SQLModel):
    name: str = Field(index=True)
    secret_name: str
    age: Optional[int] = Field(default=None, index=True)

class Hero(HeroBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class HeroCreate(HeroBase):
    pass

class HeroRead(HeroBase):
    id: int

class HeroUpdate(SQLModel):
    name: Optional[str] = None
    secret_name: Optional[str] = None
    age: Optional[int] = None

# 2. Setup Database
DATABASE_URL = "sqlite+aiosqlite:///./sqlmodel_example.db"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

# 3. Create FastAPI App
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title="FastAPI-Easy SQLModel Example",
    lifespan=lifespan
)

# 4. Create CRUD Router
# We use the Table Model (Hero) for the Adapter
adapter = SQLModelAdapter(
    model=Hero,
    session_factory=async_session_factory
)

# We use specific Schemas for the Router
hero_router = CRUDRouter(
    schema=HeroRead,          # Used for Reading (Response)
    create_schema=HeroCreate, # Used for Creation (Request Body)
    update_schema=HeroUpdate, # Used for Updates (Request Body)
    adapter=adapter,
    prefix="/heroes",
    tags=["Heroes"]
)

app.include_router(hero_router)

@app.get("/")
async def root():
    return {
        "message": "Welcome to FastAPI-Easy SQLModel Example",
        "docs": "http://localhost:8003/docs"
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting FastAPI-Easy SQLModel Example...")
    print("✨ Features: Separate Create/Read/Update schemas supported!")
    uvicorn.run(app, host="0.0.0.0", port=8003)
