"""Admin endpoints for driver moderation."""
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.base import get_db
from app.db.models import User
from app.db.models.driver_account import DriverAccount
from app.db.models.enums import (
    DriverAccountStatus,
    DriverApplicationStatus,
    MediaFileOwnerType,
)
from app.db.models.media_file import MediaFile
from app.dependencies import get_current_admin
from app.services.azure_blob_service import download_blob

router = APIRouter(prefix="/admin/drivers", tags=["Admin - Drivers"])


@router.get("/pending")
async def get_pending_drivers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """
    Get list of drivers pending approval.

    Returns drivers with:
    - Status: pending_review
    """
    result = await db.execute(
        select(DriverAccount)
        .options(joinedload(DriverAccount.vehicles))
        .where(DriverAccount.status == DriverAccountStatus.PENDING_REVIEW)
        .order_by(DriverAccount.created_at.desc())
    )
    drivers = result.unique().scalars().all()

    items = []
    for driver in drivers:
        active_vehicles = [v for v in (driver.vehicles or []) if v.is_active]
        items.append({
            "id": str(driver.id),
            "phone_e164": driver.phone_e164,
            "full_name": driver.full_name,
            "city": driver.city,
            "region_id": driver.region_id,
            "status": driver.status.value,
            "vehicles_count": len(active_vehicles),
            "created_at": driver.created_at,
        })

    return {
        "total": len(items),
        "items": items,
    }


@router.get("")
async def get_all_drivers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    status_filter: DriverAccountStatus | None = Query(None, alias="status", description="Filter by status"),
) -> dict:
    """
    Get all drivers with filters.

    Admin can filter by status.
    """
    query = (
        select(DriverAccount)
        .options(joinedload(DriverAccount.vehicles))
    )

    if status_filter is not None:
        query = query.where(DriverAccount.status == status_filter)

    query = query.order_by(DriverAccount.created_at.desc())

    result = await db.execute(query)
    drivers = result.unique().scalars().all()

    items = []
    for driver in drivers:
        active_vehicles = [v for v in (driver.vehicles or []) if v.is_active]
        items.append({
            "id": str(driver.id),
            "phone_e164": driver.phone_e164,
            "full_name": driver.full_name,
            "city": driver.city,
            "region_id": driver.region_id,
            "status": driver.status.value,
            "vehicles_count": len(active_vehicles),
            "created_at": driver.created_at,
        })

    return {
        "total": len(items),
        "items": items,
    }


@router.post("/{driver_id}/approve")
async def approve_driver(
    driver_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """
    Approve driver account.

    Sets:
    - driver.status = active
    - application.status = approved
    - application.reviewed_at = now
    - application.reviewed_by = admin_id
    """
    result = await db.execute(
        select(DriverAccount)
        .options(joinedload(DriverAccount.application))
        .where(DriverAccount.id == driver_id)
    )
    driver = result.unique().scalar_one_or_none()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )

    if driver.status == DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver already approved",
        )

    if driver.status != DriverAccountStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is not in pending review status",
        )

    driver.status = DriverAccountStatus.ACTIVE

    if driver.application:
        driver.application.status = DriverApplicationStatus.APPROVED
        driver.application.reviewed_at = datetime.now(timezone.utc)
        driver.application.reviewed_by = current_admin.id

    await db.commit()

    return {
        "message": "Driver approved successfully",
        "driver_id": str(driver.id),
        "phone_e164": driver.phone_e164,
    }


@router.post("/{driver_id}/reject")
async def reject_driver(
    driver_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    reason: str | None = None,
) -> dict:
    """
    Reject driver account.

    Sets:
    - driver.status = draft (so they can resubmit)
    - application.status = rejected
    - application.reviewed_at = now
    - application.reviewed_by = admin_id
    - application.reject_reason = reason
    """
    result = await db.execute(
        select(DriverAccount)
        .options(joinedload(DriverAccount.application))
        .where(DriverAccount.id == driver_id)
    )
    driver = result.unique().scalar_one_or_none()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )

    if driver.status == DriverAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is blocked",
        )

    if driver.status not in (DriverAccountStatus.PENDING_REVIEW, DriverAccountStatus.ACTIVE):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is not in reviewable status",
        )

    driver.status = DriverAccountStatus.DRAFT

    if driver.application:
        driver.application.status = DriverApplicationStatus.REJECTED
        driver.application.reviewed_at = datetime.now(timezone.utc)
        driver.application.reviewed_by = current_admin.id
        driver.application.reject_reason = reason

    await db.commit()

    return {
        "message": "Driver rejected successfully",
        "driver_id": str(driver.id),
        "phone_e164": driver.phone_e164,
        "reason": reason,
    }


