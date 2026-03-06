"""Courier delivery task schemas."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CourierDeliveryTaskItem(BaseModel):
    """SKU item info within a courier task."""

    sku_name: str
    sku_code: str
    quantity: int


class CourierDeliveryTaskResponse(BaseModel):
    """Courier delivery task response."""

    task_id: int
    item_point_id: int
    order_id: int
    order_number: Optional[str]
    status: str
    dc_id: int
    dc_name: str
    dc_address: Optional[str]
    dc_lat: float
    dc_lon: float
    delivery_point_id: int
    delivery_point_name: Optional[str]
    delivery_point_address: Optional[str]
    delivery_point_lat: float
    delivery_point_lon: float
    sku_name: Optional[str]
    quantity: int
    taken_at: datetime
    in_transit_at: Optional[datetime]
    delivered_at: Optional[datetime]
    qr_scanned: bool
    qr_token: Optional[UUID] = None
    delivery_photo_media_id: Optional[UUID]
    # Map-compatible aliases
    from_address: Optional[str] = None
    from_lat: float = 0.0
    from_lon: float = 0.0
    to_address: Optional[str] = None
    to_lat: float = 0.0
    to_lon: float = 0.0
    sku_code: str = ""


class AvailableCourierTask(BaseModel):
    """Available task for courier (item_point in sorted_to_zone with no active courier task)."""

    item_point_id: int
    order_id: int
    order_number: Optional[str]
    dc_id: int
    dc_name: str
    dc_address: Optional[str]
    dc_lat: float
    dc_lon: float
    delivery_point_id: int
    delivery_point_name: Optional[str]
    delivery_point_address: Optional[str]
    delivery_point_lat: float
    delivery_point_lon: float
    sku_name: Optional[str]
    quantity: int
    # Frontend-compatible aliases
    task_id: int          # same as item_point_id
    status: str = "available"
    from_address: Optional[str] = None
    from_lat: float = 0.0
    from_lon: float = 0.0
    to_address: Optional[str] = None
    to_lat: float = 0.0
    to_lon: float = 0.0
    sku_code: str = ""


class ConfirmDeliveryRequest(BaseModel):
    """Request body for confirming delivery."""

    qr_token: UUID = Field(..., description="QR token scanned from the box")


class CompletedCourierTaskResponse(BaseModel):
    """Completed courier task for history view."""

    task_id: int
    order_id: int
    order_number: Optional[str]
    delivery_point_name: Optional[str]
    delivery_point_address: Optional[str]
    sku_name: Optional[str]
    quantity: int = 0
    delivered_at: Optional[datetime]
