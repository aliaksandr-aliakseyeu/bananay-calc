"""Delivery point schemas."""
from pydantic import BaseModel, ConfigDict, Field


class BoundingBox(BaseModel):
    """Bounding box for filtering by coordinates."""

    min_lng: float = Field(..., description="Minimum longitude (western boundary)")
    min_lat: float = Field(..., description="Minimum latitude (southern boundary)")
    max_lng: float = Field(..., description="Maximum longitude (eastern boundary)")
    max_lat: float = Field(..., description="Maximum latitude (northern boundary)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "min_lng": 39.7,
            "min_lat": 43.5,
            "max_lng": 39.8,
            "max_lat": 43.6
        }
    })


class DeliveryPointSearchRequest(BaseModel):
    """Request schema for delivery points search."""

    region_id: int = Field(..., description="Region ID", examples=[1])
    only_in_sectors: bool = Field(
        False,
        description="true = only points in sectors, false = all region points"
    )
    search: str | None = Field(
        None,
        min_length=3,
        max_length=100,
        description=(
            "Search by name (autocomplete). Minimum 3 characters. "
            "Supports prefix search and fuzzy search with typos."
        )
    )
    bbox: BoundingBox | None = Field(
        None,
        description="Filter by coordinate bounding box (optional)"
    )
    tag_ids: list[int] | None = Field(
        None,
        description="Filter by tags (optional, OR logic)"
    )
    limit: int | None = Field(
        None,
        ge=1,
        le=50,
        description=(
            "Maximum number of results. "
            "⚠️ Applied ONLY when using 'search' parameter (autocomplete). "
            "Default 15, maximum 50. "
            "Without 'search' all found points are returned. "
            "In the future, autocomplete should be moved to a separate endpoint."
        )
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "region_id": 1,
            "only_in_sectors": False,
            "search": "маг",
            "bbox": {
                "min_lng": 39.7,
                "min_lat": 43.5,
                "max_lng": 39.8,
                "max_lat": 43.6
            },
            "tag_ids": [1, 2, 3],
            "limit": 10
        }
    })


class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""

    type: str = Field(default="Point", description="Geometry type")
    coordinates: list[float] = Field(
        ...,
        description="Point coordinates [longitude, latitude]"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "type": "Point",
            "coordinates": [39.723098, 43.585472]
        }
    })


class DeliveryPointResponse(BaseModel):
    """Delivery point response schema."""

    id: int
    name: str
    type: str | None = Field(None, description="Delivery point type")
    title: str | None = Field(None, description="Title / additional description")
    address: str | None = Field(None, description="Address")
    address_comment: str | None = Field(None, description="Address comment")
    landmark: str | None = Field(None, description="Landmark")
    location: GeoJSONPoint = Field(..., description="Coordinates in GeoJSON format")
    phone: str | None = Field(None, description="Phone number(s)")
    mobile: str | None = Field(None, description="Mobile number(s)")
    email: str | None = Field(None, description="Email(s)")
    schedule: str | None = Field(None, description="Working schedule")
    is_active: bool = Field(..., description="Is delivery point active")

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "name": "Магазин Пятёрочка",
            "type": "Магазин",
            "title": "Пятёрочка на Краснофлотской",
            "address": "село Казачий Брод, Краснофлотская улица, 27",
            "address_comment": "Вход со стороны парковки",
            "landmark": "Рядом с автобусной остановкой",
            "location": {
                "type": "Point",
                "coordinates": [39.723098, 43.585472]
            },
            "phone": "+7 (862) 123-45-67",
            "mobile": "+7 (999) 123-45-67",
            "email": "shop@example.com",
            "schedule": "Пн-Вс: 08:00-22:00",
            "is_active": True
        }
    })


class DeliveryPointSearchResponse(BaseModel):
    """Search response with total count and items."""

    total: int = Field(..., description="Total number of found delivery points")
    items: list[DeliveryPointResponse] = Field(..., description="List of delivery points")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total": 150,
            "items": [
                {
                    "id": 1,
                    "name": "Магазин Пятёрочка",
                    "type": "Магазин",
                    "title": "Пятёрочка на Краснофлотской",
                    "address": "село Казачий Брод, Краснофлотская улица, 27",
                    "address_comment": "Вход со стороны парковки",
                    "landmark": "Рядом с автобусной остановкой",
                    "location": {
                        "type": "Point",
                        "coordinates": [39.723098, 43.585472]
                    },
                    "phone": "+7 (862) 123-45-67",
                    "mobile": "+7 (999) 123-45-67",
                    "email": "shop@example.com",
                    "schedule": "Пн-Вс: 08:00-22:00",
                    "is_active": True
                }
            ]
        }
    })


class DeliveryPointCreate(BaseModel):
    """Schema for creating a delivery point."""

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
    is_active: bool = Field(True, description="Is delivery point active")
    tag_ids: list[int] = Field(default_factory=list, description="Tag IDs to assign")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "settlement_id": 1,
            "name": "Новый ПВЗ Озон",
            "type": "ПВЗ",
            "title": "Озон на Ленина",
            "address": "ул. Ленина, 42",
            "location": {
                "type": "Point",
                "coordinates": [39.723098, 43.585472]
            },
            "phone": "+7 (999) 123-45-67",
            "email": "pvz@example.com",
            "schedule": "Пн-Вс: 09:00-21:00",
            "is_active": True,
            "tag_ids": [1, 2]
        }
    })


class DeliveryPointUpdate(BaseModel):
    """Schema for updating a delivery point. All fields are optional."""

    settlement_id: int | None = Field(None, description="Settlement ID")
    name: str | None = Field(None, min_length=1, max_length=255, description="Name")
    type: str | None = Field(None, max_length=100, description="Type")
    title: str | None = Field(None, description="Title / additional description")
    district_id: int | None = Field(None, description="District ID")
    address: str | None = Field(None, description="Address")
    address_comment: str | None = Field(None, description="Address comment")
    landmark: str | None = Field(None, max_length=255, description="Landmark")
    location: GeoJSONPoint | None = Field(None, description="Coordinates in GeoJSON format")
    category_id: int | None = Field(None, description="Category ID")
    subcategory_id: int | None = Field(None, description="Subcategory ID")
    phone: str | None = Field(None, description="Phone number(s)")
    mobile: str | None = Field(None, description="Mobile number(s)")
    email: str | None = Field(None, description="Email(s)")
    schedule: str | None = Field(None, description="Working schedule")
    is_active: bool | None = Field(None, description="Is delivery point active")
    tag_ids: list[int] | None = Field(None, description="Tag IDs to assign (replaces existing)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Обновлённое название",
            "address": "Новый адрес",
            "is_active": False
        }
    })


class DeliveryPointDetailResponse(BaseModel):
    """Detailed delivery point response with all fields."""

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
    is_active: bool
    tag_ids: list[int] = Field(default_factory=list, description="Assigned tag IDs")

    model_config = ConfigDict(from_attributes=True)
