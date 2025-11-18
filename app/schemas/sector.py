"""Sector schemas."""
from pydantic import BaseModel, ConfigDict, Field


class GeoJSONPolygon(BaseModel):
    """GeoJSON Polygon geometry."""

    type: str = Field(default="Polygon", description="Geometry type")
    coordinates: list[list[list[float]]] = Field(
        ...,
        description="Polygon coordinates [[[lng, lat], [lng, lat], ...]]"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "type": "Polygon",
            "coordinates": [
                [
                    [39.723098, 43.585472],
                    [39.730678, 43.585525],
                    [39.732000, 43.580000],
                    [39.723098, 43.585472]
                ]
            ]
        }
    })


class SectorResponse(BaseModel):
    """Sector response schema with GeoJSON boundary."""

    id: int
    region_id: int
    name: str | None = Field(None, description="Sector name")
    description: str | None = Field(None, description="Sector description")
    boundary: GeoJSONPolygon = Field(..., description="Sector boundary in GeoJSON format")

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "region_id": 1,
            "name": "Адлерский сектор 1",
            "description": "Сектор доставки в Адлерском районе",
            "boundary": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [39.723098, 43.585472],
                        [39.730678, 43.585525],
                        [39.732000, 43.580000],
                        [39.723098, 43.585472]
                    ]
                ]
            }
        }
    })
