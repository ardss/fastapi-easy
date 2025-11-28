"""Security data models for FastAPI-Easy"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user model"""

    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = Field(None, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """User creation model"""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """User update model"""

    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: Optional[List[str]] = None


class UserResponse(UserBase):
    """User response model"""

    id: int
    roles: List[str] = []
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TokenRequest(BaseModel):
    """Token request model"""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response model"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""

    refresh_token: str


class TokenPayload(BaseModel):
    """JWT token payload"""

    sub: str  # subject (user_id or username)
    roles: List[str] = []
    permissions: List[str] = []
    exp: int  # expiration time
    iat: int  # issued at
    type: str = "access"  # access or refresh


class RoleBase(BaseModel):
    """Base role model"""

    name: str = Field(..., min_length=3, max_length=50)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Role creation model"""

    permissions: List[str] = []


class RoleUpdate(BaseModel):
    """Role update model"""

    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleResponse(RoleBase):
    """Role response model"""

    id: int
    permissions: List[str] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PermissionBase(BaseModel):
    """Base permission model"""

    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    resource: str  # e.g., "items", "users"
    action: str  # e.g., "read", "create", "update", "delete"


class PermissionResponse(PermissionBase):
    """Permission response model"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Login response model"""

    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ErrorResponse(BaseModel):
    """Error response model"""

    error: str
    error_code: str
    message: str
    status_code: int
