"""Product category schemas."""
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import SlugStr


class ProductCategoryCreate(BaseModel):
    """Product category create schema."""
    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Category name",
        examples=["Food", "Drinks", "Home goods"]
    )
    description: str | None = Field(
        None,
        max_length=255,
        description="Category description",
        examples=["Food category", "Drinks category", "Home goods category"]
    )
    is_active: bool = Field(True, description="Is active")
    sort_order: int = Field(0, description="Sort order")
    cost_multiplier: float = Field(1.0, description="Cost multiplier", ge=0.0, le=10.0)
    slug: SlugStr = Field(None, min_length=3, max_length=100, description="Slug")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Food",
            "description": "Food category",
            "is_active": True,
            "sort_order": 0,
            "cost_multiplier": 1.0,
            "slug": "food",
        }
    })


class ProductCategoryUpdate(BaseModel):
    """Product category update schema."""
    name: str | None = Field(None, min_length=3, max_length=100, description="Category name")
    description: str | None = Field(None, max_length=255, description="Category description")
    is_active: bool | None = Field(None, description="Is active")
    sort_order: int | None = Field(None, description="Sort order")
    cost_multiplier: float | None = Field(None, description="Cost multiplier", ge=0.0, le=10.0)
    slug: SlugStr = Field(None, min_length=3, max_length=100, description="Slug")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Food",
            "description": "Food category",
        }
    })


class ProductCategoryResponse(BaseModel):
    """Product category response schema."""
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Category name")
    description: str | None = Field(None, description="Category description")
    is_active: bool = Field(..., description="Is active")
    sort_order: int = Field(..., description="Sort order")
    cost_multiplier: float = Field(..., description="Cost multiplier")
    slug: str = Field(..., description="Slug")

    model_config = ConfigDict(from_attributes=True, json_schema_extra={
        "example": {
            "id": 1,
            "name": "Food",
            "description": "Food category",
            "is_active": True,
            "sort_order": 0,
            "cost_multiplier": 1.0,
            "slug": "food",
        }
    })
