# Testing Best Practices

This guide covers testing best practices for FastAPI-Easy.

## Testing Strategy

### Test Pyramid
- **Unit Tests (70%)**: Fast, isolated tests for individual functions
- **Integration Tests (20%)**: Test component interactions
- **End-to-End Tests (10%) Test complete user workflows

### Test Organization

```
tests/
├── unit/           # Unit tests (fast, isolated)
├── integration/    # Integration tests (requires external resources)
├── e2e/           # End-to-end tests (slow, full flow)
├── performance/   # Performance and load tests
└── conftest.py    # Shared fixtures and configuration
```

## Essential pytest Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--cov=src/fastapi_easy",
    "--cov-report=html:htmlcov",
    "--cov-report=term-missing",
    "--cov-fail-under=85",
    "-v",
    "--strict-markers",
    "--tb=short"
]
asyncio_mode = "auto"
markers = [
    "unit: mark test as unit test (fast, isolated)",
    "integration: mark test as integration test",
    "e2e: mark test as end-to-end test",
    "performance: mark test as performance test",
    "slow: mark test as slow to run",
    "requires_db: mark test as requiring database",
]
```

## Key Fixtures

### Basic Test Fixtures

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app

@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def db_session():
    """Create database session for testing."""
    # Implementation depends on your database setup
    async with create_test_engine() as engine:
        async with AsyncSession(engine) as session:
            yield session
            await session.rollback()
```

### Test Data Factory Pattern

```python
# tests/factories.py
import factory
from faker import Faker

fake = Faker()

class UserFactory(factory.Factory):
    """Factory for creating test users."""

    class Meta:
        model = User

    email = factory.Faker('email')
    username = factory.Faker('user_name')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True

# Usage in tests
def test_user_creation():
    user = UserFactory()
    assert user.email is not None
    assert user.is_active is True
```

## Unit Testing

### Example Unit Test

```python
# tests/unit/test_user_service.py
import pytest
from unittest.mock import AsyncMock, patch

from app.services.user_service import UserService
from app.core.errors import AppError, ErrorCode

class TestUserService:
    """Test cases for UserService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return UserService()

    @pytest.mark.asyncio
    async def test_create_user_success(self, service):
        """Test successful user creation."""
        # Arrange
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123"
        }

        with patch('app.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"

            with patch.object(service, 'save_user') as mock_save:
                mock_user = AsyncMock()
                mock_user.id = 1
                mock_user.email = user_data["email"]
                mock_save.return_value = mock_user

                # Act
                result = await service.create_user(user_data)

                # Assert
                assert result.id == 1
                assert result.email == user_data["email"]
                mock_hash.assert_called_once_with("securepassword123")
                mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self, service):
        """Test user creation with duplicate email."""
        # Arrange
        user_data = {
            "email": "existing@example.com",
            "username": "newuser",
            "password": "password123"
        }

        with patch.object(service, 'get_user_by_email') as mock_get:
            mock_get.return_value = AsyncMock()  # User exists

            # Act & Assert
            with pytest.raises(AppError) as exc_info:
                await service.create_user(user_data)

            assert exc_info.value.code == ErrorCode.CONFLICT
            assert "already exists" in exc_info.value.message
            mock_get.assert_called_once_with("existing@example.com")
```

