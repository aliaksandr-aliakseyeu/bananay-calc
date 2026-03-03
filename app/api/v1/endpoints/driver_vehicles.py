"""Driver vehicles endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DriverAccount, DriverVehicle, MediaFile, MediaFileOwnerType
from app.db.models.enums import DriverAccountStatus
from app.dependencies import get_current_driver
from app.schemas.driver import (DriverVehicleCreate, DriverVehicleResponse,
                                DriverVehicleUpdate)
from app.services.azure_blob_service import (upload_vehicle_document,
                                             upload_vehicle_photo)

from .driver_common import MAX_FILE_SIZE

router = APIRouter()


@router.get("/vehicles", response_model=list[DriverVehicleResponse])
async def list_vehicles(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DriverVehicleResponse]:
    """List driver's vehicles."""
    result = await db.execute(
        select(DriverVehicle).where(DriverVehicle.driver_id == driver.id).order_by(DriverVehicle.created_at)
    )
    vehicles = result.scalars().all()
    return [DriverVehicleResponse.model_validate(v) for v in vehicles]


@router.post("/vehicles", response_model=DriverVehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    body: DriverVehicleCreate,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverVehicleResponse:
    """Add a vehicle."""
    if driver.status not in (DriverAccountStatus.DRAFT, DriverAccountStatus.PENDING_REVIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vehicles cannot be added in current status",
        )
    vehicle = DriverVehicle(
        driver_id=driver.id,
        plate_number=body.plate_number.strip(),
        model=body.model.strip() if body.model else None,
        capacity_kg=body.capacity_kg,
        capacity_m3=body.capacity_m3,
        body_type=body.body_type.strip() if body.body_type else None,
    )
    db.add(vehicle)
    await db.commit()
    await db.refresh(vehicle)
    return DriverVehicleResponse.model_validate(vehicle)


@router.get("/vehicles/{vehicle_id}", response_model=DriverVehicleResponse)
async def get_vehicle(
    vehicle_id: UUID,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverVehicleResponse:
    """Get one vehicle."""
    result = await db.execute(
        select(DriverVehicle).where(
            DriverVehicle.id == vehicle_id,
            DriverVehicle.driver_id == driver.id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return DriverVehicleResponse.model_validate(vehicle)


@router.patch("/vehicles/{vehicle_id}", response_model=DriverVehicleResponse)
async def update_vehicle(
    vehicle_id: UUID,
    body: DriverVehicleUpdate,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverVehicleResponse:
    """Update a vehicle."""
    result = await db.execute(
        select(DriverVehicle).where(
            DriverVehicle.id == vehicle_id,
            DriverVehicle.driver_id == driver.id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    if driver.status not in (DriverAccountStatus.DRAFT, DriverAccountStatus.PENDING_REVIEW):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit in current status")
    if body.plate_number is not None:
        vehicle.plate_number = body.plate_number.strip()
    if body.model is not None:
        vehicle.model = body.model.strip() or None
    if body.capacity_kg is not None:
        vehicle.capacity_kg = body.capacity_kg
    if body.capacity_m3 is not None:
        vehicle.capacity_m3 = body.capacity_m3
    if body.body_type is not None:
        vehicle.body_type = body.body_type.strip() or None
    if body.is_active is not None:
        vehicle.is_active = body.is_active
    await db.commit()
    await db.refresh(vehicle)
    return DriverVehicleResponse.model_validate(vehicle)


@router.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: UUID,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a vehicle."""
    result = await db.execute(
        select(DriverVehicle).where(
            DriverVehicle.id == vehicle_id,
            DriverVehicle.driver_id == driver.id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    if driver.status not in (DriverAccountStatus.DRAFT, DriverAccountStatus.PENDING_REVIEW):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete in current status")
    await db.delete(vehicle)
    await db.commit()


@router.post("/vehicles/{vehicle_id}/photo", response_model=DriverVehicleResponse)
async def upload_vehicle_photo_endpoint(
    vehicle_id: UUID,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> DriverVehicleResponse:
    """Upload a photo for the vehicle."""
    result = await db.execute(
        select(DriverVehicle).where(
            DriverVehicle.id == vehicle_id,
            DriverVehicle.driver_id == driver.id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    if driver.status not in (DriverAccountStatus.DRAFT, DriverAccountStatus.PENDING_REVIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot upload vehicle photo in current status",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max {MAX_FILE_SIZE // (1024*1024)} MB",
        )
    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed for vehicle photo",
        )
    try:
        blob_path, sha256 = upload_vehicle_photo(
            str(driver.id),
            str(vehicle_id),
            content,
            content_type,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    media = MediaFile(
        owner_type=MediaFileOwnerType.VEHICLE,
        owner_id=vehicle_id,
        kind="photo",
        blob_path=blob_path,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256,
    )
    db.add(media)
    await db.flush()
    vehicle.photo_media_id = media.id
    await db.commit()
    await db.refresh(vehicle)
    return DriverVehicleResponse.model_validate(vehicle)


@router.post("/vehicles/{vehicle_id}/sts", response_model=DriverVehicleResponse)
async def upload_vehicle_sts(
    vehicle_id: UUID,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> DriverVehicleResponse:
    """Upload STS (registration certificate) for the vehicle. Image or PDF."""
    result = await db.execute(
        select(DriverVehicle).where(
            DriverVehicle.id == vehicle_id,
            DriverVehicle.driver_id == driver.id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    if driver.status not in (DriverAccountStatus.DRAFT, DriverAccountStatus.PENDING_REVIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot upload STS in current status",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max {MAX_FILE_SIZE // (1024*1024)} MB",
        )
    content_type = file.content_type or "application/octet-stream"
    if not (
        content_type.startswith("image/")
        or content_type == "application/pdf"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image or PDF files are allowed for STS",
        )
    try:
        blob_path, sha256 = upload_vehicle_document(
            str(driver.id),
            str(vehicle_id),
            "sts",
            content,
            content_type,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    media = MediaFile(
        owner_type=MediaFileOwnerType.VEHICLE,
        owner_id=vehicle_id,
        kind="sts",
        blob_path=blob_path,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256,
    )
    db.add(media)
    await db.flush()
    vehicle.sts_media_id = media.id
    await db.commit()
    await db.refresh(vehicle)
    return DriverVehicleResponse.model_validate(vehicle)
