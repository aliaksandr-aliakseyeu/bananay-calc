"""Country schemas."""
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.i18n import I18nStrings


class CountryResponse(BaseModel):
    """Country response schema."""

    id: int
    name: str = Field(..., description="Resolved country name for requested language")
    name_i18n: I18nStrings = Field(..., description="All localized names")
    code: str

    model_config = ConfigDict(from_attributes=True)
