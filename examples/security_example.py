"""FastAPI-Easy Security Example"""

import os
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from fastapi_easy import CRUDRouter
from fastapi_easy.security import (
    JWTAuth,
    PasswordManager,
    SecurityMiddleware,
    SecurityLogger,
    SecurityEventType,
    SecurityValidator,
)
from fastapi_easy.security.models import (
    UserCreate,
    UserResponse,
    TokenResponse,
    LoginResponse,
)
from fastapi_easy.backends.sqlalchemy import SQLAlchemyAdapter
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

# Initialize FastAPI app
app = FastAPI(title="Secure API Example", version="1.0.0")

# Database setup (using SQLite for example)
SQLALCHEMY_DATABASE_URL = "sqlite:///./secure_example.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize security components
jwt_auth = JWTAuth(
    secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production"),
    algorithm="HS256",
    access_token_expire_minutes=15,
    refresh_token_expire_days=7,
    issuer="secure-api-example",
    audience="api-users",
)

password_manager = PasswordManager(
    algorithm="argon2",  # Use Argon2id for production
    argon2_time_cost=3,
    argon2_memory_cost=65536,
    argon2_parallelism=4,
)

security_logger = SecurityLogger(
    log_file="logs/security.log",
    enable_json_format=True,
)

# Initialize adapters
user_adapter = SQLAlchemyAdapter(User, SessionLocal)

# Initialize CRUD router with security
secure_user_router = CRUDRouter(
    schema=UserResponse,
    adapter=user_adapter,
    prefix="/users",
    tags=["users"],
    create_schema=UserCreate,
)

# Add security middleware
app.add_middleware(
    SecurityMiddleware,
    jwt_auth=jwt_auth,
    rate_limit_per_minute=60,
    rate_limit_per_hour=1000,
    max_request_size=10 * 1024 * 1024,  # 10MB
    require_auth_paths=["/api/", "/users/", "/admin/"],
    skip_auth_paths=["/auth/login", "/auth/register", "/health", "/docs"],
    enable_input_validation=True,
    enable_cors=True,
    allowed_origins=["http://localhost:3000"],  # Configure for your frontend
)

# HTTP Bearer for token authentication
bearer = HTTPBearer()

# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

