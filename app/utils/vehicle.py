from __future__ import annotations

import re

from app.db.models.enums import DriverVehicleStatus, VehicleBodyType

_NON_ALNUM_RE = re.compile(r"[^0-9A-Za-zА-Яа-я]+")

_BODY_TYPE_LABELS: dict[int, str] = {
    int(VehicleBodyType.UNKNOWN): "other",
    int(VehicleBodyType.VAN): "van",
    int(VehicleBodyType.REFRIGERATED): "refrigerated",
    int(VehicleBodyType.TENT): "tent",
    int(VehicleBodyType.BOX): "box",
    int(VehicleBodyType.FLATBED): "flatbed",
    int(VehicleBodyType.ISOTHERMAL): "isothermal",
    int(VehicleBodyType.OTHER): "other",
}

ACTIVE_DRIVER_VEHICLE_STATUSES: tuple[int, ...] = (
    int(DriverVehicleStatus.ACTIVE),
    int(DriverVehicleStatus.DRAFT),
    int(DriverVehicleStatus.PENDING_VERIFICATION),
)


def normalize_plate_number(value: str) -> str:
    """Normalize vehicle plate for search and deduplication."""
    return _NON_ALNUM_RE.sub("", (value or "").strip()).upper()


def body_type_code_from_legacy(value: str | None) -> int:
    """Best-effort mapping from free-text body type to code."""
    if not value:
        return int(VehicleBodyType.UNKNOWN)
    normalized = value.strip().lower()
    if not normalized:
        return int(VehicleBodyType.UNKNOWN)
    if any(token in normalized for token in ("реф", "fridge", "refriger", "cold")):
        return int(VehicleBodyType.REFRIGERATED)
    if any(token in normalized for token in ("изотерм", "isotherm")):
        return int(VehicleBodyType.ISOTHERMAL)
    if any(token in normalized for token in ("тент", "tent", "curtain")):
        return int(VehicleBodyType.TENT)
    if any(token in normalized for token in ("фург", "van")):
        return int(VehicleBodyType.VAN)
    if any(token in normalized for token in ("box", "будк")):
        return int(VehicleBodyType.BOX)
    if any(token in normalized for token in ("борт", "flatbed", "platform")):
        return int(VehicleBodyType.FLATBED)
    return int(VehicleBodyType.OTHER)


def body_type_label_from_code(code: int | None) -> str | None:
    """Return a stable legacy label for UI compatibility."""
    if code is None:
        return None
    return _BODY_TYPE_LABELS.get(code, _BODY_TYPE_LABELS[int(VehicleBodyType.OTHER)])


def vehicle_is_active_for_operations(status_code: int | None) -> bool:
    """Map richer status codes back to the legacy is_active flag."""
    if status_code is None:
        return True
    return status_code in ACTIVE_DRIVER_VEHICLE_STATUSES
