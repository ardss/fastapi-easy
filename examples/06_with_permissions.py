"""
Example 6: FastAPI-Easy with Permission Control

This example demonstrates how to use the permission control module
to protect your CRUD routes with JWT authentication and role-based access control.

Features:
- JWT authentication
- Role-based access control (RBAC)
- Permission checking
- Login and token refresh endpoints
"""

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# Import security components
from fastapi_easy.security import (
    JWTAuth,
    init_jwt_auth,
    get_current_user,
    require_role,
    require_permission,
    TokenRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
)

# Create FastAPI app
app = FastAPI(
    title="FastAPI-Easy with Permissions",
    description="Example of permission control in FastAPI-Easy",
    version="1.0.0",
)

# ============================================================================
# 1. Initialize JWT Authentication
# ============================================================================

# Initialize JWT auth with custom settings
jwt_auth = init_jwt_auth(
    secret_key="your-secret-key-change-in-production",
    algorithm="HS256",
    access_token_expire_minutes=15,
    refresh_token_expire_days=7,
)


# ============================================================================
# 2. Define Data Models
# ============================================================================

class Item(BaseModel):
    """Item model"""

    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    owner_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(BaseModel):
    """User model"""

    id: Optional[int] = None
    username: str
    email: str
    roles: List[str] = ["user"]
    is_active: bool = True
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# 3. Mock Database
# ============================================================================

# Mock users database
USERS_DB = {
    1: {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "password_hash": "hashed_password_123",  # In production, use bcrypt
        "roles": ["admin", "editor", "user"],
        "is_active": True,
        "created_at": datetime.now(),
    },
    2: {
        "id": 2,
        "username": "editor",
        "email": "editor@example.com",
        "password_hash": "hashed_password_456",
        "roles": ["editor", "user"],
        "is_active": True,
        "created_at": datetime.now(),
    },
    3: {
        "id": 3,
        "username": "viewer",
        "email": "viewer@example.com",
        "password_hash": "hashed_password_789",
        "roles": ["user"],
        "is_active": True,
        "created_at": datetime.now(),
    },
}

# Mock items database
ITEMS_DB = {
    1: {
        "id": 1,
        "name": "Item 1",
        "description": "First item",
        "price": 100.0,
        "owner_id": 1,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
    2: {
        "id": 2,
        "name": "Item 2",
        "description": "Second item",
        "price": 200.0,
        "owner_id": 2,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    },
}


# ============================================================================
# 4. Authentication Endpoints
# ============================================================================

@app.post("/auth/login", response_model=TokenResponse)
async def login(request: TokenRequest):
    """Login endpoint

    Args:
        request: Username and password

    Returns:
        Access token and refresh token

    Raises:
        HTTPException: If credentials are invalid
    """
    # Find user by username
    user = None
    for u in USERS_DB.values():
        if u["username"] == request.username:
            user = u
            break

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password (in production, use bcrypt)
    if user["password_hash"] != f"hashed_{request.password}":
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate tokens
    access_token = jwt_auth.create_access_token(
        subject=str(user["id"]),
        roles=user["roles"],
    )
    refresh_token = jwt_auth.create_refresh_token(subject=str(user["id"]))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=15 * 60,  # 15 minutes in seconds
    )


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh(request: RefreshTokenRequest):
    """Refresh access token

    Args:
        request: Refresh token

    Returns:
        New access token

    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Verify refresh token
        payload = jwt_auth.verify_token(request.refresh_token)

        if payload.type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # Get user from database
        user_id = int(payload.sub)
        user = USERS_DB.get(user_id)

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        # Generate new access token
        access_token = jwt_auth.create_access_token(
            subject=str(user["id"]),
            roles=user["roles"],
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,
            expires_in=15 * 60,
        )

    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# ============================================================================
# 5. Public Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FastAPI-Easy with Permissions",
        "endpoints": {
            "login": "POST /auth/login",
            "refresh": "POST /auth/refresh",
            "items": "GET /items",
            "create_item": "POST /items (requires editor role)",
            "update_item": "PUT /items/{item_id} (requires editor role)",
            "delete_item": "DELETE /items/{item_id} (requires admin role)",
        },
    }


@app.get("/items", response_model=List[Item])
async def list_items():
    """List all items (public endpoint)"""
    return list(ITEMS_DB.values())


# ============================================================================
# 6. Protected Endpoints - Require Authentication
# ============================================================================

@app.get("/items/my-items", response_model=List[Item])
async def my_items(current_user: dict = Depends(get_current_user)):
    """Get current user's items

    Args:
        current_user: Current user from JWT token

    Returns:
        List of items owned by current user
    """
    user_id = int(current_user["user_id"])
    items = [item for item in ITEMS_DB.values() if item["owner_id"] == user_id]
    return items


@app.get("/profile", response_model=User)
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get current user's profile

    Args:
        current_user: Current user from JWT token

    Returns:
        User profile
    """
    user_id = int(current_user["user_id"])
    user = USERS_DB.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(**user)


