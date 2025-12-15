"""Distribution center schemas."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.delivery_point import GeoJSONPoint


class DistributionCenterCreate(BaseModel):
    """Schema for creating a distribution center."""

    region_id: int = Field(..., description="Region ID", examples=[1])
    name: str = Field(..., min_length=1, max_length=200, description="Distribution center name")
    address: Optional[str] = Field(None, description="Distribution center address")
    is_active: bool = Field(True, description="Whether the center is active")
    location: GeoJSONPoint = Field(..., description="Coordinates in GeoJSON format")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "region_id": 1,
            "name": "РЦ Адлер",
            "address": "село Казачий Брод, Краснофлотская улица, 27",
            "is_active": True,
            "location": {
                "type": "Point",
                "coordinates": [39.723098, 43.585472]
            }
        }
    })


class DistributionCenterUpdate(BaseModel):
    """Schema for updating a distribution center. All fields are optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Distribution center name")
    address: Optional[str] = Field(None, description="Distribution center address")
    is_active: Optional[bool] = Field(None, description="Whether the center is active")
    location: Optional[GeoJSONPoint] = Field(None, description="Coordinates in GeoJSON format")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Обновлённое название РЦ",
            "address": "Новый адрес",
            "is_active": False
        }
    })


class DistributionCenterResponse(BaseModel):
    """Schema for distribution center response."""

    id: int = Field(..., description="Distribution center ID")
    region_id: int = Field(..., description="Region ID")
    name: str = Field(..., description="Distribution center name")
    address: Optional[str] = Field(None, description="Distribution center address")
    is_active: bool = Field(..., description="Whether the center is active")
    location: Optional[GeoJSONPoint] = Field(None, description="Coordinates in GeoJSON format")

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "region_id": 1,
            "name": "РЦ Адлер",
            "address": "село Казачий Брод, Краснофлотская улица, 27",
            "is_active": True,
            "location": {
                "type": "Point",
                "coordinates": [39.723098, 43.585472]
            }
        }
    })
