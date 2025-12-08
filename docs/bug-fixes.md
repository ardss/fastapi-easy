# Bug Fixes and Solutions

This document describes common issues and their solutions that have been implemented in FastAPI-Easy.

## Fixed Issues

### 1. 🐛 Pydantic模型依赖注入导致OpenAPI文档错误显示GET请求需要请求体

**Problem**: When using Pydantic models as dependencies via `Depends()` in FastAPI GET endpoints, the OpenAPI documentation incorrectly shows that the GET request requires a request body, which conflicts with RESTful API conventions.

**Solution**: Use the `QueryParams` utility to convert Pydantic models into proper query parameters.

```python
from fastapi import FastAPI, Depends
from fastapi_easy.utils import as_query_params
from pydantic import BaseModel

app = FastAPI()

class QueryParams(BaseModel):
    name: str
    age: int

# ❌ Old way - shows request body in OpenAPI
@app.get("/users-old")
async def get_users_old(params: QueryParams = Depends()):
    return params

# ✅ New way - correctly shows query parameters
@app.get("/users")
async def get_users(params: QueryParams = Depends(as_query_params(QueryParams))):
    return {"name": params.name, "age": params.age}
```

### 2. 🐛 静态文件服务导致前端应用无法正确获取资源

**Problem**: FastAPI's static file serving has issues with MIME type detection and caching, causing frontend applications to fail to properly retrieve static resource files.

**Solution**: Use the `EnhancedStaticFiles` class which provides proper MIME type detection, ETag support, and caching headers.

```python
from fastapi import FastAPI
from fastapi_easy.utils import setup_static_files

app = FastAPI()

# Basic usage with proper MIME types and caching
setup_static_files(app, "/static", "static")

# Advanced usage with CORS for development
if os.getenv("ENVIRONMENT") == "development":
    setup_static_files(
        app,
        path="/static",
        directory="static",
        cache_control=0,  # No caching in dev
        enable_cors=True
    )
```

### 3. 🐛 异步接口卡死问题 - Socket连接未正确关闭

**Problem**: In high-concurrency scenarios, database connections aren't properly closed, leading to interface freezing and connection pool exhaustion.

**Solution**: Use the `ConnectionManager` to properly manage database connections with automatic cleanup and health checks.

```python
import asyncpg
from fastapi import FastAPI, Depends
from fastapi_easy.utils import ConnectionManager, with_connection_manager, managed_connection

app = FastAPI()

# Create connection manager
conn_manager = ConnectionManager()

async def create_db_connection():
    """Database connection factory"""
    return await asyncpg.connect("postgresql://user:pass@localhost/db")

# Set up connection factory
conn_manager.set_connection_factory(create_db_connection)
await conn_manager.start_cleanup_task()

# Method 1: Using decorator
@app.get("/data")
@with_connection_manager(create_db_connection)
async def get_data(connection_manager: ConnectionManager):
    async with managed_connection() as conn:
        return await conn.fetch("SELECT * FROM table")

# Method 2: Manual management
@app.get("/data2")
async def get_data_2():
    async with managed_connection() as conn:
        return await conn.fetch("SELECT * FROM table")

# Graceful shutdown
@app.on_event("shutdown")
async def shutdown():
    await conn_manager.shutdown()
```

### 4. 🐛 热重载功能导致Token状态不一致

**Problem**: In development environments, FastAPI's hot reload clears in-memory state, causing JWT tokens or other session states to become inconsistent across reloads.

**Solution**: Use the `StateManager` or `TokenStore` to persist state across hot reloads.

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi_easy.utils import TokenStore, StateManager, persistent_state

app = FastAPI()

# Initialize token store that persists across reloads
token_store = TokenStore()

# Method 1: Using TokenStore for JWT tokens
@app.post("/login")
async def login(username: str, password: str):
    # Authenticate user...
    if authenticate(username, password):
        token = generate_jwt_token(username)
        # Store token - persists across hot reloads
        token_store.add_token(username, token, expires_in=3600)
        return {"token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/protected")
async def protected_route(token: str = Depends(get_token_from_header)):
    # Validate token - works across hot reloads
    if token_store.is_valid(get_user_from_token(token), token):
        return {"message": "Access granted"}
    raise HTTPException(status_code=401, detail="Invalid token")

# Method 2: Using StateManager for general state persistence
state_manager = StateManager()

@persistent_state("user_permissions", ttl=3600)
def load_user_permissions():
    # This expensive operation is cached across reloads
    return database.load_all_permissions()

# Method 3: Direct state management
@app.get("/config")
async def get_config():
    config = state_manager.get("app_config")
    if not config:
        config = load_expensive_config()
        state_manager.set("app_config", config, ttl=300)
    return config
```

## Best Practices

### Development Environment

```python
from fastapi import FastAPI
from fastapi_easy.utils import setup_static_files, StateManager, TokenStore

app = FastAPI()

# Enable hot-reload friendly features
if os.getenv("ENVIRONMENT") == "development":
    # Static files with CORS and no caching
    setup_static_files(
        app,
        "/static",
        "static",
        cache_control=0,
        enable_cors=True
    )

    # Initialize state management
    token_store = TokenStore()
    state_manager = StateManager()

    # Clear expired state periodically
    @app.on_event("startup")
    async def startup():
        state_manager.clear_expired()
        token_store.clear_expired_tokens()
```

### Production Environment

```python
from fastapi import FastAPI
from fastapi_easy.utils import ConnectionManager, EnhancedStaticFiles
import uvicorn

app = FastAPI()

# Production static file serving
app.mount(
    "/static",
    EnhancedStaticFiles(
        directory="static",
        cache_control=86400,  # 24 hours
        enable_cors=False
    ),
    name="static"
)

# Database connection management
conn_manager = ConnectionManager()
await conn_manager.start_cleanup_task()

# Health check endpoint
@app.get("/health")
async def health_check():
    stats = await conn_manager.get_stats()
    return {
        "status": "healthy",
        "connections": stats
    }
```

## Additional Resources

- [FastAPI-Easy Documentation](../README.md)
- [API Reference](reference/api.md)
- [Security Guide](security/)
- [Examples](../examples/)