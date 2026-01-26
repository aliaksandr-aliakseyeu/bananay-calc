"""Delivery list schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.delivery_point import DeliveryPointResponse


class DeliveryListCreate(BaseModel):
    """Schema for creating a delivery list."""

    name: str = Field(..., min_length=3, max_length=100, description="List name")
    description: str | None = Field(None, max_length=500, description="List description")
    is_default: bool = Field(False, description="Set as default list")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Основные клиенты",
            "description": "Список постоянных точек доставки",
            "is_default": True
        }
    })


class DeliveryListUpdate(BaseModel):
    """Schema for updating a delivery list."""

    name: str | None = Field(None, min_length=3, max_length=100, description="List name")
    description: str | None = Field(None, max_length=500, description="List description")
    is_default: bool | None = Field(None, description="Set as default list")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Обновлённое название",
            "description": "Новое описание"
        }
    })


class DeliveryListResponse(BaseModel):
    """Schema for delivery list response (list view)."""

    id: int
    name: str
    description: str | None = None
    is_default: bool
    items_count: int = Field(..., description="Number of points in the list")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "name": "Основные клиенты",
            "description": "Список постоянных точек доставки",
            "is_default": True,
            "items_count": 15,
            "created_at": "2026-01-20T10:00:00Z",
            "updated_at": "2026-01-20T12:00:00Z"
        }
    })


class DeliveryListItemCreate(BaseModel):
    """Schema for adding a point to a list."""

    delivery_point_id: int = Field(..., description="Delivery point ID")
    custom_name: str | None = Field(None, max_length=200, description="Custom name for this point")
    notes: str | None = Field(None, max_length=1000, description="Notes about this point")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "delivery_point_id": 42,
            "custom_name": "Мой основной склад",
            "notes": "Звонить за час до доставки"
        }
    })


class DeliveryListItemUpdate(BaseModel):
    """Schema for updating a list item."""

    custom_name: str | None = Field(None, max_length=200, description="Custom name")
    notes: str | None = Field(None, max_length=1000, description="Notes")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "custom_name": "Обновлённое название",
            "notes": "Новые заметки"
        }
    })


class DeliveryListItemResponse(BaseModel):
    """Schema for delivery list item response."""

    id: int
    custom_name: str | None = None
    notes: str | None = None
    created_at: datetime
    delivery_point: DeliveryPointResponse

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 10,
            "custom_name": "Мой основной склад",
            "notes": "Звонить за час",
            "created_at": "2026-01-20T10:00:00Z",
            "delivery_point": {
                "id": 42,
                "name": "Магазин Пятёрочка",
                "type": "Магазин",
                "address": "ул. Ленина, 42",
                "location": {
                    "type": "Point",
                    "coordinates": [39.723098, 43.585472]
                },
                "is_active": True
            }
        }
    })


class DeliveryListDetailResponse(BaseModel):
    """Schema for detailed delivery list response."""

    id: int
    name: str
    description: str | None = None
    is_default: bool
    items_count: int = Field(0, description="Number of items in the list")
    created_at: datetime
    updated_at: datetime
    items: list[DeliveryListItemResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "name": "Основные клиенты",
            "description": "Список постоянных точек",
            "is_default": True,
            "created_at": "2026-01-20T10:00:00Z",
            "updated_at": "2026-01-20T12:00:00Z",
            "items": [
                {
                    "id": 10,
                    "custom_name": "Мой основной склад",
                    "notes": "Звонить за час",
                    "created_at": "2026-01-20T10:00:00Z",
                    "delivery_point": {
                        "id": 42,
                        "name": "Магазин Пятёрочка",
                        "address": "ул. Ленина, 42",
                        "location": {
                            "type": "Point",
                            "coordinates": [39.723098, 43.585472]
                        }
                    }
                }
            ]
        }
    })


class CheckPointInListResponse(BaseModel):
    """Response for checking if a point is in a list."""

    in_list: bool
    item_id: int | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "in_list": True,
            "item_id": 10
        }
    })


class TogglePointRequest(BaseModel):
    """Request for toggling a point in a list."""

    delivery_point_id: int = Field(..., description="Delivery point ID")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "delivery_point_id": 42
        }
    })


class TogglePointResponse(BaseModel):
    """Response for toggling a point in a list."""

    action: str = Field(..., description="Action performed: 'added' or 'removed'")
    item_id: int | None = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "action": "added",
            "item_id": 10
        }
    })


class DeliveryPointInRadiusResponse(BaseModel):
    """Response for finding delivery points in radius."""

    delivery_point: DeliveryPointResponse
    distance_meters: float = Field(..., description="Distance from search point in meters")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "delivery_point": {
                "id": 42,
                "name": "Магазин Пятёрочка",
                "address": "ул. Ленина, 42",
                "location": {
                    "type": "Point",
                    "coordinates": [39.723098, 43.585472]
                }
            },
            "distance_meters": 150.5
        }
    })
