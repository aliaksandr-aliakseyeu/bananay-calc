"""Product category schemas."""
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.i18n import I18nStrings
from app.schemas.types import SlugStr


def _require_english_name(values: dict[str, str]) -> dict[str, str]:
    if not values.get("en", "").strip():
        raise ValueError("English name (en) is required in name_i18n")
    return values


class ProductCategoryCreate(BaseModel):
    """Product category create schema."""
    name_i18n: I18nStrings = Field(
        ...,
        description="Localized category names",
        examples=[{"en": "Fresh products", "ka": "ახალი პროდუქტები"}],
    )
    description_i18n: I18nStrings | None = Field(
        None,
        description="Localized category descriptions",
    )
    is_active: bool = Field(True, description="Is active")
    sort_order: int = Field(0, description="Sort order")
    cost_multiplier: float = Field(1.0, description="Cost multiplier", ge=0.0, le=10.0)
    slug: SlugStr = Field(None, min_length=3, max_length=100, description="Slug")

    @field_validator("name_i18n")
    @classmethod
    def validate_name_i18n(cls, value: dict[str, str]) -> dict[str, str]:
        return _require_english_name(value)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name_i18n": {
                "en": "Fresh products",
                "ka": "ახალი პროდუქტები",
            },
            "description_i18n": {
                "en": "Fresh fruits and vegetables",
                "ka": "ახალი ხილი და ბოსტნეული",
            },
            "is_active": True,
            "sort_order": 0,
            "cost_multiplier": 1.0,
            "slug": "fresh-products",
        }
    })


class ProductCategoryUpdate(BaseModel):
    """Product category update schema."""
    name_i18n: I18nStrings | None = Field(None, description="Localized category names")
    description_i18n: I18nStrings | None = Field(
        None,
        description="Localized category descriptions",
    )
    is_active: bool | None = Field(None, description="Is active")
    sort_order: int | None = Field(None, description="Sort order")
    cost_multiplier: float | None = Field(None, description="Cost multiplier", ge=0.0, le=10.0)
    slug: SlugStr = Field(None, min_length=3, max_length=100, description="Slug")

    @field_validator("name_i18n")
    @classmethod
    def validate_name_i18n(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return value
        return _require_english_name(value)


class ProductCategoryResponse(BaseModel):
    """Product category response schema."""
    id: int = Field(..., description="Category ID")
    name: str = Field(..., description="Resolved category name for requested language")
    description: str | None = Field(None, description="Resolved category description")
    name_i18n: I18nStrings = Field(..., description="All localized names")
    description_i18n: I18nStrings | None = Field(None, description="All localized descriptions")
    is_active: bool = Field(..., description="Is active")
    sort_order: int = Field(..., description="Sort order")
    cost_multiplier: float = Field(..., description="Cost multiplier")
    slug: str = Field(..., description="Slug")

    model_config = ConfigDict(from_attributes=True)
