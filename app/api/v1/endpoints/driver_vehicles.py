"""Driver vehicles endpoints."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import (DriverAccount, DriverVehicle, MediaFile,
                           MediaFileOwnerType, VehicleCapability,
                           VehicleCompliance)
from app.db.models.enums import DriverAccountStatus, DriverVehicleStatus, VehicleBodyType
from app.dependencies import get_current_driver
from app.schemas.driver import (DriverVehicleCapabilitiesResponse,
                                DriverVehicleComplianceResponse,
                                DriverVehicleCreate, DriverVehicleResponse,
                                DriverVehicleUpdate)
from app.services.azure_blob_service import (upload_vehicle_document,
                                             upload_vehicle_photo)
from app.utils.vehicle import normalize_plate_number

from .driver_common import MAX_FILE_SIZE

router = APIRouter()

# Vehicle CRUD/uploads are allowed during onboarding and for approved drivers; blocked accounts only.
_DRIVER_STATUSES_ALLOWED_VEHICLE_WRITES: frozenset[DriverAccountStatus] = frozenset(
    {
        DriverAccountStatus.DRAFT,
        DriverAccountStatus.PENDING_REVIEW,
        DriverAccountStatus.ACTIVE,
    }
)


def _vehicle_loader():
    return (
        selectinload(DriverVehicle.capabilities),
        selectinload(DriverVehicle.compliance),
    )


async def _get_vehicle_or_404(
    vehicle_id: UUID,
    driver_id: UUID,
    db: AsyncSession,
) -> DriverVehicle:
    result = await db.execute(
        select(DriverVehicle)
        .options(*_vehicle_loader())
        .where(
            DriverVehicle.id == vehicle_id,
            DriverVehicle.driver_id == driver_id,
        )
    )
    vehicle = result.scalar_one_or_none()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle


def _resolve_status(explicit_status: int | None, current_status: int | None) -> int:
    if explicit_status is not None:
        return explicit_status
    if current_status is not None:
        return current_status
    return int(DriverVehicleStatus.ACTIVE)


def _ensure_related_records(vehicle: DriverVehicle) -> None:
    if vehicle.capabilities is None:
        vehicle.capabilities = VehicleCapability(
            vehicle_id=vehicle.id,
            payload_kg=1,
            cargo_volume_m3=None,
        )
    # Async session: never touch vehicle.compliance if lazy-loaded (MissingGreenlet).
    inst = inspect(vehicle)
    if "compliance" in inst.unloaded:
        vehicle.compliance = VehicleCompliance(vehicle_id=vehicle.id)
    elif vehicle.compliance is None:
        vehicle.compliance = VehicleCompliance(vehicle_id=vehicle.id)


def _apply_capability_updates(vehicle: DriverVehicle, body: DriverVehicleUpdate | DriverVehicleCreate) -> None:
    _ensure_related_records(vehicle)
    capabilities = vehicle.capabilities
    assert capabilities is not None

    nested_capabilities = getattr(body, "capabilities", None)
    if not nested_capabilities:
        return
    for field in nested_capabilities.model_fields_set:
        setattr(capabilities, field, getattr(nested_capabilities, field))


def _apply_compliance_updates(vehicle: DriverVehicle, body: DriverVehicleUpdate) -> None:
    nested_compliance = body.compliance
    if not nested_compliance:
        return
    _ensure_related_records(vehicle)
    compliance = vehicle.compliance
    assert compliance is not None
    for field in nested_compliance.model_fields_set:
        setattr(compliance, field, getattr(nested_compliance, field))


def _serialize_capabilities(vehicle: DriverVehicle) -> DriverVehicleCapabilitiesResponse | None:
    capabilities = vehicle.capabilities
    if capabilities is None:
        return None
    return DriverVehicleCapabilitiesResponse.model_validate(capabilities)


def _serialize_compliance(vehicle: DriverVehicle) -> DriverVehicleComplianceResponse | None:
    compliance = vehicle.compliance
    if compliance is None:
        return None
    return DriverVehicleComplianceResponse.model_validate(compliance)


def _vehicle_submit_readiness_errors(vehicle: DriverVehicle) -> list[str]:
    """Return field keys blocking submit-for-verification (driver-facing)."""
    missing: list[str] = []
    if not (vehicle.plate_number or "").strip():
        missing.append("plate_number")
    if vehicle.body_type_code is None:
        missing.append("body_type_code")
    elif vehicle.body_type_code == int(VehicleBodyType.UNKNOWN):
        missing.append("body_type_code")
    if vehicle.photo_media_id is None:
        missing.append("photo")
    if vehicle.sts_media_id is None:
        missing.append("sts")
    cap = vehicle.capabilities
    if cap is None or cap.payload_kg is None or cap.payload_kg < 1:
        missing.append("payload_kg")
    if cap is None or cap.cargo_volume_m3 is None or cap.cargo_volume_m3 <= 0:
        missing.append("cargo_volume_m3")
    if cap is not None and cap.has_refrigerator and (cap.min_temp_c is None or cap.max_temp_c is None):
        missing.append("temperature_range")
    return missing


def _serialize_vehicle(vehicle: DriverVehicle) -> DriverVehicleResponse:
    plate_number_normalized = vehicle.plate_number_normalized or normalize_plate_number(vehicle.plate_number)
    return DriverVehicleResponse(
        id=vehicle.id,
        driver_id=vehicle.driver_id,
        plate_number=vehicle.plate_number,
        plate_number_normalized=plate_number_normalized,
        brand=vehicle.brand,
        model=vehicle.model,
        vin=vehicle.vin,
        year=vehicle.year,
        body_type_code=vehicle.body_type_code,
        status=vehicle.status,
        photo_media_id=vehicle.photo_media_id,
        sts_media_id=vehicle.sts_media_id,
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
        capabilities=_serialize_capabilities(vehicle),
        compliance=_serialize_compliance(vehicle),
    )


async def _mark_media_superseded(
    old_media_id: UUID | None,
    new_media_id: UUID,
    db: AsyncSession,
) -> None:
    if old_media_id is None or old_media_id == new_media_id:
        return
    old_media = await db.get(MediaFile, old_media_id)
    if old_media:
        old_media.is_current = False
        old_media.superseded_by_media_id = new_media_id


@router.get("/vehicles", response_model=list[DriverVehicleResponse])
async def list_vehicles(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DriverVehicleResponse]:
    """List driver's vehicles."""
    result = await db.execute(
        select(DriverVehicle)
        .options(*_vehicle_loader())
        .where(DriverVehicle.driver_id == driver.id)
        .order_by(DriverVehicle.created_at)
    )
    vehicles = result.scalars().all()
    return [_serialize_vehicle(v) for v in vehicles]