# ============================================================================
# 7. Protected Endpoints - Require Role
# ============================================================================

@app.post("/items", response_model=Item)
async def create_item(
    item: Item,
    current_user: dict = Depends(require_role("editor", "admin")),
):
    """Create a new item

    Requires: editor or admin role

    Args:
        item: Item data
        current_user: Current user from JWT token

    Returns:
        Created item
    """
    user_id = int(current_user["user_id"])

    # Create item
    new_id = max(ITEMS_DB.keys()) + 1 if ITEMS_DB else 1
    new_item = {
        "id": new_id,
        "name": item.name,
        "description": item.description,
        "price": item.price,
        "owner_id": user_id,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    ITEMS_DB[new_id] = new_item
    return Item(**new_item)


@app.put("/items/{item_id}", response_model=Item)
async def update_item(
    item_id: int,
    item: Item,
    current_user: dict = Depends(require_role("editor", "admin")),
):
    """Update an item

    Requires: editor or admin role

    Args:
        item_id: Item ID
        item: Updated item data
        current_user: Current user from JWT token

    Returns:
        Updated item

    Raises:
        HTTPException: If item not found or user is not owner/admin
    """
    if item_id not in ITEMS_DB:
        raise HTTPException(status_code=404, detail="Item not found")

    user_id = int(current_user["user_id"])
    existing_item = ITEMS_DB[item_id]

    # Check if user is owner or admin
    if existing_item["owner_id"] != user_id and "admin" not in current_user["roles"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Update item
    existing_item.update({
        "name": item.name,
        "description": item.description,
        "price": item.price,
        "updated_at": datetime.now(),
    })

    return Item(**existing_item)


# ============================================================================
# 8. Protected Endpoints - Require Admin Role
# ============================================================================

@app.delete("/items/{item_id}")
async def delete_item(
    item_id: int,
    current_user: dict = Depends(require_role("admin")),
):
    """Delete an item

    Requires: admin role

    Args:
        item_id: Item ID
        current_user: Current user from JWT token

    Returns:
        Success message

    Raises:
        HTTPException: If item not found
    """
    if item_id not in ITEMS_DB:
        raise HTTPException(status_code=404, detail="Item not found")

    del ITEMS_DB[item_id]
    return {"message": "Item deleted successfully"}


@app.get("/users", response_model=List[User])
async def list_users(current_user: dict = Depends(require_role("admin"))):
    """List all users

    Requires: admin role

    Args:
        current_user: Current user from JWT token

    Returns:
        List of all users
    """
    return [User(**user) for user in USERS_DB.values()]


# ============================================================================
# 9. Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return {
        "error": "HTTP Exception",
        "status_code": exc.status_code,
        "detail": exc.detail,
    }


# ============================================================================
# 10. Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ============================================================================
# Usage Instructions
# ============================================================================

"""
USAGE INSTRUCTIONS:

1. Start the server:
   uvicorn examples.06_with_permissions:app --reload

2. Login to get tokens:
   curl -X POST http://localhost:8000/auth/login \\
     -H "Content-Type: application/json" \\
     -d '{"username": "admin", "password": "password_123"}'

   Response:
   {
     "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "token_type": "bearer",
     "expires_in": 900
   }

3. Use access token to access protected endpoints:
   curl -X GET http://localhost:8000/profile \\
     -H "Authorization: Bearer <access_token>"

4. Refresh token:
   curl -X POST http://localhost:8000/auth/refresh \\
     -H "Content-Type: application/json" \\
     -d '{"refresh_token": "<refresh_token>"}'

5. Create item (requires editor role):
   curl -X POST http://localhost:8000/items \\
     -H "Authorization: Bearer <access_token>" \\
     -H "Content-Type: application/json" \\
     -d '{"name": "New Item", "description": "Test", "price": 99.99}'

6. Delete item (requires admin role):
   curl -X DELETE http://localhost:8000/items/1 \\
     -H "Authorization: Bearer <admin_token>"

USERS:
- admin: admin@example.com (roles: admin, editor, user)
- editor: editor@example.com (roles: editor, user)
- viewer: viewer@example.com (roles: user)

PASSWORD: Use the username as password (e.g., "admin" for admin user)
Note: This is for demo only. In production, use proper password hashing.
"""

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
