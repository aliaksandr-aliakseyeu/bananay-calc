"""Helpers for JSONB i18n fields."""

from __future__ import annotations

DEFAULT_LANG = "en"
FALLBACK_LANGS = ("en", "ka", "ru")


def resolve_i18n(
    values: dict[str, str] | None,
    lang: str = DEFAULT_LANG,
    *,
    fallback: str | None = None,
) -> str | None:
    """Resolve a localized string with en as the ultimate fallback."""
    if not values:
        return fallback

    if lang in values and values[lang]:
        return values[lang]

    for code in FALLBACK_LANGS:
        if code in values and values[code]:
            return values[code]

    for value in values.values():
        if value:
            return value

    return fallback


def sync_legacy_text_from_i18n(
    values: dict[str, str] | None,
    *,
    fallback: str | None = None,
) -> str | None:
    """Pick the canonical legacy column value (English first)."""
    return resolve_i18n(values, DEFAULT_LANG, fallback=fallback)
