"""Admin endpoints for driver vehicle verification moderation."""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.base import get_db
from app.db.models import User
from app.db.models.driver_account import DriverAccount
from app.db.models.driver_vehicle import DriverVehicle
from app.db.models.enums import DriverVehicleStatus, VehicleVerificationStatus
from app.db.models.vehicle_compliance import VehicleCompliance
from app.dependencies import get_current_admin
from app.schemas.admin_driver_vehicle import AdminDriverVehicleRejectBody

router = APIRouter(prefix="/admin/driver-vehicles", tags=["Admin - Driver Vehicles"])


def _decimal_to_json(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _serialize_pending_vehicle(vehicle: DriverVehicle) -> dict[str, Any]:
    driver = vehicle.driver
    cap = vehicle.capabilities
    comp = vehicle.compliance
    return {
        "id": str(vehicle.id),
        "driver_id": str(vehicle.driver_id),
        "driver_phone_e164": driver.phone_e164,
        "driver_full_name": driver.full_name,
        "plate_number": vehicle.plate_number,
        "plate_number_normalized": vehicle.plate_number_normalized,
        "brand": vehicle.brand,
        "model": vehicle.model,
        "vin": vehicle.vin,
        "year": vehicle.year,
        "body_type_code": vehicle.body_type_code,
        "status": vehicle.status,
        "photo_media_id": str(vehicle.photo_media_id) if vehicle.photo_media_id else None,
        "sts_media_id": str(vehicle.sts_media_id) if vehicle.sts_media_id else None,
        "payload_kg": cap.payload_kg if cap else None,
        "cargo_volume_m3": _decimal_to_json(cap.cargo_volume_m3) if cap else None,
        "cargo_length_mm": cap.cargo_length_mm if cap else None,
        "cargo_width_mm": cap.cargo_width_mm if cap else None,
        "cargo_height_mm": cap.cargo_height_mm if cap else None,
        "has_refrigerator": cap.has_refrigerator if cap else None,
        "insurance_valid_until": comp.insurance_valid_until.isoformat() if comp and comp.insurance_valid_until else None,
        "last_inspection_date": comp.last_inspection_date.isoformat() if comp and comp.last_inspection_date else None,
        "sts_number": comp.sts_number if comp else None,
        "verification_status": comp.verification_status if comp else 0,
        "verified_at": comp.verified_at.isoformat() if comp and comp.verified_at else None,
        "verification_reject_reason": comp.verification_reject_reason if comp else None,
        "created_at": vehicle.created_at.isoformat() if vehicle.created_at else None,
        "updated_at": vehicle.updated_at.isoformat() if vehicle.updated_at else None,
    }


async def _get_vehicle_admin(db: AsyncSession, vehicle_id: UUID) -> DriverVehicle | None:
    result = await db.execute(
        select(DriverVehicle)
        .options(
            joinedload(DriverVehicle.driver),
            selectinload(DriverVehicle.capabilities),
            selectinload(DriverVehicle.compliance),
        )
        .where(DriverVehicle.id == vehicle_id)
    )
    return result.unique().scalar_one_or_none()


@router.get("/pending")
async def list_pending_vehicles(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict[str, Any]:
    """Vehicles submitted for verification (driver-facing pending)."""
    result = await db.execute(
        select(DriverVehicle)
        .join(DriverAccount, DriverVehicle.driver_id == DriverAccount.id)
        .options(
            joinedload(DriverVehicle.driver),
            selectinload(DriverVehicle.capabilities),
            selectinload(DriverVehicle.compliance),
        )
        .where(DriverVehicle.status == int(DriverVehicleStatus.PENDING_VERIFICATION))
        .order_by(DriverVehicle.updated_at.desc())
    )
    vehicles = result.unique().scalars().all()
    items = [_serialize_pending_vehicle(v) for v in vehicles]
    return {"total": len(items), "items": items}


@router.post("/{vehicle_id}/approve")
async def approve_vehicle(
    vehicle_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict[str, Any]:
    vehicle = await _get_vehicle_admin(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    if vehicle.status != int(DriverVehicleStatus.PENDING_VERIFICATION):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle is not pending verification",
        )
    if vehicle.compliance is None:
        vehicle.compliance = VehicleCompliance(vehicle_id=vehicle.id)
    vehicle.status = int(DriverVehicleStatus.ACTIVE)
    vehicle.compliance.verification_status = int(VehicleVerificationStatus.APPROVED)
    vehicle.compliance.verified_at = datetime.now(timezone.utc)
    vehicle.compliance.verification_reject_reason = None
    await db.commit()
    return {
        "message": "Vehicle approved successfully",
        "vehicle_id": str(vehicle.id),
        "driver_id": str(vehicle.driver_id),
    }


@router.post("/{vehicle_id}/reject")
async def reject_vehicle(
    vehicle_id: UUID,
    body: AdminDriverVehicleRejectBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict[str, Any]:
    vehicle = await _get_vehicle_admin(db, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    if vehicle.status != int(DriverVehicleStatus.PENDING_VERIFICATION):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle is not pending verification",
        )
    if vehicle.compliance is None:
        vehicle.compliance = VehicleCompliance(vehicle_id=vehicle.id)
    vehicle.status = int(DriverVehicleStatus.DRAFT)
    vehicle.compliance.verification_status = int(VehicleVerificationStatus.REJECTED)
    vehicle.compliance.verification_reject_reason = body.reason
    vehicle.compliance.verified_at = None
    await db.commit()
    return {
        "message": "Vehicle rejected; returned to draft for the driver",
        "vehicle_id": str(vehicle.id),
        "driver_id": str(vehicle.driver_id),
        "reason": body.reason,
    }
