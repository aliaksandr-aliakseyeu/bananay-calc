"""Phone number normalization and validation (E.164, any country)."""
import re

from fastapi import HTTPException, status

PHONE_INVALID_MESSAGE = (
    "Неверный формат номера. Укажите номер с кодом страны, "
    "например +79001234567 или +48451011168."
)


def normalize_phone_e164(raw: str) -> str | None:
    """
    Normalize phone to E.164 (any country).
    Returns None if invalid (too short/long or not parseable).
    """
    s = (raw or "").strip()
    digits = re.sub(r"\D", "", s)
    if not digits or len(digits) < 9 or len(digits) > 15:
        return None
    if s.startswith("+"):
        return "+" + digits
    if len(digits) == 11 and digits[0] in ("7", "8"):
        return "+7" + digits[1:]
    if len(digits) == 10:
        return "+7" + digits
    return "+" + digits


def validate_phone_e164(raw: str) -> str:
    """
    Normalize phone to E.164 or raise HTTP 400.
    Use in endpoints to avoid duplicating validation logic.
    """
    phone = normalize_phone_e164(raw)
    if not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=PHONE_INVALID_MESSAGE,
        )
    return phone
