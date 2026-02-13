"""Driver profile, vehicles, application, media schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DriverProfileUpdate(BaseModel):
    """Update driver profile (onboarding)."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    city: Optional[str] = Field(None, max_length=255)
    street: Optional[str] = Field(None, max_length=255)
    building: Optional[str] = Field(None, max_length=50)
    apartment: Optional[str] = Field(None, max_length=50)
    region_id: Optional[int] = None
    payout_account: Optional[str] = Field(None, max_length=500)


class DriverProfileResponse(BaseModel):
    """Driver profile + status for /me."""

    id: UUID
    phone_e164: str
    status: str
    full_name: Optional[str]
    city: Optional[str]
    street: Optional[str]
    building: Optional[str]
    apartment: Optional[str]
    region_id: Optional[int]
    payout_account: Optional[str]
    created_at: datetime
    updated_at: datetime
    can_submit: bool = False
    required_fields: dict[str, bool] = Field(default_factory=dict)
    required_document_kinds: list[str] = Field(
        default_factory=lambda: ["selfie", "license_front", "license_back"],
        description="Driver document kinds required for submit (STS is per vehicle)",
    )

    model_config = ConfigDict(from_attributes=True)


class DriverVehicleCreate(BaseModel):
    """Create driver vehicle."""

    plate_number: str = Field(..., min_length=1, max_length=20)
    model: Optional[str] = Field(None, max_length=255)
    capacity_kg: int = Field(..., ge=1, le=50000)
    capacity_m3: Decimal = Field(..., ge=0, le=1000)
    body_type: Optional[str] = Field(None, max_length=50)


class DriverVehicleUpdate(BaseModel):
    """Update driver vehicle."""

    plate_number: Optional[str] = Field(None, min_length=1, max_length=20)
    model: Optional[str] = Field(None, max_length=255)
    capacity_kg: Optional[int] = Field(None, ge=1, le=50000)
    capacity_m3: Optional[Decimal] = Field(None, ge=0, le=1000)
    body_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class DriverVehicleResponse(BaseModel):
    """Driver vehicle response."""

    id: UUID
    driver_id: UUID
    plate_number: str
    model: Optional[str]
    capacity_kg: int
    capacity_m3: Decimal
    body_type: Optional[str]
    photo_media_id: Optional[UUID] = None
    sts_media_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriverApplicationResponse(BaseModel):
    """Driver application status."""

    id: UUID
    driver_id: UUID
    status: str
    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reject_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriverMediaFileResponse(BaseModel):
    """Uploaded document/photo response."""

    id: UUID
    owner_type: str
    owner_id: UUID
    kind: str
    blob_path: str
    content_type: str
    size_bytes: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
