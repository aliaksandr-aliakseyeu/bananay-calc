"""Authentication schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.enums import OnboardingStatus, UserRole


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
    onboarding_status: OnboardingStatus
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
    """Producer registration schema (Step 1)."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    company_name: str = Field(..., min_length=1, max_length=500)


class ProducerProfileComplete(BaseModel):
    """Producer profile completion schema (Step 2)."""

    contact_person: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(..., min_length=10, max_length=20)
    company_inn: Optional[str] = Field(None, min_length=10, max_length=12)
    company_address: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = None
    website: Optional[str] = Field(None, max_length=500)


class EmailVerificationRequest(BaseModel):
    """Email verification request schema."""

    token: str


class OnboardingStatusResponse(BaseModel):
    """Onboarding status response schema."""

    onboarding_status: OnboardingStatus
    email_verified: bool
    profile_completed: bool
    is_approved: bool
    required_fields: dict[str, bool]


class ChangePasswordRequest(BaseModel):
    """Change password request schema."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class ProducerStatistics(BaseModel):
    """Producer dashboard statistics schema."""

    delivery_lists_count: int
    product_skus_count: int
    delivery_templates_count: int
    total_orders_count: int
    active_orders_count: int


class DriverRequestOtp(BaseModel):
    """Request OTP for driver login."""

    phone_e164: str = Field(..., min_length=10, max_length=20)


class DriverVerifyOtp(BaseModel):
    """Verify OTP and get driver tokens."""

    phone_e164: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=10)


class DriverVerifyOtpResponse(BaseModel):
    """Response after driver OTP verification."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool = False