### Testing Async Functions

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test async function with mocking."""
    with patch('app.module.httpx.AsyncClient.get') as mock_get:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_get.return_value = mock_response

        result = await fetch_data("https://api.example.com")

        assert result["status"] == "success"
        mock_get.assert_called_once()
```

## Integration Testing

### API Integration Tests

```python
# tests/integration/test_user_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.integration
class TestUserAPI:
    """Integration tests for User API endpoints."""

    @pytest.mark.asyncio
    async def test_create_user_endpoint(self, async_client: AsyncClient):
        """Test user creation endpoint."""
        # Arrange
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepassword123",
            "first_name": "New",
            "last_name": "User"
        }

        # Act
        response = await async_client.post("/api/users", json=user_data)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "password" not in data  # Password should not be returned
        assert "id" in data

    @pytest.mark.asyncio
    async def test_get_user_authenticated(self, async_client: AsyncClient, test_user):
        """Test getting user with authentication."""
        # Arrange
        token = create_access_token(data={"sub": str(test_user.id)})
        headers = {"Authorization": f"Bearer {token}"}

        # Act
        response = await async_client.get(
            f"/api/users/{test_user.id}",
            headers=headers
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_unauthorized(self, async_client: AsyncClient):
        """Test getting user without authentication."""
        # Act
        response = await async_client.get("/api/users/1")

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "UNAUTHORIZED"
```

## End-to-End Testing

### Workflow Tests

```python
@pytest.mark.e2e
@pytest.mark.slow
class TestUserRegistrationWorkflow:
    """End-to-end tests for user registration workflow."""

    @pytest.mark.asyncio
    async def test_complete_registration_workflow(self, async_client: AsyncClient):
        """Test complete user registration and login workflow."""
        # Step 1: Register new user
        registration_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User"
        }

        reg_response = await async_client.post("/api/auth/register", json=registration_data)
        assert reg_response.status_code == 201

        # Step 2: Login with new credentials
        login_data = {
            "username": registration_data["email"],
            "password": registration_data["password"]
        }

        login_response = await async_client.post("/api/auth/login", json=login_data)
        assert login_response.status_code == 200
        login_data = login_response.json()
        assert "access_token" in login_data

        # Step 3: Access protected endpoint
        headers = {"Authorization": f"Bearer {login_data['access_token']}"}
        profile_response = await async_client.get("/api/auth/me", headers=headers)
        assert profile_response.status_code == 200

        profile_data = profile_response.json()
        assert profile_data["email"] == registration_data["email"]
```

## Best Practices

### 1. Test Naming

```python
# Good: Descriptive test names
def test_create_user_should_return_201_when_valid_data_provided():
    """Clear description of what should happen."""
    pass

# Good: Parameterized tests
@pytest.mark.parametrize("invalid_email", [
    "invalid",
    "@domain.com",
    "user@",
])
def test_create_user_should_return_400_when_invalid_email(invalid_email):
    """Test with multiple invalid inputs."""
    pass
```

### 2. Test Organization

```python
class TestUserService:
    """Group related tests in a class."""

    @pytest.fixture
    def service(self):
        """Create service instance for all tests in class."""
        return UserService()

    def test_create_user_success(self, service):
        """Test successful user creation."""
        pass

    def test_create_user_duplicate_email(self, service):
        """Test duplicate email handling."""
        pass
```

### 3. Assertion Strategy

```python
# Good: Specific assertions
assert response.status_code == 201
assert response.json()["email"] == user_data["email"]
assert "password" not in response.json()

# Good: Use helper functions for common assertions
def assert_user_response(response_data, expected_user):
    """Assert user response has expected fields."""
    assert response_data["id"] == expected_user.id
    assert response_data["email"] == expected_user.email
    assert "password" not in response_data
```

### 4. Test Independence

```python
# Each test should be independent
@pytest.fixture(autouse=True)
async def cleanup_test_data(db_session):
    """Clean up test data after each test."""
    yield
    # Clean up created data
    await db_session.execute("DELETE FROM users WHERE email LIKE 'test%'")
    await db_session.commit()
```

### 5. Mocking Strategy

```python
# Mock external dependencies
@pytest.fixture
def mock_email_service():
    """Mock email service for testing."""
    with patch('app.services.email_service.send_email') as mock_send:
        mock_send.return_value = True
        yield mock_send

def test_user_registration_sends_email(mock_email_service):
    """Test that user registration sends welcome email."""
    # Test implementation
    mock_email_service.assert_called_once_with(
        to="user@example.com",
        subject="Welcome!",
        template="welcome"
    )
```

### 6. Parameterized Testing

```python
@pytest.mark.parametrize("input_data,expected_status", [
    ({"email": "valid@example.com", "password": "valid123"}, 201),
    ({"email": "invalid", "password": "valid123"}, 400),
    ({"email": "valid@example.com", "password": ""}, 400),
])
def test_create_user_with_various_inputs(input_data, expected_status):
    """Test user creation with various input combinations."""
    response = client.post("/api/users", json=input_data)
    assert response.status_code == expected_status
```

### 7. Error Testing

```python
def test_error_handling():
    """Test that errors are properly handled."""
    with pytest.raises(AppError) as exc_info:
        # Code that should raise AppError
        pass

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert "expected message" in str(exc_info.value)
```

## Running Tests

### Development

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/fastapi_easy --cov-report=html

# Run specific test file
pytest tests/unit/test_user_service.py

# Run specific marker
pytest -m unit

# Run in parallel
pytest -n auto

# Run only fast tests
pytest -m "not slow"
```

### Continuous Integration

```bash
# CI command with all checks
pytest --cov=src/fastapi_easy --cov-fail-under=85 -v
mypy src/
ruff check src/
bandit -r src/
```

## Test Data Management

### Test Database

```python
@pytest.fixture(scope="session")
async def test_db():
    """Create test database for all tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()
```

### Factory Patterns

```python
# Use factories for consistent test data
def test_user_with_posts():
    """Test user with multiple posts."""
    user = UserFactory()
    PostFactory.create_batch(3, user=user)

    assert len(user.posts) == 3
```

This testing guide provides essential patterns and best practices for maintaining high-quality tests throughout the FastAPI-Easy project.