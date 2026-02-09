"""Delivery point suggestion schemas (producer-submitted points, pending moderation)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.delivery_point import GeoJSONPoint


class DeliveryPointSuggestionCreate(BaseModel):
    """Schema for creating a delivery point suggestion (producer)."""

    settlement_id: int = Field(..., description="Settlement ID (required)")
    name: str = Field(..., min_length=1, max_length=255, description="Name")
    type: str | None = Field(None, max_length=100, description="Type (e.g., 'Магазин', 'ПВЗ')")
    title: str | None = Field(None, description="Title / additional description")
    district_id: int | None = Field(None, description="District ID")
    address: str | None = Field(None, description="Address")
    address_comment: str | None = Field(None, description="Address comment")
    landmark: str | None = Field(None, max_length=255, description="Landmark")
    location: GeoJSONPoint = Field(..., description="Coordinates in GeoJSON format")
    category_id: int | None = Field(None, description="Category ID")
    subcategory_id: int | None = Field(None, description="Subcategory ID")
    phone: str | None = Field(None, description="Phone number(s)")
    mobile: str | None = Field(None, description="Mobile number(s)")
    email: str | None = Field(None, description="Email(s)")
    schedule: str | None = Field(None, description="Working schedule")
    tag_ids: list[int] = Field(default_factory=list, description="Tag IDs to assign")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "settlement_id": 1,
                "name": "Новый ПВЗ Озон",
                "type": "ПВЗ",
                "title": "Озон на Ленина",
                "address": "ул. Ленина, 42",
                "location": {"type": "Point", "coordinates": [39.723098, 43.585472]},
                "phone": "+7 (999) 123-45-67",
                "email": "pvz@example.com",
                "schedule": "Пн-Вс: 09:00-21:00",
                "tag_ids": [1, 2],
            }
        }
    )


class DeliveryPointSuggestionResponse(BaseModel):
    """Delivery point suggestion response (for list and detail)."""

    id: int
    name: str
    type: str | None = None
    title: str | None = None
    settlement_id: int
    district_id: int | None = None
    address: str | None = None
    address_comment: str | None = None
    landmark: str | None = None
    location: GeoJSONPoint
    category_id: int | None = None
    subcategory_id: int | None = None
    phone: str | None = None
    mobile: str | None = None
    email: str | None = None
    schedule: str | None = None
    tag_ids: list[int] = Field(default_factory=list, description="Assigned tag IDs")
    created_by_id: int = Field(..., description="User ID who submitted")
    created_at: datetime = Field(..., description="Submission time")

    model_config = ConfigDict(from_attributes=True)


class DeliveryPointSuggestionListResponse(BaseModel):
    """List of delivery point suggestions."""

    total: int = Field(..., description="Total count")
    items: list[DeliveryPointSuggestionResponse] = Field(..., description="Suggestions")
