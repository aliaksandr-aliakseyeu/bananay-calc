"""Country schemas."""
from pydantic import BaseModel, ConfigDict


class CountryBase(BaseModel):
    """Base Country schema."""

    name: str
    code: str


class CountryResponse(CountryBase):
    """Country response schema."""

    id: int

    model_config = ConfigDict(from_attributes=True)
