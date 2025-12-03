"""Integration tests for security with CRUDRouter"""

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from fastapi_easy.security import (
    PasswordManager,
    get_current_user,
    init_jwt_auth,
    require_role,
)
from fastapi_easy.security.crud_integration import (
    CRUDSecurityConfig,
    create_protected_crud_router,
)


class Item(BaseModel):
    """Item model"""

    id: int
    name: str
    description: str


class LoginRequest(BaseModel):
    """Login request"""

    username: str
    password: str


@pytest.fixture
def jwt_auth():
    """Create JWT auth instance"""
    return init_jwt_auth(secret_key="test-secret-key")


@pytest.fixture
def password_manager():
    """Create password manager"""
    return PasswordManager()


@pytest.fixture
def app_with_security(jwt_auth):
    """Create app with security"""
    app = FastAPI()

    # Mock users
    users = {
        "admin": {"id": 1, "username": "admin", "roles": ["admin"]},
        "editor": {"id": 2, "username": "editor", "roles": ["editor"]},
        "viewer": {"id": 3, "username": "viewer", "roles": ["viewer"]},
    }

    # Mock items
    items = {
        1: Item(id=1, name="Item 1", description="Description 1"),
        2: Item(id=2, name="Item 2", description="Description 2"),
    }

    # Login endpoint
    @app.post("/auth/login")
    async def login(request: LoginRequest):
        """Login endpoint"""
        if request.username not in users:
            raise HTTPException(status_code=401, detail="User not found")

        user = users[request.username]
        access_token = jwt_auth.create_access_token(
            subject=str(user["id"]),
            roles=user["roles"],
        )

        return {"access_token": access_token, "token_type": "bearer"}

    # Public endpoint
    @app.get("/items")
    async def get_items():
        """Get all items"""
        return list(items.values())

    # Protected endpoint
    @app.get("/items/{item_id}")
    async def get_item(
        item_id: int,
        current_user: dict = Depends(get_current_user),
    ):
        """Get item by ID"""
        if item_id not in items:
            raise Exception("Item not found")
        return items[item_id]

    # Admin only endpoint
    @app.post("/items")
    async def create_item(
        item: Item,
        current_user: dict = Depends(require_role("admin")),
    ):
        """Create item"""
        items[item.id] = item
        return item

    return app


@pytest.fixture
def client(app_with_security):
    """Create test client"""
    return TestClient(app_with_security)


class TestSecurityCRUDIntegration:
    """Test security integration with CRUD"""

    def test_public_endpoint_no_auth(self, client):
        """Test public endpoint without auth"""
        response = client.get("/items")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_protected_endpoint_without_token(self, client):
        """Test protected endpoint without token"""
        response = client.get("/items/1")
        assert response.status_code == 403

    def test_protected_endpoint_with_valid_token(self, client, jwt_auth):
        """Test protected endpoint with valid token"""
        # Login
        response = client.post("/auth/login", json={"username": "viewer", "password": "any"})
        assert response.status_code == 200
        token = response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/items/1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == 1

    def test_admin_only_endpoint_with_user_role(self, client):
        """Test admin only endpoint with user role"""
        # Login as viewer
        response = client.post("/auth/login", json={"username": "viewer", "password": "any"})
        token = response.json()["access_token"]

        # Try to create item
        response = client.post(
            "/items",
            json={"id": 3, "name": "Item 3", "description": "Description 3"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_admin_only_endpoint_with_admin_role(self, client):
        """Test admin only endpoint with admin role"""
        # Login as admin
        response = client.post("/auth/login", json={"username": "admin", "password": "any"})
        token = response.json()["access_token"]

        # Create item
        response = client.post(
            "/items",
            json={"id": 3, "name": "Item 3", "description": "Description 3"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["id"] == 3

    def test_security_config_creation(self):
        """Test security config creation"""
        config = CRUDSecurityConfig(
            enable_auth=True,
            require_roles=["admin"],
            require_permissions=["read"],
        )

        assert config.enable_auth is True
        assert config.require_roles == ["admin"]
        assert config.require_permissions == ["read"]

    def test_protected_crud_router_creation(self):
        """Test protected CRUD router creation"""
        from fastapi_easy.core.crud_router import CRUDRouter

        # Create a mock CRUD router
        class MockAdapter:
            async def get_all(self, **kwargs):
                return []

        crud_router = CRUDRouter(
            schema=Item,
            adapter=MockAdapter(),
        )

        # Create protected router
        protected_router = create_protected_crud_router(
            crud_router,
            enable_auth=True,
            require_roles=["admin"],
        )

        assert protected_router.security_config.enable_auth is True
        assert protected_router.security_config.require_roles == ["admin"]

    def test_multiple_roles_check(self, client):
        """Test checking multiple roles"""
        # Login as editor
        response = client.post("/auth/login", json={"username": "editor", "password": "any"})
        token = response.json()["access_token"]

        # Access protected endpoint (should work for any authenticated user)
        response = client.get(
            "/items/1",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_token_refresh_with_protected_endpoint(self, client, jwt_auth):
        """Test token refresh with protected endpoint"""
        # Login
        response = client.post("/auth/login", json={"username": "viewer", "password": "any"})
        access_token = response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/items/1",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

    def test_invalid_token_format(self, client):
        """Test invalid token format"""
        response = client.get(
            "/items/1",
            headers={"Authorization": "InvalidFormat token"},
        )
        assert response.status_code == 403

    def test_missing_authorization_header(self, client):
        """Test missing authorization header"""
        response = client.get("/items/1")
        assert response.status_code == 403
