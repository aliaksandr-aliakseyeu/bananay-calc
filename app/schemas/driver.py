"""Driver profile, vehicles, application, media schemas."""
from datetime import date, datetime
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
    brand: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=255)
    vin: Optional[str] = Field(None, min_length=11, max_length=17)
    year: Optional[int] = Field(None, ge=1950, le=2100)
    body_type_code: Optional[int] = None
    status: Optional[int] = None
    capabilities: "DriverVehicleCapabilitiesCreate"
    compliance: Optional["DriverVehicleComplianceCreate"] = None


class DriverVehicleCapabilitiesCreate(BaseModel):
    """Create operational capabilities for a vehicle."""

    payload_kg: int = Field(..., ge=1, le=50000)
    cargo_volume_m3: Decimal = Field(..., ge=0, le=1000)
    cargo_length_mm: Optional[int] = Field(None, ge=1)
    cargo_width_mm: Optional[int] = Field(None, ge=1)
    cargo_height_mm: Optional[int] = Field(None, ge=1)
    max_cargo_length_mm: Optional[int] = Field(None, ge=1)
    max_cargo_weight_kg: Optional[int] = Field(None, ge=1)
    banana_box_capacity: Optional[int] = Field(None, ge=0, le=32767)
    banana_box_capacity_bucket: Optional[int] = Field(None, ge=0, le=32767)
    has_refrigerator: bool = False
    min_temp_c: Optional[Decimal] = None
    max_temp_c: Optional[Decimal] = None
    supports_constant_temp: bool = False
    has_liftgate: bool = False
    has_ramp: bool = False
    has_straps: bool = False
    has_antislip_floor: bool = False
    allows_chilled_food: bool = False
    allows_frozen_food: bool = False
    allows_perishable_goods: bool = False
    allows_fmcg: bool = False
    allows_hazardous_goods: bool = False
    hazard_class: Optional[str] = Field(None, max_length=255)


class DriverVehicleComplianceCreate(BaseModel):
    """Create compliance details for a vehicle."""

    insurance_valid_until: Optional[date] = None
    last_inspection_date: Optional[date] = None
    sts_number: Optional[str] = Field(None, max_length=100)
    verification_status: int = 0
    verified_at: Optional[datetime] = None


class DriverVehicleCapabilitiesUpdate(BaseModel):
    """Expanded operational capabilities for a vehicle."""

    payload_kg: Optional[int] = Field(None, ge=1, le=50000)
    cargo_volume_m3: Optional[Decimal] = Field(None, ge=0, le=1000)
    cargo_length_mm: Optional[int] = Field(None, ge=1)
    cargo_width_mm: Optional[int] = Field(None, ge=1)
    cargo_height_mm: Optional[int] = Field(None, ge=1)
    max_cargo_length_mm: Optional[int] = Field(None, ge=1)
    max_cargo_weight_kg: Optional[int] = Field(None, ge=1)
    banana_box_capacity: Optional[int] = Field(None, ge=0, le=32767)
    banana_box_capacity_bucket: Optional[int] = Field(None, ge=0, le=32767)
    has_refrigerator: Optional[bool] = None
    min_temp_c: Optional[Decimal] = None
    max_temp_c: Optional[Decimal] = None
    supports_constant_temp: Optional[bool] = None
    has_liftgate: Optional[bool] = None
    has_ramp: Optional[bool] = None
    has_straps: Optional[bool] = None
    has_antislip_floor: Optional[bool] = None
    allows_chilled_food: Optional[bool] = None
    allows_frozen_food: Optional[bool] = None
    allows_perishable_goods: Optional[bool] = None
    allows_fmcg: Optional[bool] = None
    allows_hazardous_goods: Optional[bool] = None
    hazard_class: Optional[str] = Field(None, max_length=255)


class DriverVehicleComplianceUpdate(BaseModel):
    """Compliance and verification details for a vehicle."""

    insurance_valid_until: Optional[date] = None
    last_inspection_date: Optional[date] = None
    sts_number: Optional[str] = Field(None, max_length=100)
    verification_status: Optional[int] = None
    verified_at: Optional[datetime] = None


class DriverVehicleUpdate(BaseModel):
    """Update driver vehicle."""

    plate_number: Optional[str] = Field(None, min_length=1, max_length=20)
    brand: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=255)
    vin: Optional[str] = Field(None, min_length=11, max_length=17)
    year: Optional[int] = Field(None, ge=1950, le=2100)
    body_type_code: Optional[int] = None
    status: Optional[int] = None
    capabilities: Optional[DriverVehicleCapabilitiesUpdate] = None
    compliance: Optional[DriverVehicleComplianceUpdate] = None


class DriverVehicleCapabilitiesResponse(BaseModel):
    """Operational capabilities for a vehicle."""

    vehicle_id: UUID
    payload_kg: int
    cargo_volume_m3: Optional[Decimal]
    cargo_length_mm: Optional[int]
    cargo_width_mm: Optional[int]
    cargo_height_mm: Optional[int]
    max_cargo_length_mm: Optional[int]
    max_cargo_weight_kg: Optional[int]
    banana_box_capacity: Optional[int]
    banana_box_capacity_bucket: Optional[int]
    has_refrigerator: bool
    min_temp_c: Optional[Decimal]
    max_temp_c: Optional[Decimal]
    supports_constant_temp: bool
    has_liftgate: bool
    has_ramp: bool
    has_straps: bool
    has_antislip_floor: bool
    allows_chilled_food: bool
    allows_frozen_food: bool
    allows_perishable_goods: bool
    allows_fmcg: bool
    allows_hazardous_goods: bool
    hazard_class: Optional[str]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriverVehicleComplianceResponse(BaseModel):
    """Compliance and verification details for a vehicle."""

    vehicle_id: UUID
    insurance_valid_until: Optional[date]
    last_inspection_date: Optional[date]
    sts_number: Optional[str]
    verification_status: int
    verified_at: Optional[datetime]
    verification_reject_reason: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriverVehicleResponse(BaseModel):
    """Driver vehicle response."""

    id: UUID
    driver_id: UUID
    plate_number: str
    plate_number_normalized: str
    brand: Optional[str]
    model: Optional[str]
    vin: Optional[str]
    year: Optional[int]
    body_type_code: Optional[int]
    status: int
    photo_media_id: Optional[UUID] = None
    sts_media_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    capabilities: Optional[DriverVehicleCapabilitiesResponse] = None
    compliance: Optional[DriverVehicleComplianceResponse] = None

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
