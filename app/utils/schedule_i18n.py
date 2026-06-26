"""Translate legacy Russian schedule strings (Yandex import) to en/ka JSONB."""

from __future__ import annotations

import re

DAY_LABELS: dict[str, dict[str, str]] = {
    "Пн": {"en": "Mon", "ka": "ორშ"},
    "Вт": {"en": "Tue", "ka": "სამ"},
    "Ср": {"en": "Wed", "ka": "ოთხ"},
    "Чт": {"en": "Thu", "ka": "ხუთ"},
    "Пт": {"en": "Fri", "ka": "პარ"},
    "Сб": {"en": "Sat", "ka": "შაბ"},
    "Вс": {"en": "Sun", "ka": "კვი"},
}

DAY_TOKEN_PATTERN = re.compile(r"Пн|Вт|Ср|Чт|Пт|Сб|Вс")

# Exact Yandex / import phrases (normalized key = lower stripped Russian source).
KNOWN_SCHEDULE_PHRASES: dict[str, dict[str, str]] = {
    "график работы не указан": {
        "en": "Hours not specified",
        "ka": "სამუშაო გრაფიკი არ არის მითითებული",
        "ru": "График работы не указан",
    },
}


def _normalize_phrase_key(schedule: str) -> str:
    return schedule.strip().casefold()


def is_known_schedule_phrase(schedule: str) -> bool:
    return _normalize_phrase_key(schedule) in KNOWN_SCHEDULE_PHRASES


def _translate_day_token(token: str, lang: str) -> str:
    return DAY_LABELS.get(token, {}).get(lang, token)


def _translate_day_range(value: str, lang: str) -> str:
    return DAY_TOKEN_PATTERN.sub(lambda match: _translate_day_token(match.group(0), lang), value)


def translate_schedule_text(schedule: str, lang: str) -> str | None:
    """Translate a single schedule string to the target language."""
    trimmed = schedule.strip()
    if not trimmed:
        return None

    known = KNOWN_SCHEDULE_PHRASES.get(_normalize_phrase_key(trimmed))
    if known:
        return known.get(lang) or known.get("en")

    open_until_match = re.match(r"^Открыто до\s+(.+)$", trimmed, flags=re.IGNORECASE)
    if open_until_match:
        time_part = open_until_match.group(1).strip()
        if lang == "ka":
            return f"ღიაა {time_part}-მდე"
        return f"Open until {time_part}"

    if re.fullmatch(r"Круглосуточно", trimmed, flags=re.IGNORECASE):
        return "24/7"

    if re.fullmatch(r"Открыто круглосуточно", trimmed, flags=re.IGNORECASE):
        return "Open 24/7" if lang == "en" else "24/7"

    if re.fullmatch(r"Закрыто до завтра", trimmed, flags=re.IGNORECASE):
        return "Closed until tomorrow" if lang == "en" else "დაკეტილია ხვალამდე"

    if re.fullmatch(r"Закрыто", trimmed, flags=re.IGNORECASE):
        return "Closed" if lang == "en" else "დაკეტილია"

    day_range_match = re.match(
        r"^((?:Пн|Вт|Ср|Чт|Пт|Сб|Вс)(?:-(?:Пн|Вт|Ср|Чт|Пт|Сб|Вс))?):?\s*(.+)$",
        trimmed,
    )
    if day_range_match:
        days = _translate_day_range(day_range_match.group(1), lang)
        hours = day_range_match.group(2).strip()
        return f"{days}: {hours}"

    if DAY_TOKEN_PATTERN.search(trimmed):
        return _translate_day_range(trimmed, lang)

    return None


def translate_schedule_to_i18n(schedule: str | None) -> dict[str, str] | None:
    """Build schedule_i18n from a legacy Russian (or plain) schedule string."""
    if not schedule or not schedule.strip():
        return None

    original = schedule.strip()
    known = KNOWN_SCHEDULE_PHRASES.get(_normalize_phrase_key(original))
    if known:
        return dict(known)

    en = translate_schedule_text(original, "en") or original
    ka = translate_schedule_text(original, "ka") or original

    result: dict[str, str] = {"en": en, "ka": ka}
    if re.search(r"[А-Яа-яЁё]", original):
        result["ru"] = original

    return result


def normalize_schedule_i18n(values: dict[str, str] | None) -> dict[str, str] | None:
    """Drop empty values and ensure at least en is present."""
    if not values:
        return None

    cleaned = {lang: text.strip() for lang, text in values.items() if text and text.strip()}
    return cleaned or None
