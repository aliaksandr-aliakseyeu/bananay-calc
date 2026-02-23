"""Shared constants and helpers for driver endpoints."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DriverAccount, MediaFile, MediaFileOwnerType

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
REQUIRED_DRIVER_DOCUMENT_KINDS = frozenset({
    "selfie",
    "license_front",
    "license_back",
})
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


async def check_can_submit(
    driver: DriverAccount, db: AsyncSession
) -> tuple[bool, dict]:
    """Returns (can_submit, required_fields dict). Driver docs + STS per vehicle."""
    required = {
        "full_name": bool(driver.full_name and driver.full_name.strip()),
        "region_id": driver.region_id is not None,
        "at_least_one_vehicle": False,
        "required_documents": False,
        "sts_per_vehicle": False,
    }
    active_vehicles = [v for v in (driver.vehicles or []) if v.is_active]
    required["at_least_one_vehicle"] = any(
        v.plate_number and v.capacity_kg and v.capacity_m3
        for v in active_vehicles
    )
    doc_result = await db.execute(
        select(MediaFile.kind).where(
            MediaFile.owner_type == MediaFileOwnerType.DRIVER,
            MediaFile.owner_id == driver.id,
        ).distinct()
    )
    uploaded_driver_kinds = frozenset(doc_result.scalars().all())
    required["required_documents"] = REQUIRED_DRIVER_DOCUMENT_KINDS <= uploaded_driver_kinds
    required["sts_per_vehicle"] = (
        len(active_vehicles) == 0
        or all(v.sts_media_id is not None for v in active_vehicles)
    )
    can = all(required.values())
    return can, required
