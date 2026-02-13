"""Driver daily check-in (EKF) API schemas."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class CheckInPhotoResponse(BaseModel):
    """Single photo in check-in response (driver)."""

    kind: str
    media_id: str
    uploaded_at: datetime


class CheckInResponse(BaseModel):
    """Daily check-in response for driver."""

    id: str
    vehicle_id: str
    check_date: date
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    photos: list[CheckInPhotoResponse]
    missing_photos: list[str]
    reject_reason: Optional[str] = None


class CheckInStatusResponse(BaseModel):
    """Status of today's check-in."""

    has_checkin: bool
    is_complete: bool
    checkin: Optional[CheckInResponse]


class StartCheckInRequest(BaseModel):
    """Start daily check-in request."""

    vehicle_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