@router.post("/vehicles", response_model=DriverVehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    body: DriverVehicleCreate,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverVehicleResponse:
    """Add a vehicle."""
    if driver.status not in _DRIVER_STATUSES_ALLOWED_VEHICLE_WRITES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vehicles cannot be added in current status",
        )
    status_code = _resolve_status(body.status, None)
    vehicle = DriverVehicle(
        driver_id=driver.id,
        plate_number=body.plate_number.strip(),
        plate_number_normalized=normalize_plate_number(body.plate_number),
        brand=body.brand.strip() if body.brand else None,
        model=body.model.strip() if body.model else None,
        vin=body.vin.strip().upper() if body.vin else None,
        year=body.year,
        body_type_code=body.body_type_code or int(VehicleBodyType.UNKNOWN),
        status=status_code,
    )
    vehicle.normalize_plate()
    db.add(vehicle)
    await db.flush()
    vehicle.capabilities = VehicleCapability(
        vehicle_id=vehicle.id,
        payload_kg=body.capabilities.payload_kg,
        cargo_volume_m3=body.capabilities.cargo_volume_m3,
    )
    _apply_capability_updates(vehicle, body)
    if body.compliance is not None:
        vehicle.compliance = VehicleCompliance(
            vehicle_id=vehicle.id,
            verification_status=body.compliance.verification_status,
        )
        for field in body.compliance.model_fields_set:
            setattr(vehicle.compliance, field, getattr(body.compliance, field))
    await db.commit()
    vehicle = await _get_vehicle_or_404(vehicle.id, driver.id, db)
    return _serialize_vehicle(vehicle)


