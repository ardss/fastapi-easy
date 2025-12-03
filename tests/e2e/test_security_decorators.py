"""Unit tests for security decorators"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from fastapi_easy.security import (
    get_current_user,
    get_jwt_auth,
    init_jwt_auth,
    require_all_permissions,
    require_all_roles,
    require_permission,
    require_role,
)


@pytest.fixture
def jwt_auth():
    """Initialize JWT auth"""
    return init_jwt_auth(secret_key="test-secret-key")


@pytest.fixture
def app(jwt_auth):
    """Create test FastAPI app"""
    app = FastAPI()

    # Public endpoint
    @app.get("/public")
    async def public_endpoint():
        return {"message": "public"}

    # Protected endpoint - requires authentication
    @app.get("/protected")
    async def protected_endpoint(current_user: dict = Depends(get_current_user)):
        return {"user_id": current_user["user_id"], "roles": current_user["roles"]}

    # Endpoint requiring specific role
    @app.get("/admin-only")
    async def admin_only(current_user: dict = Depends(require_role("admin"))):
        return {"message": "admin access"}

    # Endpoint requiring one of multiple roles
    @app.get("/editor-or-admin")
    async def editor_or_admin(current_user: dict = Depends(require_role("editor", "admin"))):
        return {"message": "editor or admin access"}

    # Endpoint requiring specific permission
    @app.get("/read-permission")
    async def read_permission(current_user: dict = Depends(require_permission("read"))):
        return {"message": "read permission"}

    # Endpoint requiring all roles
    @app.get("/all-roles")
    async def all_roles_endpoint(
        current_user: dict = Depends(require_all_roles("admin", "editor"))
    ):
        return {"message": "all roles"}

    # Endpoint requiring all permissions
    @app.get("/all-permissions")
    async def all_permissions_endpoint(
        current_user: dict = Depends(require_all_permissions("read", "write"))
    ):
        return {"message": "all permissions"}

    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


class TestSecurityDecorators:
    """Test security decorators"""

    def test_get_jwt_auth(self, jwt_auth):
        """Test getting JWT auth instance"""
        retrieved_auth = get_jwt_auth()
        assert retrieved_auth is not None

    def test_public_endpoint_no_auth(self, client):
        """Test public endpoint without authentication"""
        response = client.get("/public")
        assert response.status_code == 200
        assert response.json() == {"message": "public"}

    def test_protected_endpoint_without_token(self, client):
        """Test protected endpoint without token"""
        response = client.get("/protected")
        assert response.status_code == 403

    def test_protected_endpoint_with_invalid_token(self, client):
        """Test protected endpoint with invalid token"""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, client, jwt_auth):
        """Test protected endpoint with valid token"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["user"],
        )

        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user123"
        assert data["roles"] == ["user"]

    def test_admin_only_endpoint_with_user_role(self, client, jwt_auth):
        """Test admin endpoint with user role"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["user"],
        )

        response = client.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_admin_only_endpoint_with_admin_role(self, client, jwt_auth):
        """Test admin endpoint with admin role"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["admin"],
        )

        response = client.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "admin access"}

    def test_editor_or_admin_with_editor_role(self, client, jwt_auth):
        """Test endpoint requiring editor or admin with editor role"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["editor"],
        )

        response = client.get(
            "/editor-or-admin",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "editor or admin access"}

    def test_editor_or_admin_with_admin_role(self, client, jwt_auth):
        """Test endpoint requiring editor or admin with admin role"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["admin"],
        )

        response = client.get(
            "/editor-or-admin",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    def test_editor_or_admin_with_user_role(self, client, jwt_auth):
        """Test endpoint requiring editor or admin with user role"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["user"],
        )

        response = client.get(
            "/editor-or-admin",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_permission_check_with_permission(self, client, jwt_auth):
        """Test permission check with required permission"""
        token = jwt_auth.create_access_token(
            subject="user123",
            permissions=["read", "write"],
        )

        response = client.get(
            "/read-permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "read permission"}

    def test_permission_check_without_permission(self, client, jwt_auth):
        """Test permission check without required permission"""
        token = jwt_auth.create_access_token(
            subject="user123",
            permissions=["write"],
        )

        response = client.get(
            "/read-permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_all_roles_with_all_roles(self, client, jwt_auth):
        """Test all roles requirement with all roles"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["admin", "editor", "user"],
        )

        response = client.get(
            "/all-roles",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "all roles"}

    def test_all_roles_with_missing_role(self, client, jwt_auth):
        """Test all roles requirement with missing role"""
        token = jwt_auth.create_access_token(
            subject="user123",
            roles=["admin"],
        )

        response = client.get(
            "/all-roles",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_all_permissions_with_all_permissions(self, client, jwt_auth):
        """Test all permissions requirement with all permissions"""
        token = jwt_auth.create_access_token(
            subject="user123",
            permissions=["read", "write", "delete"],
        )

        response = client.get(
            "/all-permissions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "all permissions"}

    def test_all_permissions_with_missing_permission(self, client, jwt_auth):
        """Test all permissions requirement with missing permission"""
        token = jwt_auth.create_access_token(
            subject="user123",
            permissions=["read"],
        )

        response = client.get(
            "/all-permissions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_bearer_token_format(self, client, jwt_auth):
        """Test Bearer token format"""
        token = jwt_auth.create_access_token(subject="user123")

        # Valid Bearer format
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Invalid Bearer format
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer"},
        )
        assert response.status_code == 403

    def test_empty_roles_and_permissions(self, client, jwt_auth):
        """Test with empty roles and permissions"""
        token = jwt_auth.create_access_token(subject="user123")

        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["roles"] == []