class SecureDataResponse(BaseModel):
    message: str
    user_id: str
    timestamp: datetime

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    """Get current user from JWT token"""
    try:
        # Verify token with client IP for rate limiting
        payload = jwt_auth.verify_token(credentials.credentials)
        return payload
    except Exception as e:
        security_logger.log_authentication_event(
            SecurityEventType.TOKEN_INVALID,
            user_id="unknown",
            ip_address="unknown",
            success=False,
            failure_reason=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Admin role check
async def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role"""
    if "admin" not in current_user.get("roles", []):
        security_logger.log_authorization_event(
            SecurityEventType.PERMISSION_DENIED,
            user_id=current_user.get("sub"),
            resource="admin_endpoint",
            action="access",
            ip_address="unknown",
            granted=False,
            reason="Admin role required"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

# Routes
@app.post("/auth/register", response_model=UserResponse)
async def register(user_data: RegisterRequest):
    """Register a new user with security checks"""
    try:
        # Validate input with security validator
        validated_data = SecurityValidator.comprehensive_validation(user_data.dict())

        # Check if user already exists
        async with SessionLocal() as session:
            existing_user = session.query(User).filter(
                (User.username == validated_data["username"]) |
                (User.email == validated_data["email"])
            ).first()

            if existing_user:
                security_logger.log_security_violation(
                    SecurityEventType.SECURITY_POLICY_VIOLATION,
                    f"Duplicate user registration attempt: {validated_data['username']}",
                    ip_address="client_ip",  # Would get from request
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already exists"
                )

            # Hash password with strength checking
            hashed_password = password_manager.hash_password(
                validated_data["password"],
                check_strength=True
            )

            # Create user
            user = User(
                username=validated_data["username"],
                email=validated_data["email"],
                hashed_password=hashed_password,
                full_name=validated_data.get("full_name"),
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            security_logger.log_authentication_event(
                SecurityEventType.LOGIN_SUCCESS,
                user_id=str(user.id),
                ip_address="client_ip",  # Would get from request
                success=True,
                additional_info={"registration": True}
            )

            return UserResponse.from_orm(user)

    except ValueError as e:
        security_logger.log_security_violation(
            SecurityEventType.INPUT_VALIDATION_FAILED,
            f"Invalid registration data: {str(e)}",
            ip_address="client_ip",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post("/auth/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Login user with rate limiting and security checks"""
    try:
        # Validate input
        validated_data = SecurityValidator.comprehensive_validation(login_data.dict())

        # Get user from database
        async with SessionLocal() as session:
            user = session.query(User).filter(
                User.username == validated_data["username"]
            ).first()

            if not user or not user.is_active:
                security_logger.log_authentication_event(
                    SecurityEventType.LOGIN_FAILURE,
                    user_id=validated_data["username"],
                    ip_address="client_ip",
                    success=False,
                    failure_reason="Invalid credentials or inactive user"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # Verify password with rate limiting
            password_valid = password_manager.verify_password(
                validated_data["password"],
                user.hashed_password,
                identifier=validated_data["username"],
                rate_limit=True
            )

            if not password_valid:
                security_logger.log_authentication_event(
                    SecurityEventType.LOGIN_FAILURE,
                    user_id=str(user.id),
                    ip_address="client_ip",
                    success=False,
                    failure_reason="Invalid password"
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # Create tokens
            roles = ["admin"] if user.is_admin else ["user"]
            access_token = jwt_auth.create_access_token(
                subject=str(user.id),
                roles=roles,
                client_identifier="client_ip"  # Would get from request
            )
            refresh_token = jwt_auth.create_refresh_token(
                subject=str(user.id),
                client_identifier="client_ip"
            )

            security_logger.log_authentication_event(
                SecurityEventType.LOGIN_SUCCESS,
                user_id=str(user.id),
                ip_address="client_ip",
                success=True,
                additional_info={"roles": roles}
            )

            return LoginResponse(
                user=UserResponse.from_orm(user),
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=jwt_auth.access_token_expire_minutes * 60
            )

    except HTTPException:
        raise
    except Exception as e:
        security_logger.log_security_violation(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            f"Login error: {str(e)}",
            ip_address="client_ip",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Logout user and blacklist token"""
    try:
        # In a real implementation, you'd get the token from the request
        # and add it to the blacklist
        security_logger.log_authentication_event(
            SecurityEventType.LOGOUT,
            user_id=current_user.get("sub"),
            ip_address="client_ip",
            success=True
        )
        return {"message": "Successfully logged out"}
    except Exception as e:
        security_logger.log_security_violation(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            f"Logout error: {str(e)}",
            ip_address="client_ip",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )

@app.get("/api/secure-data", response_model=SecureDataResponse)
async def get_secure_data(current_user: dict = Depends(get_current_user)):
    """Example endpoint requiring authentication"""
    security_logger.log_data_access(
        user_id=current_user.get("sub"),
        resource_type="secure_data",
        resource_id=None,
        action="read",
        ip_address="client_ip",
        is_sensitive=True
    )

    return SecureDataResponse(
        message="This is secure data accessible only to authenticated users",
        user_id=current_user.get("sub"),
        timestamp=datetime.now(timezone.utc)
    )

@app.get("/api/admin/dashboard")
async def admin_dashboard(current_user: dict = Depends(require_admin)):
    """Example admin-only endpoint"""
    security_logger.log_data_access(
        user_id=current_user.get("sub"),
        resource_type="admin_dashboard",
        resource_id=None,
        action="read",
        ip_address="client_ip",
        is_sensitive=True
    )

    return {
        "message": "Admin dashboard",
        "stats": {
            "total_users": 100,
            "active_users": 75,
            "security_score": 95,
        }
    }

@app.post("/api/validate-input")
async def validate_input_endpoint(data: dict):
    """Example endpoint demonstrating input validation"""
    try:
        # Validate and sanitize input
        sanitized_data = SecurityValidator.comprehensive_validation(data)

        security_logger.log_security_event(
            SecurityEventType.INPUT_VALIDATION_PASSED,
            "Input validation successful",
            user_id="unknown",
            ip_address="client_ip",
            details={"input_size": len(str(data))}
        )

        return {"message": "Input validated successfully", "data": sanitized_data}

    except Exception as e:
        security_logger.log_security_violation(
            SecurityEventType.INPUT_VALIDATION_FAILED,
            f"Input validation failed: {str(e)}",
            ip_address="client_ip",
            request_data=data
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint (no authentication required)"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

# Include secure CRUD router
app.include_router(secure_user_router)

if __name__ == "__main__":
    import uvicorn

    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Run with SSL in production
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        # Uncomment for production:
        # ssl_keyfile="path/to/key.pem",
        # ssl_certfile="path/to/cert.pem"
    )