@router.get("/vehicles/{vehicle_id}", response_model=DriverVehicleResponse)
async def get_vehicle(
    vehicle_id: UUID,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverVehicleResponse:
    """Get one vehicle."""
    vehicle = await _get_vehicle_or_404(vehicle_id, driver.id, db)
    return _serialize_vehicle(vehicle)


@router.patch("/vehicles/{vehicle_id}", response_model=DriverVehicleResponse)
async def update_vehicle(
    vehicle_id: UUID,
    body: DriverVehicleUpdate,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverVehicleResponse:
    """Update a vehicle."""
    vehicle = await _get_vehicle_or_404(vehicle_id, driver.id, db)
    if driver.status not in _DRIVER_STATUSES_ALLOWED_VEHICLE_WRITES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot edit in current status")
    if body.plate_number is not None:
        vehicle.plate_number = body.plate_number.strip()
        vehicle.plate_number_normalized = normalize_plate_number(vehicle.plate_number)
    if body.brand is not None:
        vehicle.brand = body.brand.strip() or None
    if body.model is not None:
        vehicle.model = body.model.strip() or None
    if body.vin is not None:
        vehicle.vin = body.vin.strip().upper() or None
    if body.year is not None:
        vehicle.year = body.year
    if body.body_type_code is not None:
        vehicle.body_type_code = body.body_type_code
    vehicle.status = _resolve_status(body.status, vehicle.status)
    _apply_capability_updates(vehicle, body)
    _apply_compliance_updates(vehicle, body)
    vehicle.normalize_plate()
    await db.commit()
    vehicle = await _get_vehicle_or_404(vehicle.id, driver.id, db)
    return _serialize_vehicle(vehicle)


@router.post(
    "/vehicles/{vehicle_id}/submit-for-verification",
    response_model=DriverVehicleResponse,
)
async def submit_vehicle_for_verification(
    vehicle_id: UUID,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverVehicleResponse:
    """Move this vehicle to pending verification after required fields and media are set."""
    if driver.status not in _DRIVER_STATUSES_ALLOWED_VEHICLE_WRITES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot submit vehicle in current status")
    vehicle = await _get_vehicle_or_404(vehicle_id, driver.id, db)
    if vehicle.status == int(DriverVehicleStatus.PENDING_VERIFICATION):
        return _serialize_vehicle(vehicle)
    if vehicle.status not in (
        int(DriverVehicleStatus.DRAFT),
        int(DriverVehicleStatus.ACTIVE),
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle cannot be submitted for verification in current status",
        )
    missing = _vehicle_submit_readiness_errors(vehicle)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing or invalid: {', '.join(missing)}",
        )
    vehicle.status = int(DriverVehicleStatus.PENDING_VERIFICATION)
    _ensure_related_records(vehicle)
    if vehicle.compliance is not None:
        vehicle.compliance.verification_status = 1
        vehicle.compliance.verification_reject_reason = None
        vehicle.compliance.verified_at = None
    await db.commit()
    vehicle = await _get_vehicle_or_404(vehicle.id, driver.id, db)
    return _serialize_vehicle(vehicle)


@router.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: UUID,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a vehicle."""
    vehicle = await _get_vehicle_or_404(vehicle_id, driver.id, db)
    if driver.status not in _DRIVER_STATUSES_ALLOWED_VEHICLE_WRITES:
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
    vehicle = await _get_vehicle_or_404(vehicle_id, driver.id, db)
    if driver.status not in _DRIVER_STATUSES_ALLOWED_VEHICLE_WRITES:
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
    await _mark_media_superseded(vehicle.photo_media_id, media.id, db)
    vehicle.photo_media_id = media.id
    await db.commit()
    vehicle = await _get_vehicle_or_404(vehicle.id, driver.id, db)
    return _serialize_vehicle(vehicle)


@router.post("/vehicles/{vehicle_id}/sts", response_model=DriverVehicleResponse)
async def upload_vehicle_sts(
    vehicle_id: UUID,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> DriverVehicleResponse:
    """Upload STS (registration certificate) for the vehicle. Image or PDF."""
    vehicle = await _get_vehicle_or_404(vehicle_id, driver.id, db)
    if driver.status not in _DRIVER_STATUSES_ALLOWED_VEHICLE_WRITES:
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
    await _mark_media_superseded(vehicle.sts_media_id, media.id, db)
    vehicle.sts_media_id = media.id
    await db.commit()
    vehicle = await _get_vehicle_or_404(vehicle.id, driver.id, db)
    return _serialize_vehicle(vehicle)
