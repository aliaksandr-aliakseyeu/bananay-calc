"""Admin API for daily check-in moderation."""
import json
from datetime import datetime, timezone
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import DailyCheckIn, DailyCheckInStatus, MediaFile, User
from app.dependencies import get_current_admin
from app.schemas.admin_daily_checkin import (
    CheckInDetailResponse,
    CheckInListItem,
    CheckInPhotoResponse,
    DriverShortInfo,
    RejectRequest,
    VehicleShortInfo,
)
from app.services.azure_blob_service import download_blob

router = APIRouter(prefix="/admin/daily-checkins", tags=["Admin - Daily Check-ins"])


@router.get("/pending", response_model=list[CheckInListItem])
async def get_pending_checkins(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    limit: int = Query(50, le=100),
    offset: int = 0,
):
    """Get all check-ins pending review."""
    result = await db.execute(
        select(DailyCheckIn)
        .options(
            selectinload(DailyCheckIn.driver),
            selectinload(DailyCheckIn.vehicle),
            selectinload(DailyCheckIn.photos),
        )
        .where(DailyCheckIn.status == DailyCheckInStatus.PENDING_REVIEW)
        .order_by(DailyCheckIn.completed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    checkins = result.scalars().all()

    return [
        CheckInListItem(
            id=str(c.id),
            driver=DriverShortInfo(
                id=str(c.driver.id),
                phone_e164=c.driver.phone_e164,
                full_name=c.driver.full_name,
            ),
            vehicle=VehicleShortInfo(
                id=str(c.vehicle.id),
                plate_number=c.vehicle.plate_number,
                model=c.vehicle.model,
            ),
            check_date=str(c.check_date),
            status=c.status.value,
            completed_at=c.completed_at,
            photos_count=len(c.photos),
        )
        for c in checkins
    ]


@router.get("/all", response_model=list[CheckInListItem])
async def get_all_checkins(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    status_filter: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = 0,
):
    """Get all check-ins with optional status filter."""
    query = select(DailyCheckIn).options(
        selectinload(DailyCheckIn.driver),
        selectinload(DailyCheckIn.vehicle),
        selectinload(DailyCheckIn.photos),
    )

    if status_filter:
        try:
            status_enum = DailyCheckInStatus(status_filter)
            query = query.where(DailyCheckIn.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )

    result = await db.execute(
        query.order_by(DailyCheckIn.check_date.desc(), DailyCheckIn.completed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    checkins = result.scalars().all()

    return [
        CheckInListItem(
            id=str(c.id),
            driver=DriverShortInfo(
                id=str(c.driver.id),
                phone_e164=c.driver.phone_e164,
                full_name=c.driver.full_name,
            ),
            vehicle=VehicleShortInfo(
                id=str(c.vehicle.id),
                plate_number=c.vehicle.plate_number,
                model=c.vehicle.model,
            ),
            check_date=str(c.check_date),
            status=c.status.value,
            completed_at=c.completed_at,
            photos_count=len(c.photos),
        )
        for c in checkins
    ]


@router.get("/{checkin_id}", response_model=CheckInDetailResponse)
async def get_checkin_detail(
    checkin_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
):
    """Get detailed check-in info."""
    result = await db.execute(
        select(DailyCheckIn)
        .options(
            selectinload(DailyCheckIn.driver),
            selectinload(DailyCheckIn.vehicle),
            selectinload(DailyCheckIn.photos),
        )
        .where(DailyCheckIn.id == checkin_id)
    )
    checkin = result.scalar_one_or_none()

    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in not found",
        )

    return CheckInDetailResponse(
        id=str(checkin.id),
        driver=DriverShortInfo(
            id=str(checkin.driver.id),
            phone_e164=checkin.driver.phone_e164,
            full_name=checkin.driver.full_name,
        ),
        vehicle=VehicleShortInfo(
            id=str(checkin.vehicle.id),
            plate_number=checkin.vehicle.plate_number,
            model=checkin.vehicle.model,
        ),
        check_date=str(checkin.check_date),
        status=checkin.status.value,
        started_at=checkin.started_at,
        completed_at=checkin.completed_at,
        latitude=checkin.latitude,
        longitude=checkin.longitude,
        notes=checkin.notes,
        reviewed_at=checkin.reviewed_at,
        reject_reason=checkin.reject_reason,
        photos=[
            CheckInPhotoResponse(kind=p.kind.value, media_id=str(p.media_id))
            for p in checkin.photos
        ],
    )


@router.post("/{checkin_id}/approve")
async def approve_checkin(
    checkin_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
):
    """Approve a daily check-in."""
    result = await db.execute(
        select(DailyCheckIn).where(DailyCheckIn.id == checkin_id)
    )
    checkin = result.scalar_one_or_none()

    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in not found",
        )

    if checkin.status != DailyCheckInStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Check-in is not pending review (status: {checkin.status.value})",
        )

    checkin.status = DailyCheckInStatus.APPROVED
    checkin.reviewed_by = current_admin.id
    checkin.reviewed_at = datetime.now(timezone.utc)
    checkin.reject_reason = None

    payload = json.dumps({
        "driver_id": str(checkin.driver_id),
        "event": "daily_checkin_status",
        "checkin_id": str(checkin_id),
        "status": "approved",
        "reject_reason": None,
    })
    safe_payload = payload.replace("'", "''")
    await db.execute(text(f"NOTIFY daily_checkin_events, '{safe_payload}'"))
    await db.commit()

    return {"status": "approved", "checkin_id": str(checkin_id)}


@router.post("/{checkin_id}/reject")
async def reject_checkin(
    checkin_id: UUID,
    body: RejectRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
):
    """Reject a daily check-in."""
    result = await db.execute(
        select(DailyCheckIn).where(DailyCheckIn.id == checkin_id)
    )
    checkin = result.scalar_one_or_none()

    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Check-in not found",
        )

    if checkin.status != DailyCheckInStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Check-in is not pending review (status: {checkin.status.value})",
        )

    checkin.status = DailyCheckInStatus.REJECTED
    checkin.reviewed_by = current_admin.id
    checkin.reviewed_at = datetime.now(timezone.utc)
    checkin.reject_reason = body.reason

    payload = json.dumps({
        "driver_id": str(checkin.driver_id),
        "event": "daily_checkin_status",
        "checkin_id": str(checkin_id),
        "status": "rejected",
        "reject_reason": body.reason,
    })
    safe_payload = payload.replace("'", "''")
    await db.execute(text(f"NOTIFY daily_checkin_events, '{safe_payload}'"))
    await db.commit()

    return {"status": "rejected", "checkin_id": str(checkin_id)}


@router.get("/media/{media_id}")
async def get_checkin_media(
    media_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
):
    """Get media file for check-in (admin access)."""
    result = await db.execute(
        select(MediaFile).where(MediaFile.id == media_id)
    )
    media = result.scalar_one_or_none()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )

    out = download_blob(media.blob_path)
    if out is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file not found in storage",
        )

    content, content_type = out
    return Response(content=content, media_type=media.content_type or content_type)


@router.get("/stats/pending-count")
async def get_pending_count(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
):
    """Get count of pending check-ins."""
    result = await db.execute(
        select(func.count(DailyCheckIn.id))
        .where(DailyCheckIn.status == DailyCheckInStatus.PENDING_REVIEW)
    )
    count = result.scalar() or 0

    return {"pending_count": count}
