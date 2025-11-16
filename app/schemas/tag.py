"""Tag schemas."""
from pydantic import BaseModel, ConfigDict


class TagResponse(BaseModel):
    """Tag response schema."""

    id: int
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "name": "Продукты питания",
            "slug": "produkty-pitaniya"
        }
    })
