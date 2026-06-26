"""Name classification and fallback helpers for Batumi import."""
from __future__ import annotations

import re
from enum import Enum

GEORGIAN_RE = re.compile(r"[\u10A0-\u10FF]")
CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
LATIN_RE = re.compile(r"[A-Za-z]")
SPLIT_RE = re.compile(r"[•|/]")


class NameScript(str, Enum):
    EMPTY = "empty"
    RUSSIAN = "russian"
    GEORGIAN = "georgian"
    LATIN = "latin"
    MIXED = "mixed"


def classify_name(name: str | None) -> NameScript:
    """Classify a delivery point name by dominant script."""
    if not name or not str(name).strip():
        return NameScript.EMPTY

    text = str(name).strip()
    has_georgian = bool(GEORGIAN_RE.search(text))
    has_cyrillic = bool(CYRILLIC_RE.search(text))
    has_latin = bool(LATIN_RE.search(text))

    if has_georgian and (has_cyrillic or has_latin):
        return NameScript.MIXED
    if has_georgian:
        return NameScript.GEORGIAN
    if has_cyrillic:
        return NameScript.RUSSIAN
    if has_latin:
        return NameScript.LATIN
    return NameScript.MIXED


def extract_georgian_part(name: str) -> str | None:
    """Extract Georgian substring from a mixed or Georgian name."""
    if not name:
        return None

    text = str(name).strip()
    for part in SPLIT_RE.split(text):
        part = part.strip()
        if GEORGIAN_RE.search(part):
            return part

    if GEORGIAN_RE.search(text):
        return text
    return None


def extract_latin_part(name: str) -> str | None:
    """Extract Latin substring from a mixed or Latin name."""
    if not name:
        return None

    text = str(name).strip()
    for part in SPLIT_RE.split(text):
        part = part.strip()
        if LATIN_RE.search(part) and not CYRILLIC_RE.search(part) and not GEORGIAN_RE.search(part):
            return part

    if LATIN_RE.search(text) and not CYRILLIC_RE.search(text) and not GEORGIAN_RE.search(text):
        return text
    return None


def resolve_fallback_name(name: str, script: NameScript) -> str | None:
    """Resolve a fallback name from the original Excel value."""
    if script == NameScript.GEORGIAN:
        return str(name).strip() or None

    if script == NameScript.LATIN:
        return extract_latin_part(name) or str(name).strip() or None

    if script == NameScript.MIXED:
        georgian = extract_georgian_part(name)
        if georgian:
            return georgian
        latin = extract_latin_part(name)
        if latin:
            return latin

    return str(name).strip() or None
