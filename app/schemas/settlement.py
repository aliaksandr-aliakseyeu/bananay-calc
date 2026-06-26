"""Settlement schemas."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import SettlementType
from app.schemas.delivery_point import GeoJSONPoint


class SettlementResponse(BaseModel):
    """Settlement response for dropdown/list."""

    id: int
    region_id: int = Field(..., description="Region ID")
    name: str
    type: str | None = Field(None, description="Settlement type (город, село, etc.)")
    postal_code: int | None = Field(None, description="Postal code")
    location: GeoJSONPoint | None = Field(None, description="Center coordinates")

    model_config = ConfigDict(from_attributes=True)


class SettlementCreate(BaseModel):
    """Schema for creating a settlement."""

    region_id: int = Field(..., description="Region ID")
    name: str = Field(..., min_length=1, max_length=200, description="Settlement name")
    type: Optional[SettlementType] = Field(None, description="Settlement type")
    postal_code: Optional[int] = Field(None, description="Postal code")
    location: GeoJSONPoint = Field(..., description="Coordinates in GeoJSON format")


class SettlementUpdate(BaseModel):
    """Schema for updating a settlement. All fields are optional."""

    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Settlement name")
    type: Optional[SettlementType] = Field(None, description="Settlement type")
    postal_code: Optional[int] = Field(None, description="Postal code")
    location: Optional[GeoJSONPoint] = Field(None, description="Coordinates in GeoJSON format")


class SettlementSearchResponse(BaseModel):
    """Response for settlement search by coordinates."""

    settlement: SettlementResponse | None = Field(
        None, description="Found settlement or null"
    )
    distance_km: float | None = Field(
        None, description="Distance from point to settlement center in km"
    )
    auto_detected: bool = Field(
        False, description="Whether settlement was auto-detected"
    )
