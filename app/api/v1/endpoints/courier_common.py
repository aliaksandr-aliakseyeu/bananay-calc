"""Shared constants and helpers for courier endpoints."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import CourierAccount, MediaFile, MediaFileOwnerType

ALLOWED_DOCUMENT_KINDS = frozenset({
    "selfie",
    "license_front",
    "license_back",
    "sts",
    "car_front",
    "car_left",
    "car_right",
    "other",
})
REQUIRED_COURIER_DOCUMENT_KINDS = frozenset({
    "selfie",
    "license_front",
    "license_back",
})
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_VEHICLES = 3


async def check_can_submit(
    courier: CourierAccount, db: AsyncSession
) -> tuple[bool, dict]:
    """Returns (can_submit, required_fields dict). Courier docs + STS per vehicle."""
    required = {
        "full_name": bool(courier.full_name and courier.full_name.strip()),
        "region_id": courier.region_id is not None,
        "at_least_one_vehicle": False,
        "required_documents": False,
        "sts_per_vehicle": False,
    }
    active_vehicles = [v for v in (courier.vehicles or []) if v.is_active]
    required["at_least_one_vehicle"] = any(
        v.plate_number and v.capacity_kg
        for v in active_vehicles
    )
    doc_result = await db.execute(
        select(MediaFile.kind).where(
            MediaFile.owner_type == MediaFileOwnerType.COURIER,
            MediaFile.owner_id == courier.id,
        ).distinct()
    )
    uploaded_courier_kinds = frozenset(doc_result.scalars().all())
    required["required_documents"] = REQUIRED_COURIER_DOCUMENT_KINDS <= uploaded_courier_kinds
    required["sts_per_vehicle"] = (
        len(active_vehicles) == 0
        or all(v.sts_media_id is not None for v in active_vehicles)
    )
    can = all(required.values())
    return can, required
