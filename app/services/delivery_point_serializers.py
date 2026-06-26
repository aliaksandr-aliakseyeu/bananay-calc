"""Serializers for delivery point API responses."""

from __future__ import annotations

from app.schemas.delivery_point import DeliveryPointResponse, GeoJSONPoint
from app.utils.i18n_fields import resolve_i18n
from app.utils.schedule_i18n import translate_schedule_to_i18n


def serialize_schedule(
    schedule_i18n: dict[str, str] | None,
    legacy_schedule: str | None,
    lang: str = "en",
) -> tuple[str | None, dict[str, str] | None]:
    """Return resolved schedule text and full i18n payload."""
    i18n = schedule_i18n or {}
    if not i18n and legacy_schedule:
        i18n = translate_schedule_to_i18n(legacy_schedule) or {}

    if not i18n and not legacy_schedule:
        return None, None

    resolved = resolve_i18n(i18n, lang, fallback=legacy_schedule)
    return resolved, i18n or None


def build_delivery_point_response(
    delivery_point,
    location: GeoJSONPoint,
    lang: str = "en",
) -> DeliveryPointResponse:
    """Build a delivery point response with localized schedule."""
    schedule, schedule_i18n = serialize_schedule(
        delivery_point.schedule_i18n,
        delivery_point.schedule,
        lang,
    )
    return DeliveryPointResponse(
        id=delivery_point.id,
        name=delivery_point.name,
        type=delivery_point.type,
        title=delivery_point.title,
        address=delivery_point.address,
        address_comment=delivery_point.address_comment,
        landmark=delivery_point.landmark,
        location=location,
        phone=delivery_point.phone,
        mobile=delivery_point.mobile,
        email=delivery_point.email,
        schedule=schedule,
        schedule_i18n=schedule_i18n,
        is_active=delivery_point.is_active,
    )
