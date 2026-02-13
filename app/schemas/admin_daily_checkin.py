"""Admin daily check-in moderation API schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CheckInPhotoResponse(BaseModel):
    """Single photo in check-in (admin list/detail)."""

    kind: str
    media_id: str


class DriverShortInfo(BaseModel):
    """Short driver info for check-in list/detail."""

    id: str
    phone_e164: str
    full_name: Optional[str]


class VehicleShortInfo(BaseModel):
    """Short vehicle info for check-in list/detail."""

    id: str
    plate_number: str
    model: Optional[str]


class CheckInListItem(BaseModel):
    """Check-in list item for admin."""

    id: str
    driver: DriverShortInfo
    vehicle: VehicleShortInfo
    check_date: str
    status: str
    completed_at: Optional[datetime]
    photos_count: int


class CheckInDetailResponse(BaseModel):
    """Full check-in detail for admin."""

    id: str
    driver: DriverShortInfo
    vehicle: VehicleShortInfo
    check_date: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    latitude: Optional[float]
    longitude: Optional[float]
    notes: Optional[str]
    reviewed_at: Optional[datetime]
    reject_reason: Optional[str]
    photos: list[CheckInPhotoResponse]


class RejectRequest(BaseModel):
    """Reject check-in request body."""

    reason: str
