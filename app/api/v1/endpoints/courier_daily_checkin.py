"""Daily check-in API for couriers."""
import asyncio
import json
from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.base import get_db
from app.db.models import (
    CourierAccount,
    CourierDailyCheckIn,
    CourierDailyCheckInPhoto,
    CourierVehicle,
    DailyCheckInPhotoKind,
    DailyCheckInStatus,
    MediaFile,
    MediaFileOwnerType,
)
from app.dependencies import get_current_courier, get_current_courier_from_query
from app.schemas.daily_checkin import (
    CheckInPhotoResponse,
    CheckInResponse,
    CheckInStatusResponse,
    StartCheckInRequest,
)
from app.services.azure_blob_service import upload_blob
from app.services.sse_manager import driver_sse_manager

router = APIRouter(prefix="/courier/daily-checkin", tags=["Courier - Daily Check-in"])

REQUIRED_PHOTO_KINDS = frozenset({
    DailyCheckInPhotoKind.SELFIE,
    DailyCheckInPhotoKind.VEHICLE_FRONT,
    DailyCheckInPhotoKind.VEHICLE_LEFT,
    DailyCheckInPhotoKind.VEHICLE_RIGHT,
    DailyCheckInPhotoKind.VEHICLE_REAR,
    DailyCheckInPhotoKind.VEHICLE_CARGO,
})

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _get_missing_photos(photos: list[CourierDailyCheckInPhoto]) -> list[str]:
    uploaded_kinds = {p.kind for p in photos}
    return [k.value for k in REQUIRED_PHOTO_KINDS if k not in uploaded_kinds]


def _checkin_to_response(checkin: CourierDailyCheckIn) -> CheckInResponse:
    photos = [
        CheckInPhotoResponse(
            kind=p.kind.value,
            media_id=str(p.media_id),
            uploaded_at=p.uploaded_at,
        )
        for p in checkin.photos
    ]
    missing = _get_missing_photos(checkin.photos)
    return CheckInResponse(
        id=str(checkin.id),
        vehicle_id=str(checkin.vehicle_id),
        check_date=checkin.check_date,
        status=checkin.status.value,
        started_at=checkin.started_at,
        completed_at=checkin.completed_at,
        photos=photos,
        missing_photos=missing,
        reject_reason=checkin.reject_reason,
    )


