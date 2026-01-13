"""Types for schemas."""
from typing import Annotated

from pydantic import BeforeValidator

from app.utils.slugify import slugify


def _normalize_slug(value: str | None) -> str | None:
    """Normalize slug: strip, slugify or return None."""
    if value is not None:
        value = value.strip()
        if not value:
            return None
        return slugify(value)
    return value


SlugStr = Annotated[str | None, BeforeValidator(_normalize_slug)]
