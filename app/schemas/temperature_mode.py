"""Temperature mode schemas."""
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import SlugStr


class TemperatureModeCreate(BaseModel):
    """Temperature mode create schema."""
    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Temperature mode name",
        examples=["Cold", "Frozen", "Room temperature"]
    )
    description: str | None = Field(None, max_length=255, description="Temperature mode description")
    slug: SlugStr = Field(None, min_length=3, max_length=100, description="Slug")
    is_active: bool = Field(True, description="Is active")
    sort_order: int = Field(0, description="Sort order")
    cost_multiplier: float = Field(1.0, description="Cost multiplier", ge=0.0, le=10.0)
    min_temperature: int | None = Field(None, description="Min temperature", ge=-100, le=100)
    max_temperature: int | None = Field(None, description="Max temperature", ge=-100, le=100)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Cold",
            "description": "Cold temperature mode",
            "is_active": True,
            "sort_order": 0,
            "cost_multiplier": 1.0,
            "slug": "cold",
            "min_temperature": -100,
            "max_temperature": 100
        }
    })


class TemperatureModeUpdate(BaseModel):
    """Temperature mode update schema."""
    name: str | None = Field(None, min_length=3, max_length=100, description="Temperature mode name")
    description: str | None = Field(None, max_length=255, description="Temperature mode description")
    is_active: bool | None = Field(None, description="Is active")
    sort_order: int | None = Field(None, description="Sort order")
    cost_multiplier: float | None = Field(None, description="Cost multiplier", ge=0.0, le=10.0)
    slug: SlugStr = Field(None, min_length=3, max_length=100, description="Slug")
    min_temperature: int | None = Field(None, description="Min temperature", ge=-100, le=100)
    max_temperature: int | None = Field(None, description="Max temperature", ge=-100, le=100)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Cold",
            "description": "Cold temperature mode",
        }
    })


class TemperatureModeResponse(BaseModel):
    """Temperature mode response schema."""
    id: int = Field(..., description="Temperature mode ID")
    name: str = Field(..., description="Temperature mode name")
    description: str | None = Field(None, description="Temperature mode description")
    is_active: bool = Field(..., description="Is active")
    sort_order: int = Field(..., description="Sort order")
    cost_multiplier: float = Field(..., description="Cost multiplier")
    slug: str = Field(..., description="Slug")
    min_temperature: int | None = Field(None, description="Min temperature")
    max_temperature: int | None = Field(None, description="Max temperature")

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "name": "Cold",
            "description": "Cold temperature mode",
            "is_active": True,
            "sort_order": 0,
            "cost_multiplier": 1.0,
            "slug": "cold",
            "min_temperature": -100,
            "max_temperature": 100
        }
    })
