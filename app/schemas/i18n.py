"""Shared i18n schema types."""

from typing import Annotated

from pydantic import Field

I18nStrings = Annotated[
    dict[str, str],
    Field(description="Localized strings keyed by language code (en, ka, ru)"),
]
