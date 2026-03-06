"""Admin API for courier daily check-in moderation."""
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import (CourierDailyCheckIn, CourierDailyCheckInPhoto,
                            DailyCheckInStatus, MediaFile, User)
from app.dependencies import get_current_admin
from app.services.azure_blob_service import download_blob


class RejectRequest(BaseModel):
    reason: str = ""

router = APIRouter(prefix="/admin/courier-daily-checkins", tags=["Admin - Courier Daily Check-ins"])


def _serialize(c: CourierDailyCheckIn) -> dict:
    return {
        "id": str(c.id),
        "courier": {
            "id": str(c.courier.id),
            "phone_e164": c.courier.phone_e164,
            "full_name": c.courier.full_name,
        },
        "vehicle": {
            "id": str(c.vehicle.id),
            "plate_number": c.vehicle.plate_number,
            "model": c.vehicle.model,
        },
        "check_date": str(c.check_date),
        "status": c.status.value,
        "completed_at": c.completed_at,
        "photos_count": len(c.photos),
    }


def _serialize_detail(c: CourierDailyCheckIn) -> dict:
    base = _serialize(c)
    base.update({
        "started_at": c.started_at,
        "latitude": c.latitude,
        "longitude": c.longitude,
        "notes": c.notes,
        "reviewed_at": c.reviewed_at,
        "reject_reason": c.reject_reason,
        "photos": [{"kind": p.kind.value, "media_id": str(p.media_id)} for p in c.photos],
    })
    return base


@router.get("/pending")
async def get_pending_checkins(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    limit: int = Query(50, le=100),
    offset: int = 0,
) -> list[dict]:
    """Get all courier check-ins pending review."""
    result = await db.execute(
        select(CourierDailyCheckIn)
        .options(
            selectinload(CourierDailyCheckIn.courier),
            selectinload(CourierDailyCheckIn.vehicle),
            selectinload(CourierDailyCheckIn.photos),
        )
        .where(CourierDailyCheckIn.status == DailyCheckInStatus.PENDING_REVIEW)
        .order_by(CourierDailyCheckIn.completed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_serialize(c) for c in result.scalars().all()]


@router.get("/all")
async def get_all_checkins(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    status_filter: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
) -> list[dict]:
    """Get all courier check-ins with optional status filter."""
    query = select(CourierDailyCheckIn).options(
        selectinload(CourierDailyCheckIn.courier),
        selectinload(CourierDailyCheckIn.vehicle),
        selectinload(CourierDailyCheckIn.photos),
    )
    if status_filter:
        try:
            query = query.where(CourierDailyCheckIn.status == DailyCheckInStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid status: {status_filter}")
    result = await db.execute(
        query.order_by(CourierDailyCheckIn.check_date.desc(), CourierDailyCheckIn.completed_at.desc())
        .limit(limit).offset(offset)
    )
    return [_serialize(c) for c in result.scalars().all()]


@router.get("/stats/pending-count")
async def get_pending_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(
        select(func.count(CourierDailyCheckIn.id))
        .where(CourierDailyCheckIn.status == DailyCheckInStatus.PENDING_REVIEW)
    )
    return {"pending_count": result.scalar() or 0}


@router.get("/{checkin_id}")
async def get_checkin_detail(
    checkin_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(
        select(CourierDailyCheckIn)
        .options(
            selectinload(CourierDailyCheckIn.courier),
            selectinload(CourierDailyCheckIn.vehicle),
            selectinload(CourierDailyCheckIn.photos),
        )
        .where(CourierDailyCheckIn.id == checkin_id)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
    return _serialize_detail(checkin)


@router.post("/{checkin_id}/approve")
async def approve_checkin(
    checkin_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(select(CourierDailyCheckIn).where(CourierDailyCheckIn.id == checkin_id))
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
    if checkin.status != DailyCheckInStatus.PENDING_REVIEW:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Check-in is not pending review (status: {checkin.status.value})")
    checkin.status = DailyCheckInStatus.APPROVED
    checkin.reviewed_by = current_admin.id
    checkin.reviewed_at = datetime.now(timezone.utc)
    checkin.reject_reason = None
    await db.commit()
    return {"status": "approved", "checkin_id": str(checkin_id)}


@router.post("/{checkin_id}/reject")
async def reject_checkin(
    checkin_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    body: RejectRequest,
) -> dict:
    result = await db.execute(select(CourierDailyCheckIn).where(CourierDailyCheckIn.id == checkin_id))
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
    if checkin.status != DailyCheckInStatus.PENDING_REVIEW:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Check-in is not pending review (status: {checkin.status.value})")
    checkin.status = DailyCheckInStatus.REJECTED
    checkin.reviewed_by = current_admin.id
    checkin.reviewed_at = datetime.now(timezone.utc)
    checkin.reject_reason = body.reason or None
    await db.commit()
    return {"status": "rejected", "checkin_id": str(checkin_id)}


@router.get("/media/{media_id}")
async def get_checkin_media(
    media_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> Response:
    result = await db.execute(select(MediaFile).where(MediaFile.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    out = download_blob(media.blob_path)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found in storage")
    content, content_type = out
    return Response(content=content, media_type=media.content_type or content_type)
