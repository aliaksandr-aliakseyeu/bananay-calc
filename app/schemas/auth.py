"""Authentication schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.enums import UserRole


class Token(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserLogin(BaseModel):
    """User login request schema."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class UserResponse(BaseModel):
    """User response schema."""

    id: int
    email: str
    role: UserRole
    is_active: bool
    email_verified: bool
    is_approved: bool
    is_rejected: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """User creation schema (for admin script)."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.PRODUCER


class ProducerProfileCreate(BaseModel):
    """Producer profile creation schema."""

    company_name: str = Field(..., min_length=1, max_length=500)
    company_inn: Optional[str] = Field(None, min_length=10, max_length=12)
    contact_person: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    company_address: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = None
    website: Optional[str] = Field(None, max_length=500)


class ProducerProfileUpdate(BaseModel):
    """Producer profile update schema."""

    company_name: Optional[str] = Field(None, min_length=1, max_length=500)
    company_inn: Optional[str] = Field(None, min_length=10, max_length=12)
    contact_person: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    company_address: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = None
    website: Optional[str] = Field(None, max_length=500)


class ProducerProfileResponse(BaseModel):
    """Producer profile response schema."""

    id: int
    user_id: int
    company_name: str
    company_inn: Optional[str]
    contact_person: Optional[str]
    phone: Optional[str]
    company_address: Optional[str]
    description: Optional[str]
    website: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProducerRegistration(BaseModel):
    """Producer registration schema."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: str = Field(..., min_length=1, max_length=500)
    company_inn: Optional[str] = Field(None, min_length=10, max_length=12)
    contact_person: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    company_address: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = None
    website: Optional[str] = Field(None, max_length=500)
