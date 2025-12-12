"""Settlement schemas."""
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.delivery_point import GeoJSONPoint


class SettlementResponse(BaseModel):
    """Settlement response for dropdown/list."""

    id: int
    name: str
    type: str | None = Field(None, description="Settlement type (город, село, etc.)")
    postal_code: int | None = Field(None, description="Postal code")
    location: GeoJSONPoint | None = Field(None, description="Center coordinates")

    model_config = ConfigDict(from_attributes=True)


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