@router.get("/{driver_id}")
async def get_driver_detail(
    driver_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """
    Get detailed information about a driver.

    Returns full driver information including:
    - Profile details
    - Vehicles with photos and STS
    - Documents (selfie, license)
    - Application status
    """
    result = await db.execute(
        select(DriverAccount)
        .options(
            joinedload(DriverAccount.vehicles),
            joinedload(DriverAccount.application),
        )
        .where(DriverAccount.id == driver_id)
    )
    driver = result.unique().scalar_one_or_none()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )

    doc_result = await db.execute(
        select(MediaFile).where(
            MediaFile.owner_id == driver.id,
            MediaFile.owner_type == MediaFileOwnerType.DRIVER,
        )
    )
    documents = doc_result.scalars().all()

    doc_map = {}
    for doc in documents:
        doc_map[doc.kind] = str(doc.id)

    vehicles_data = []
    for vehicle in (driver.vehicles or []):
        vehicles_data.append({
            "id": str(vehicle.id),
            "plate_number": vehicle.plate_number,
            "model": vehicle.model,
            "capacity_kg": vehicle.capacity_kg,
            "capacity_m3": float(vehicle.capacity_m3) if vehicle.capacity_m3 else None,
            "body_type": vehicle.body_type,
            "is_active": vehicle.is_active,
            "photo_media_id": str(vehicle.photo_media_id) if vehicle.photo_media_id else None,
            "sts_media_id": str(vehicle.sts_media_id) if vehicle.sts_media_id else None,
            "created_at": vehicle.created_at,
        })

    application_data = None
    if driver.application:
        application_data = {
            "id": str(driver.application.id),
            "status": driver.application.status.value,
            "submitted_at": driver.application.submitted_at,
            "reviewed_at": driver.application.reviewed_at,
            "reviewed_by": driver.application.reviewed_by,
            "reject_reason": driver.application.reject_reason,
        }

    return {
        "id": str(driver.id),
        "phone_e164": driver.phone_e164,
        "status": driver.status.value,
        "full_name": driver.full_name,
        "city": driver.city,
        "street": driver.street,
        "building": driver.building,
        "apartment": driver.apartment,
        "region_id": driver.region_id,
        "payout_account": driver.payout_account,
        "created_at": driver.created_at,
        "updated_at": driver.updated_at,
        "blocked_at": driver.blocked_at,
        "blocked_reason": driver.blocked_reason,
        "last_login_at": driver.last_login_at,
        "documents": {
            "selfie": doc_map.get("selfie"),
            "license_front": doc_map.get("license_front"),
            "license_back": doc_map.get("license_back"),
        },
        "vehicles": vehicles_data,
        "application": application_data,
    }


@router.post("/{driver_id}/block")
async def block_driver(
    driver_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    reason: str | None = None,
) -> dict:
    """
    Block driver account.
    """
    result = await db.execute(
        select(DriverAccount).where(DriverAccount.id == driver_id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )

    if driver.status == DriverAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver already blocked",
        )

    driver.status = DriverAccountStatus.BLOCKED
    driver.blocked_at = datetime.now(timezone.utc)
    driver.blocked_reason = reason

    await db.commit()

    return {
        "message": "Driver blocked successfully",
        "driver_id": str(driver.id),
        "reason": reason,
    }


@router.post("/{driver_id}/unblock")
async def unblock_driver(
    driver_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """
    Unblock driver account.
    """
    result = await db.execute(
        select(DriverAccount).where(DriverAccount.id == driver_id)
    )
    driver = result.scalar_one_or_none()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )

    if driver.status != DriverAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver is not blocked",
        )

    driver.status = DriverAccountStatus.ACTIVE
    driver.blocked_at = None
    driver.blocked_reason = None

    await db.commit()

    return {
        "message": "Driver unblocked successfully",
        "driver_id": str(driver.id),
    }


@router.get("/media/{media_id}")
async def get_driver_media(
    media_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> Response:
    """
    Stream a media file (document or vehicle photo) for admin viewing.
    Admin can view any driver's media files.
    """
    result = await db.execute(select(MediaFile).where(MediaFile.id == media_id))
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    out = download_blob(media.blob_path)
    if out is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found in storage",
        )

    content, content_type = out
    return Response(content=content, media_type=media.content_type or content_type)