@router.get("/today", response_model=CheckInStatusResponse)
async def get_today_checkin(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get today's check-in status for current courier."""
    today = date.today()
    result = await db.execute(
        select(CourierDailyCheckIn)
        .options(selectinload(CourierDailyCheckIn.photos))
        .where(
            CourierDailyCheckIn.courier_id == courier.id,
            CourierDailyCheckIn.check_date == today,
        )
        .order_by(CourierDailyCheckIn.started_at.desc())
        .limit(1)
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        return CheckInStatusResponse(has_checkin=False, is_complete=False, checkin=None)
    is_complete = checkin.status == DailyCheckInStatus.APPROVED
    return CheckInStatusResponse(has_checkin=True, is_complete=is_complete, checkin=_checkin_to_response(checkin))


async def _sse_stream_for_courier(courier_id: UUID, queue: asyncio.Queue):
    courier_id_str = str(courier_id)
    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=settings.SSE_HEARTBEAT_INTERVAL)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
                continue
            event_name = payload.get("event", "message")
            data_str = json.dumps(payload, ensure_ascii=False)
            yield f"event: {event_name}\ndata: {data_str}\n\n"
    finally:
        driver_sse_manager.unsubscribe(courier_id_str, queue)


@router.get("/stream")
async def stream_daily_checkin_events(
    courier: Annotated[CourierAccount, Depends(get_current_courier_from_query)],
):
    """SSE stream for courier daily check-in status updates."""
    queue = driver_sse_manager.subscribe(str(courier.id))
    return StreamingResponse(
        _sse_stream_for_courier(courier.id, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/start", response_model=CheckInResponse, status_code=status.HTTP_201_CREATED)
async def start_checkin(
    body: StartCheckInRequest,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Start a new daily check-in for specified vehicle."""
    today = date.today()
    vehicle_id = UUID(body.vehicle_id)

    result = await db.execute(
        select(CourierVehicle).where(
            CourierVehicle.id == vehicle_id,
            CourierVehicle.courier_id == courier.id,
            CourierVehicle.is_active.is_(True),
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found or inactive")

    result = await db.execute(
        select(CourierDailyCheckIn)
        .options(selectinload(CourierDailyCheckIn.photos))
        .where(
            CourierDailyCheckIn.courier_id == courier.id,
            CourierDailyCheckIn.vehicle_id == vehicle_id,
            CourierDailyCheckIn.check_date == today,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        if existing.status in (DailyCheckInStatus.PENDING_REVIEW, DailyCheckInStatus.APPROVED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Check-in already submitted for this vehicle today",
            )
        return _checkin_to_response(existing)

    checkin = CourierDailyCheckIn(
        courier_id=courier.id,
        vehicle_id=vehicle_id,
        check_date=today,
        status=DailyCheckInStatus.PENDING,
        latitude=body.latitude,
        longitude=body.longitude,
    )
    db.add(checkin)
    await db.commit()
    await db.refresh(checkin, ["photos"])
    return _checkin_to_response(checkin)


@router.post("/{checkin_id}/photo/{kind}")
async def upload_checkin_photo(
    checkin_id: UUID,
    kind: str,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    """Upload a photo for daily check-in."""
    try:
        photo_kind = DailyCheckInPhotoKind(kind)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid photo kind. Must be one of: {[k.value for k in DailyCheckInPhotoKind]}",
        )

    result = await db.execute(
        select(CourierDailyCheckIn)
        .options(selectinload(CourierDailyCheckIn.photos))
        .where(
            CourierDailyCheckIn.id == checkin_id,
            CourierDailyCheckIn.courier_id == courier.id,
        )
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
    if checkin.status not in (DailyCheckInStatus.PENDING, DailyCheckInStatus.REJECTED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Check-in already submitted for review")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image files are allowed")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)} MB",
        )

    existing_photo = next((p for p in checkin.photos if p.kind == photo_kind), None)
    blob_path_prefix = f"couriers/{courier.id}/checkins/{checkin.check_date}/{photo_kind.value}_{checkin_id}"
    blob_path = upload_blob(blob_path_prefix, content, file.content_type)

    if existing_photo:
        result = await db.execute(select(MediaFile).where(MediaFile.id == existing_photo.media_id))
        media = result.scalar_one_or_none()
        if media:
            media.blob_path = blob_path
            media.content_type = file.content_type
    else:
        media = MediaFile(
            owner_type=MediaFileOwnerType.DAILY_CHECKIN,
            owner_id=checkin.id,
            kind=photo_kind.value,
            blob_path=blob_path,
            content_type=file.content_type,
        )
        db.add(media)
        await db.flush()
        photo = CourierDailyCheckInPhoto(checkin_id=checkin.id, kind=photo_kind, media_id=media.id)
        db.add(photo)

    await db.commit()
    await db.refresh(checkin, ["photos"])
    return _checkin_to_response(checkin)


@router.post("/{checkin_id}/complete", response_model=CheckInResponse)
async def complete_checkin(
    checkin_id: UUID,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Complete daily check-in. All required photos must be uploaded first."""
    result = await db.execute(
        select(CourierDailyCheckIn)
        .options(selectinload(CourierDailyCheckIn.photos))
        .where(
            CourierDailyCheckIn.id == checkin_id,
            CourierDailyCheckIn.courier_id == courier.id,
        )
    )
    checkin = result.scalar_one_or_none()
    if not checkin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
    if checkin.status not in (DailyCheckInStatus.PENDING, DailyCheckInStatus.REJECTED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Check-in already submitted for review")

    missing = _get_missing_photos(checkin.photos)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required photos: {missing}",
        )

    checkin.status = DailyCheckInStatus.PENDING_REVIEW
    checkin.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(checkin, ["photos"])
    return _checkin_to_response(checkin)


@router.get("/history", response_model=list[CheckInResponse])
async def get_checkin_history(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 30,
    offset: int = 0,
):
    """Get courier's check-in history."""
    result = await db.execute(
        select(CourierDailyCheckIn)
        .options(selectinload(CourierDailyCheckIn.photos))
        .where(CourierDailyCheckIn.courier_id == courier.id)
        .order_by(CourierDailyCheckIn.check_date.desc())
        .limit(limit)
        .offset(offset)
    )
    checkins = result.scalars().all()
    return [_checkin_to_response(c) for c in checkins]


@router.get("/media/{media_id}")
async def get_checkin_media(
    media_id: UUID,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get media file for courier's check-in."""
    from fastapi.responses import Response
    from app.services.azure_blob_service import download_blob

    result = await db.execute(
        select(MediaFile)
        .join(CourierDailyCheckInPhoto, CourierDailyCheckInPhoto.media_id == MediaFile.id)
        .join(CourierDailyCheckIn, CourierDailyCheckIn.id == CourierDailyCheckInPhoto.checkin_id)
        .where(
            MediaFile.id == media_id,
            CourierDailyCheckIn.courier_id == courier.id,
        )
    )
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    out = download_blob(media.blob_path)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found in storage")

    content, content_type = out
    return Response(content=content, media_type=media.content_type or content_type)
