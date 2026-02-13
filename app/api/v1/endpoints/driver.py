"""Driver onboarding: profile, vehicles, documents, submit for moderation."""
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import (APIRouter, Depends, File, HTTPException, Query, Response,
                     UploadFile, status)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import (DriverAccount, DriverApplication,
                           DriverApplicationStatus, DriverVehicle, MediaFile,
                           MediaFileOwnerType)
from app.db.models.enums import DriverAccountStatus
from app.dependencies import get_current_driver
from app.schemas.driver import (DriverApplicationResponse,
                                DriverMediaFileResponse, DriverProfileResponse,
                                DriverProfileUpdate, DriverVehicleCreate,
                                DriverVehicleResponse, DriverVehicleUpdate)
from app.services.azure_blob_service import (download_blob,
                                             upload_driver_document,
                                             upload_vehicle_document,
                                             upload_vehicle_photo)

router = APIRouter(prefix="/driver", tags=["Driver"])

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


async def _check_can_submit(
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


@router.get("/me", response_model=DriverProfileResponse)
async def get_me(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverProfileResponse:
    """Get current driver profile and onboarding status."""
    await db.refresh(driver, ["vehicles"])
    can_submit, required = await _check_can_submit(driver, db)
    return DriverProfileResponse(
        id=driver.id,
        phone_e164=driver.phone_e164,
        status=driver.status.value,
        full_name=driver.full_name,
        city=driver.city,
        street=driver.street,
        building=driver.building,
        apartment=driver.apartment,
        region_id=driver.region_id,
        payout_account=driver.payout_account,
        created_at=driver.created_at,
        updated_at=driver.updated_at,
        can_submit=can_submit,
        required_fields=required,
        required_document_kinds=sorted(REQUIRED_DRIVER_DOCUMENT_KINDS),
    )


@router.patch("/me", response_model=DriverProfileResponse)
async def update_me(
    body: DriverProfileUpdate,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverProfileResponse:
    """Update driver profile (only in draft / before submit)."""
    if driver.status not in (DriverAccountStatus.DRAFT, DriverAccountStatus.PENDING_REVIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profile cannot be edited in current status",
        )
    if body.full_name is not None:
        driver.full_name = body.full_name.strip() or None
    if body.city is not None:
        driver.city = body.city.strip() or None
    if body.street is not None:
        driver.street = body.street.strip() or None
    if body.building is not None:
        driver.building = body.building.strip() or None
    if body.apartment is not None:
        driver.apartment = body.apartment.strip() or None
    if body.region_id is not None:
        driver.region_id = body.region_id
    if body.payout_account is not None:
        driver.payout_account = body.payout_account.strip() or None
    await db.commit()
    await db.refresh(driver)
    can_submit, required = await _check_can_submit(driver, db)
    return DriverProfileResponse(
        id=driver.id,
        phone_e164=driver.phone_e164,
        status=driver.status.value,
        full_name=driver.full_name,
        city=driver.city,
        street=driver.street,
        building=driver.building,
        apartment=driver.apartment,
        region_id=driver.region_id,
        payout_account=driver.payout_account,
        created_at=driver.created_at,
        updated_at=driver.updated_at,
        can_submit=can_submit,
        required_fields=required,
        required_document_kinds=sorted(REQUIRED_DRIVER_DOCUMENT_KINDS),
    )


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


@router.post("/documents", response_model=DriverMediaFileResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    kind: str = Query(..., description="Document kind: selfie, license_front, sts, car_front, etc."),
) -> DriverMediaFileResponse:
    """Upload a document/photo (Azure Blob). kind: selfie, license_front, sts, car_front, etc."""
    if driver.status not in (DriverAccountStatus.DRAFT, DriverAccountStatus.PENDING_REVIEW):
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
            str(driver.id),
            kind_lower,
            content,
            content_type,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    media = MediaFile(
        owner_type=MediaFileOwnerType.DRIVER,
        owner_id=driver.id,
        kind=kind_lower,
        blob_path=blob_path,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return DriverMediaFileResponse.model_validate(media)


@router.get("/documents", response_model=list[DriverMediaFileResponse])
async def list_documents(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DriverMediaFileResponse]:
    """List driver's uploaded documents."""
    result = await db.execute(
        select(MediaFile).where(
            MediaFile.owner_type == MediaFileOwnerType.DRIVER,
            MediaFile.owner_id == driver.id,
        ).order_by(MediaFile.created_at)
    )
    files = result.scalars().all()
    return [DriverMediaFileResponse.model_validate(f) for f in files]


@router.get("/media/{media_id}")
async def get_media(
    media_id: UUID,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Stream a media file (document or vehicle photo) belonging to the driver."""
    result = await db.execute(select(MediaFile).where(MediaFile.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    if media.owner_type == MediaFileOwnerType.DRIVER and media.owner_id == driver.id:
        pass
    elif media.owner_type == MediaFileOwnerType.VEHICLE:
        v_result = await db.execute(
            select(DriverVehicle).where(
                DriverVehicle.id == media.owner_id,
                DriverVehicle.driver_id == driver.id,
            )
        )
        if not v_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    out = download_blob(media.blob_path)
    if not out:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage unavailable",
        )
    content, _ = out
    return Response(content=content, media_type=media.content_type or "application/octet-stream")


@router.get("/application", response_model=DriverApplicationResponse | None)
async def get_application(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverApplicationResponse | None:
    """Get current driver application (if any)."""
    result = await db.execute(
        select(DriverApplication).where(DriverApplication.driver_id == driver.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        return None
    return DriverApplicationResponse.model_validate(app)


@router.post("/application/submit", response_model=DriverApplicationResponse)
async def submit_application(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverApplicationResponse:
    """Submit for moderation. Creates/updates DriverApplication, sets status pending_review."""
    await db.refresh(driver, ["vehicles"])
    if driver.status == DriverAccountStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked")
    can_submit, required = await _check_can_submit(driver, db)
    if not can_submit:
        missing = [k for k, v in required.items() if not v]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fill required fields before submit: {', '.join(missing)}",
        )

    result = await db.execute(
        select(DriverApplication).where(DriverApplication.driver_id == driver.id)
    )
    app = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if app:
        if app.status == DriverApplicationStatus.PENDING_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already submitted for review",
            )
        if app.status == DriverApplicationStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already approved",
            )
        app.status = DriverApplicationStatus.PENDING_REVIEW
        app.submitted_at = now
        app.reject_reason = None
    else:
        app = DriverApplication(
            driver_id=driver.id,
            status=DriverApplicationStatus.PENDING_REVIEW,
            submitted_at=now,
        )
        db.add(app)
        await db.flush()

    driver.status = DriverAccountStatus.PENDING_REVIEW
    await db.commit()
    await db.refresh(app)
    return DriverApplicationResponse.model_validate(app)
