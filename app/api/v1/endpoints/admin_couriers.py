"""Admin endpoints for courier moderation."""
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
from app.db.models.courier_account import CourierAccount
from app.db.models.enums import (
    CourierAccountStatus,
    CourierApplicationStatus,
    MediaFileOwnerType,
)
from app.db.models.media_file import MediaFile
from app.dependencies import get_current_admin
from app.services.azure_blob_service import download_blob

router = APIRouter(prefix="/admin/couriers", tags=["Admin - Couriers"])


@router.get("")
async def get_all_couriers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    status_filter: CourierAccountStatus | None = Query(None, alias="status"),
) -> dict:
    """Get all couriers with optional status filter."""

    query = (
        select(CourierAccount)
        .options(joinedload(CourierAccount.vehicles))
    )
    if status_filter is not None:
        query = query.where(CourierAccount.status == status_filter)
    query = query.order_by(CourierAccount.created_at.desc())

    result = await db.execute(query)
    couriers = result.unique().scalars().all()

    items = []
    for courier in couriers:
        active_vehicles = [v for v in (courier.vehicles or []) if v.is_active]
        items.append({
            "id": str(courier.id),
            "phone_e164": courier.phone_e164,
            "full_name": courier.full_name,
            "city": courier.city,
            "region_id": courier.region_id,
            "status": courier.status.value,
            "vehicles_count": len(active_vehicles),
            "created_at": courier.created_at,
        })

    return {"total": len(items), "items": items}


@router.get("/pending")
async def get_pending_couriers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Get couriers pending approval."""
    result = await db.execute(
        select(CourierAccount)
        .options(joinedload(CourierAccount.vehicles))
        .where(CourierAccount.status == CourierAccountStatus.PENDING_REVIEW)
        .order_by(CourierAccount.created_at.desc())
    )
    couriers = result.unique().scalars().all()

    items = []
    for courier in couriers:
        active_vehicles = [v for v in (courier.vehicles or []) if v.is_active]
        items.append({
            "id": str(courier.id),
            "phone_e164": courier.phone_e164,
            "full_name": courier.full_name,
            "city": courier.city,
            "region_id": courier.region_id,
            "status": courier.status.value,
            "vehicles_count": len(active_vehicles),
            "created_at": courier.created_at,
        })

    return {"total": len(items), "items": items}


@router.get("/{courier_id}")
async def get_courier_detail(
    courier_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Get detailed information about a courier."""

    result = await db.execute(
        select(CourierAccount)
        .options(
            joinedload(CourierAccount.vehicles),
            joinedload(CourierAccount.application),
        )
        .where(CourierAccount.id == courier_id)
    )
    courier = result.unique().scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")

    doc_result = await db.execute(
        select(MediaFile).where(
            MediaFile.owner_id == courier.id,
            MediaFile.owner_type == MediaFileOwnerType.COURIER,
        )
    )
    documents = doc_result.scalars().all()
    doc_map = {doc.kind: str(doc.id) for doc in documents}

    vehicles_data = []
    for vehicle in (courier.vehicles or []):
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
    if courier.application:
        application_data = {
            "id": str(courier.application.id),
            "status": courier.application.status.value,
            "submitted_at": courier.application.submitted_at,
            "reviewed_at": courier.application.reviewed_at,
            "reviewed_by": courier.application.reviewed_by,
            "reject_reason": courier.application.reject_reason,
        }

    return {
        "id": str(courier.id),
        "phone_e164": courier.phone_e164,
        "status": courier.status.value,
        "full_name": courier.full_name,
        "city": courier.city,
        "street": courier.street,
        "building": courier.building,
        "apartment": courier.apartment,
        "region_id": courier.region_id,
        "payout_account": courier.payout_account,
        "created_at": courier.created_at,
        "updated_at": courier.updated_at,
        "blocked_at": courier.blocked_at,
        "blocked_reason": courier.blocked_reason,
        "last_login_at": courier.last_login_at,
        "documents": {
            "selfie": doc_map.get("selfie"),
            "license_front": doc_map.get("license_front"),
            "license_back": doc_map.get("license_back"),
        },
        "vehicles": vehicles_data,
        "application": application_data,
    }


@router.post("/{courier_id}/approve")
async def approve_courier(
    courier_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Approve courier account."""

    result = await db.execute(
        select(CourierAccount)
        .options(joinedload(CourierAccount.application))
        .where(CourierAccount.id == courier_id)
    )
    courier = result.unique().scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")
    if courier.status == CourierAccountStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Courier already approved")
    if courier.status != CourierAccountStatus.PENDING_REVIEW:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Courier is not in pending review status")

    courier.status = CourierAccountStatus.ACTIVE
    if courier.application:
        courier.application.status = CourierApplicationStatus.APPROVED
        courier.application.reviewed_at = datetime.now(timezone.utc)
        courier.application.reviewed_by = current_admin.id
    await db.commit()
    return {"message": "Courier approved successfully", "courier_id": str(courier.id)}


@router.post("/{courier_id}/reject")
async def reject_courier(
    courier_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    reason: str | None = None,
) -> dict:
    """Reject courier account."""
    result = await db.execute(
        select(CourierAccount)
        .options(joinedload(CourierAccount.application))
        .where(CourierAccount.id == courier_id)
    )
    courier = result.unique().scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")
    if courier.status == CourierAccountStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Courier is blocked")
    if courier.status not in (CourierAccountStatus.PENDING_REVIEW, CourierAccountStatus.ACTIVE):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Courier is not in reviewable status")

    courier.status = CourierAccountStatus.DRAFT
    if courier.application:
        courier.application.status = CourierApplicationStatus.REJECTED
        courier.application.reviewed_at = datetime.now(timezone.utc)
        courier.application.reviewed_by = current_admin.id
        courier.application.reject_reason = reason
    await db.commit()
    return {"message": "Courier rejected", "courier_id": str(courier.id), "reason": reason}


@router.post("/{courier_id}/block")
async def block_courier(
    courier_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    reason: str | None = None,
) -> dict:
    """Block courier account."""
    result = await db.execute(select(CourierAccount).where(CourierAccount.id == courier_id))
    courier = result.scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")
    if courier.status == CourierAccountStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Courier already blocked")
    courier.status = CourierAccountStatus.BLOCKED
    courier.blocked_at = datetime.now(timezone.utc)
    courier.blocked_reason = reason
    await db.commit()
    return {"message": "Courier blocked", "courier_id": str(courier.id), "reason": reason}


@router.post("/{courier_id}/unblock")
async def unblock_courier(
    courier_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """Unblock courier account."""
    result = await db.execute(select(CourierAccount).where(CourierAccount.id == courier_id))
    courier = result.scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")
    if courier.status != CourierAccountStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Courier is not blocked")
    courier.status = CourierAccountStatus.ACTIVE
    courier.blocked_at = None
    courier.blocked_reason = None
    await db.commit()
    return {"message": "Courier unblocked", "courier_id": str(courier.id)}


@router.get("/media/{media_id}")
async def get_courier_media(
    media_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> Response:
    """Stream a media file for admin viewing."""
    result = await db.execute(select(MediaFile).where(MediaFile.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    out = download_blob(media.blob_path)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found in storage")
    content, content_type = out
    return Response(content=content, media_type=media.content_type or content_type)
