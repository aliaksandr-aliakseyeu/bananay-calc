"""Shared constants and helpers for driver endpoints."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import DriverAccount, DriverVehicle, MediaFile, MediaFileOwnerType
from app.db.models.enums import DriverVehicleStatus
from app.utils.vehicle import vehicle_is_active_for_operations

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
    vehicles_result = await db.execute(
        select(DriverVehicle)
        .options(selectinload(DriverVehicle.capabilities))
        .where(DriverVehicle.driver_id == driver.id)
    )
    vehicles = vehicles_result.scalars().all()
    required = {
        "full_name": bool(driver.full_name and driver.full_name.strip()),
        "region_id": driver.region_id is not None,
        "at_least_one_vehicle": False,
        "required_documents": False,
        "sts_per_vehicle": False,
    }
    active_vehicles = [v for v in vehicles if vehicle_is_active_for_operations(v.status)]
    required["at_least_one_vehicle"] = any(
        v.plate_number and v.payload_kg() and v.cargo_volume_m3()
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
    # Draft vehicles may omit STS until the driver submits that vehicle for verification.
    vehicles_requiring_sts = [
        v for v in active_vehicles if v.status != int(DriverVehicleStatus.DRAFT)
    ]
    required["sts_per_vehicle"] = (
        len(vehicles_requiring_sts) == 0
        or all(v.sts_media_id is not None for v in vehicles_requiring_sts)
    )
    can = all(required.values())
    return can, required
