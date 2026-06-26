"""Temperature mode schemas."""
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.i18n import I18nStrings
from app.schemas.product_category import _require_english_name
from app.schemas.types import SlugStr


class TemperatureModeCreate(BaseModel):
    """Temperature mode create schema."""
    name_i18n: I18nStrings = Field(
        ...,
        description="Localized temperature mode names",
        examples=[{"en": "Frozen", "ka": "გაყინული"}],
    )
    description_i18n: I18nStrings | None = Field(
        None,
        description="Localized temperature mode descriptions",
    )
    slug: SlugStr = Field(None, min_length=3, max_length=100, description="Slug")
    is_active: bool = Field(True, description="Is active")
    sort_order: int = Field(0, description="Sort order")
    cost_multiplier: float = Field(1.0, description="Cost multiplier", ge=0.0, le=10.0)
    min_temperature: int | None = Field(None, description="Min temperature", ge=-100, le=100)
    max_temperature: int | None = Field(None, description="Max temperature", ge=-100, le=100)

    @field_validator("name_i18n")
    @classmethod
    def validate_name_i18n(cls, value: dict[str, str]) -> dict[str, str]:
        return _require_english_name(value)

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name_i18n": {
                "en": "Frozen (-18°C and below)",
                "ka": "გაყინული (-18°C და ქვემოთ)",
            },
            "description_i18n": {
                "en": "Frozen products",
                "ka": "გაყინული პროდუქტები",
            },
            "is_active": True,
            "sort_order": 0,
            "cost_multiplier": 1.0,
            "slug": "frozen",
            "min_temperature": -25,
            "max_temperature": -18,
        }
    })


class TemperatureModeUpdate(BaseModel):
    """Temperature mode update schema."""
    name_i18n: I18nStrings | None = Field(None, description="Localized temperature mode names")
    description_i18n: I18nStrings | None = Field(
        None,
        description="Localized temperature mode descriptions",
    )
    is_active: bool | None = Field(None, description="Is active")
    sort_order: int | None = Field(None, description="Sort order")
    cost_multiplier: float | None = Field(None, description="Cost multiplier", ge=0.0, le=10.0)
    slug: SlugStr = Field(None, min_length=3, max_length=100, description="Slug")
    min_temperature: int | None = Field(None, description="Min temperature", ge=-100, le=100)
    max_temperature: int | None = Field(None, description="Max temperature", ge=-100, le=100)

    @field_validator("name_i18n")
    @classmethod
    def validate_name_i18n(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        if value is None:
            return value
        return _require_english_name(value)


class TemperatureModeResponse(BaseModel):
    """Temperature mode response schema."""
    id: int = Field(..., description="Temperature mode ID")
    name: str = Field(..., description="Resolved mode name for requested language")
    description: str | None = Field(None, description="Resolved mode description")
    name_i18n: I18nStrings = Field(..., description="All localized names")
    description_i18n: I18nStrings | None = Field(None, description="All localized descriptions")
    is_active: bool = Field(..., description="Is active")
    sort_order: int = Field(..., description="Sort order")
    cost_multiplier: float = Field(..., description="Cost multiplier")
    slug: str = Field(..., description="Slug")
    min_temperature: int | None = Field(None, description="Min temperature")
    max_temperature: int | None = Field(None, description="Max temperature")

    model_config = ConfigDict(from_attributes=True)
