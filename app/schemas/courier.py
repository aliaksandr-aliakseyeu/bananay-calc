"""Courier profile, vehicles, application, media schemas."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CourierProfileUpdate(BaseModel):
    """Update courier profile (onboarding)."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    city: Optional[str] = Field(None, max_length=255)
    street: Optional[str] = Field(None, max_length=255)
    building: Optional[str] = Field(None, max_length=50)
    apartment: Optional[str] = Field(None, max_length=50)
    region_id: Optional[int] = None
    payout_account: Optional[str] = Field(None, max_length=500)


class CourierProfileResponse(BaseModel):
    """Courier profile + status for /me."""

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
        description="Courier document kinds required for submit (STS is per vehicle)",
    )

    model_config = ConfigDict(from_attributes=True)


class CourierVehicleCreate(BaseModel):
    """Create courier vehicle."""

    plate_number: str = Field(..., min_length=1, max_length=20)
    model: Optional[str] = Field(None, max_length=255)
    max_weight_kg: int = Field(..., ge=1, le=50000)
    vehicle_type: Optional[str] = Field(None, max_length=50)


class CourierVehicleUpdate(BaseModel):
    """Update courier vehicle."""

    plate_number: Optional[str] = Field(None, min_length=1, max_length=20)
    model: Optional[str] = Field(None, max_length=255)
    max_weight_kg: Optional[int] = Field(None, ge=1, le=50000)
    vehicle_type: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class CourierVehicleResponse(BaseModel):
    """Courier vehicle response."""

    id: UUID
    courier_id: UUID
    plate_number: str
    model: Optional[str]
    max_weight_kg: int
    vehicle_type: Optional[str]
    photo_media_id: Optional[UUID] = None
    sts_media_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def remap_db_fields(cls, v: Any) -> Any:
        if hasattr(v, 'capacity_kg'):
            return {
                'id': v.id,
                'courier_id': v.courier_id,
                'plate_number': v.plate_number,
                'model': v.model,
                'max_weight_kg': v.capacity_kg,
                'vehicle_type': v.body_type,
                'photo_media_id': v.photo_media_id,
                'sts_media_id': v.sts_media_id,
                'is_active': v.is_active,
                'created_at': v.created_at,
                'updated_at': v.updated_at,
            }
        return v


class CourierApplicationResponse(BaseModel):
    """Courier application status."""

    id: UUID
    courier_id: UUID
    status: str
    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reject_reason: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourierMediaFileResponse(BaseModel):
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
