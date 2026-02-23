"""Pydantic schemas for driver location."""

from datetime import datetime

from pydantic import BaseModel, Field


class DriverLocationReport(BaseModel):
    """Payload for driver to report location."""

    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    accuracy: float | None = Field(None, description="Accuracy in meters (from Geolocation API)")
    device_info: str | None = Field(None, description="Optional device/browser info for debugging")


class DriverLocationResponse(BaseModel):
    """Response for driver location (for producer / SSE)."""

    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    accuracy: float | None = Field(None, description="Accuracy in meters")
    reported_at: datetime = Field(..., description="When location was reported")
    is_stale: bool = Field(False, description="True if location is older than configured threshold")


class DriverLocationConfigResponse(BaseModel):
    """Config for location tracking (client hints)."""

    send_interval_sec: int = Field(..., description="How often driver should POST location")
    poll_interval_sec: int = Field(..., description="How often to poll when using polling")
    stale_after_sec: int = Field(..., description="Consider location stale after this many seconds")
