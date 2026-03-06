"""Courier documents and media endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import CourierAccount, CourierVehicle, MediaFile, MediaFileOwnerType
from app.db.models.enums import CourierAccountStatus
from app.dependencies import get_current_courier
from app.schemas.courier import CourierMediaFileResponse
from app.services.azure_blob_service import download_blob, upload_driver_document

from .courier_common import ALLOWED_DOCUMENT_KINDS, MAX_FILE_SIZE

router = APIRouter()


@router.post("/documents", response_model=CourierMediaFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    kind: str = Query(..., description="Document kind: selfie, license_front, license_back, etc."),
) -> CourierMediaFileResponse:
    """Upload a document/photo (Azure Blob)."""
    if courier.status not in (CourierAccountStatus.DRAFT, CourierAccountStatus.PENDING_REVIEW):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot upload in current status")
    kind_lower = kind.strip().lower()
    if kind_lower not in ALLOWED_DOCUMENT_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid kind. Allowed: {sorted(ALLOWED_DOCUMENT_KINDS)}",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max {MAX_FILE_SIZE // (1024*1024)} MB",
        )
    content_type = file.content_type or "application/octet-stream"

    try:
        blob_path, sha256 = upload_driver_document(
            str(courier.id),
            kind_lower,
            content,
            content_type,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))

    media = MediaFile(
        owner_type=MediaFileOwnerType.COURIER,
        owner_id=courier.id,
        kind=kind_lower,
        blob_path=blob_path,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return CourierMediaFileResponse.model_validate(media)


@router.get("/documents", response_model=list[CourierMediaFileResponse])
async def list_documents(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CourierMediaFileResponse]:
    """List courier's uploaded documents."""
    result = await db.execute(
        select(MediaFile).where(
            MediaFile.owner_type == MediaFileOwnerType.COURIER,
            MediaFile.owner_id == courier.id,
        ).order_by(MediaFile.created_at)
    )
    files = result.scalars().all()
    return [CourierMediaFileResponse.model_validate(f) for f in files]


@router.get("/media/{media_id}")
async def get_media(
    media_id: UUID,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Stream a media file belonging to the courier."""
    result = await db.execute(select(MediaFile).where(MediaFile.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if media.owner_type == MediaFileOwnerType.COURIER and media.owner_id == courier.id:
        pass
    elif media.owner_type == MediaFileOwnerType.VEHICLE:
        v_result = await db.execute(
            select(CourierVehicle).where(
                CourierVehicle.id == media.owner_id,
                CourierVehicle.courier_id == courier.id,
            )
        )
        if not v_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    out = download_blob(media.blob_path)
    if not out:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Storage unavailable")
    content, _ = out
    return Response(content=content, media_type=media.content_type or "application/octet-stream")
