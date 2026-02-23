"""Driver delivery tasks endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.base import get_db
from app.db.models import DriverAccount, DriverDeliveryTask, MediaFile
from app.db.models.enums import DriverAccountStatus, MediaFileOwnerType
from app.dependencies import get_current_driver
from app.schemas.driver_delivery_task import (
    CompletedTaskResponse,
    DCDeliveryResponse,
    DeliveryTaskItem,
    DriverDeliveryTaskResponse,
)
from app.schemas.driver_location import (
    DriverLocationConfigResponse,
    DriverLocationReport,
)
from app.services.azure_blob_service import upload_driver_task_photo
from app.services.delivery_task_service import DeliveryTaskService
from app.services.driver_location_service import report_location

from .driver_common import MAX_FILE_SIZE

router = APIRouter()


@router.get(
    "/delivery-tasks",
    response_model=list[DriverDeliveryTaskResponse],
    summary="Get available delivery tasks",
)
async def get_delivery_tasks(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DriverDeliveryTaskResponse]:
    """
    Get delivery tasks for driver: warehouse pickup -> DC deliveries.

    Returns orders in PENDING or IN_TRANSIT_TO_DC status, aggregated by
    warehouse and distribution center. Each task shows what to pick up
    and where to deliver.
    """
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can view delivery tasks",
        )
    service = DeliveryTaskService(db)
    tasks = await service.get_available_tasks_for_driver()

    return [
        DriverDeliveryTaskResponse(
            task_id=t.task_id,
            order_id=t.order_id,
            order_number=t.order_number,
            warehouse_lat=t.warehouse_lat,
            warehouse_lon=t.warehouse_lon,
            deliveries=[
                DCDeliveryResponse(
                    dc_id=d.dc_id,
                    dc_name=d.dc_name,
                    dc_address=d.dc_address,
                    dc_lat=d.dc_lat,
                    dc_lon=d.dc_lon,
                    items=[
                        DeliveryTaskItem(
                            sku_name=i.sku_name,
                            sku_code=i.sku_code or "",
                            quantity=i.quantity,
                        )
                        for i in d.items
                    ],
                )
                for d in t.deliveries
            ],
        )
        for t in tasks
    ]


@router.get(
    "/delivery-tasks/completed",
    response_model=list[CompletedTaskResponse],
    summary="Get my completed delivery tasks (history)",
)
async def get_completed_delivery_tasks(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CompletedTaskResponse]:
    """
    Get delivery tasks completed by the current driver (history).

    Returns tasks with status DELIVERED, ordered by delivered_at descending.
    """
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can view history",
        )
    service = DeliveryTaskService(db)
    rows = await service.get_completed_tasks_for_driver(driver.id)
    return [
        CompletedTaskResponse(
            task_id=task_id,
            order_id=order_id,
            order_number=order_number,
            delivered_at=delivered_at,
        )
        for task_id, order_id, order_number, delivered_at in rows
    ]


@router.get(
    "/delivery-tasks/my",
    response_model=list[DriverDeliveryTaskResponse],
    summary="Get my assigned delivery tasks",
)
async def get_my_delivery_tasks(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DriverDeliveryTaskResponse]:
    """
    Get delivery tasks assigned to the current driver (in progress).

    Returns tasks the driver has taken, not yet completed.
    """
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can view their tasks",
        )
    service = DeliveryTaskService(db)
    tasks = await service.get_my_assigned_tasks_for_driver(driver.id)

    return [
        DriverDeliveryTaskResponse(
            task_id=t.task_id,
            order_id=t.order_id,
            order_number=t.order_number,
            warehouse_lat=t.warehouse_lat,
            warehouse_lon=t.warehouse_lon,
            deliveries=[
                DCDeliveryResponse(
                    dc_id=d.dc_id,
                    dc_name=d.dc_name,
                    dc_address=d.dc_address,
                    dc_lat=d.dc_lat,
                    dc_lon=d.dc_lon,
                    items=[
                        DeliveryTaskItem(
                            sku_name=i.sku_name,
                            sku_code=i.sku_code or "",
                            quantity=i.quantity,
                        )
                        for i in d.items
                    ],
                    status=getattr(d, "dc_status", None),
                    delivered_at=getattr(d, "dc_delivered_at", None),
                    unload_photo_media_id=getattr(d, "unload_photo_media_id", None),
                )
                for d in t.deliveries
            ],
            status=t.status,
            loading_photo_media_id=getattr(t, "loading_photo_media_id", None),
        )
        for t in tasks
    ]


@router.post(
    "/delivery-tasks/{task_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel (release) assigned delivery task",
)
async def cancel_delivery_task(
    task_id: int,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Cancel assigned task. Only allowed before goods are loaded at warehouse.
    Returns order to pending state.
    """
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can cancel tasks",
        )
    service = DeliveryTaskService(db)
    task = await service.release_task(task_id, driver.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task not found, not assigned to you, or cannot be cancelled (already loaded)",
        )
    await db.commit()
    return {"task_id": task.id, "status": "released"}


@router.get(
    "/delivery-tasks/location-config",
    response_model=DriverLocationConfigResponse,
    summary="Get location tracking config (client hints)",
)
async def get_location_config() -> DriverLocationConfigResponse:
    """
    Returns config for driver app: how often to send location, poll interval, stale threshold.
    """
    return DriverLocationConfigResponse(
        send_interval_sec=settings.DRIVER_LOCATION_SEND_INTERVAL_SEC,
        poll_interval_sec=settings.DRIVER_LOCATION_POLL_INTERVAL_SEC,
        stale_after_sec=settings.DRIVER_LOCATION_STALE_AFTER_SEC,
    )


@router.post(
    "/delivery-tasks/{task_id}/location",
    status_code=status.HTTP_200_OK,
    summary="Report current location for a task",
)
async def post_location(
    task_id: int,
    body: DriverLocationReport,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Report driver's current location for an assigned task.
    Updates last location for this order and broadcasts to producers via SSE.
    """
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can report location",
        )
    order_id = await report_location(
        db=db,
        driver_id=driver.id,
        task_id=task_id,
        lat=body.lat,
        lon=body.lon,
        accuracy=body.accuracy,
        device_info=body.device_info,
    )
    if order_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not assigned to you",
        )
    await db.commit()
    return {"order_id": order_id, "lat": body.lat, "lon": body.lon}


@router.post(
    "/delivery-tasks/{task_id}/take",
    status_code=status.HTTP_200_OK,
    summary="Take a delivery task",
)
async def take_delivery_task(
    task_id: int,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Take (claim) a delivery task. Assigns the current driver to the task.
    """
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can take delivery tasks",
        )
    service = DeliveryTaskService(db)
    task = await service.take_task(task_id, driver.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task not found or already taken by another driver",
        )
    await db.commit()
    return {"task_id": task.id, "status": "assigned"}


@router.post(
    "/delivery-tasks/{task_id}/start-loading",
    status_code=status.HTTP_200_OK,
    summary="Start loading at warehouse",
)
async def start_loading(
    task_id: int,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Mark that loading has started at the warehouse (driver arrived and is loading)."""
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can update task",
        )
    service = DeliveryTaskService(db)
    task = await service.start_loading(task_id, driver.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task not found, not assigned to you, or invalid state (must be assigned)",
        )
    await db.commit()
    return {"task_id": task.id, "status": "loading"}


@router.post(
    "/delivery-tasks/{task_id}/upload-loading-photo",
    response_model=DriverDeliveryTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload optional loading photo for task",
)
async def upload_loading_photo(
    task_id: int,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> DriverDeliveryTaskResponse:
    """
    Upload a photo confirming loading at warehouse. Only allowed when task status is loading.
    Task must be assigned to the current driver.
    """
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can upload loading photo",
        )
    result = await db.execute(
        select(DriverDeliveryTask)
        .where(
            DriverDeliveryTask.id == task_id,
            DriverDeliveryTask.driver_id == driver.id,
            DriverDeliveryTask.status == "loading",
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found, not assigned to you, or status is not loading",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )
    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed for loading photo",
        )
    try:
        blob_path, sha256 = upload_driver_task_photo(
            str(driver.id),
            task_id,
            "loading",
            content,
            content_type,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    if task.media_owner_uuid is None:
        task.media_owner_uuid = uuid.uuid4()
    media = MediaFile(
        owner_type=MediaFileOwnerType.DRIVER_DELIVERY_TASK,
        owner_id=task.media_owner_uuid,
        kind="loading",
        blob_path=blob_path,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256,
    )
    db.add(media)
    await db.flush()
    task.loading_photo_media_id = media.id
    await db.commit()
    await db.refresh(task)
    service = DeliveryTaskService(db)
    my_tasks = await service.get_my_assigned_tasks_for_driver(driver.id)
    for t in my_tasks:
        if t.task_id == task_id:
            return DriverDeliveryTaskResponse(
                task_id=t.task_id,
                order_id=t.order_id,
                order_number=t.order_number,
                warehouse_lat=t.warehouse_lat,
                warehouse_lon=t.warehouse_lon,
                deliveries=[
                    DCDeliveryResponse(
                        dc_id=d.dc_id,
                        dc_name=d.dc_name,
                        dc_address=d.dc_address,
                        dc_lat=d.dc_lat,
                        dc_lon=d.dc_lon,
                        items=[
                            DeliveryTaskItem(
                                sku_name=i.sku_name,
                                sku_code=i.sku_code or "",
                                quantity=i.quantity,
                            )
                            for i in d.items
                        ],
                        status=getattr(d, "dc_status", None),
                        delivered_at=getattr(d, "dc_delivered_at", None),
                    )
                    for d in t.deliveries
                ],
                status=t.status,
                loading_photo_media_id=t.loading_photo_media_id,
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found after update")


@router.post(
    "/delivery-tasks/{task_id}/depart",
    status_code=status.HTTP_200_OK,
    summary="Depart from warehouse",
)
async def depart_from_warehouse(
    task_id: int,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Mark that loading is complete and driver has departed from the warehouse."""
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can update task",
        )
    service = DeliveryTaskService(db)
    task = await service.depart_from_warehouse(task_id, driver.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task not found, not assigned to you, or invalid state (must be loading)",
        )
    await db.commit()
    return {"task_id": task.id, "status": "in_transit"}


@router.post(
    "/delivery-tasks/{task_id}/dc/{dc_id}/unload",
    status_code=status.HTTP_200_OK,
    summary="Mark DC as unloaded",
)
async def unload_at_dc(
    task_id: int,
    dc_id: int,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Mark that goods have been unloaded at this distribution center."""
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can update task",
        )
    service = DeliveryTaskService(db)
    task = await service.unload_at_dc(task_id, dc_id, driver.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task not found, not assigned to you, DC not in task, or already unloaded",
        )
    await db.commit()
    return {"task_id": task.id, "dc_id": dc_id, "status": "delivered"}


@router.post(
    "/delivery-tasks/{task_id}/complete",
    status_code=status.HTTP_200_OK,
    summary="Complete task (after all DCs unloaded)",
)
async def complete_task(
    task_id: int,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Manually complete the task after all DCs are unloaded.
    Allows driver to add photos before closing the order.
    """
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can complete task",
        )
    service = DeliveryTaskService(db)
    task = await service.complete_task(task_id, driver.id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task not found, not assigned to you, or not all DCs unloaded yet",
        )
    await db.commit()
    return {"task_id": task.id, "status": "delivered"}


@router.post(
    "/delivery-tasks/{task_id}/dc/{dc_id}/upload-unload-photo",
    response_model=DriverDeliveryTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload optional unload photo for DC",
)
async def upload_unload_photo(
    task_id: int,
    dc_id: int,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> DriverDeliveryTaskResponse:
    """
    Upload a photo confirming unload at this DC. Only allowed when DC is already marked as delivered.
    Task must be assigned to the current driver.
    """
    if driver.status != DriverAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active drivers can upload unload photo",
        )
    result = await db.execute(
        select(DriverDeliveryTask)
        .where(
            DriverDeliveryTask.id == task_id,
            DriverDeliveryTask.driver_id == driver.id,
        )
        .options(selectinload(DriverDeliveryTask.dc_deliveries))
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found or not assigned to you",
        )
    dc_delivery = next((d for d in task.dc_deliveries if d.dc_id == dc_id), None)
    if not dc_delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="DC not in this task",
        )
    if dc_delivery.status != "delivered":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only upload unload photo after DC is marked as delivered",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )
    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are allowed for unload photo",
        )
    try:
        blob_path, sha256 = upload_driver_task_photo(
            str(driver.id),
            task_id,
            f"unload_dc_{dc_id}",
            content,
            content_type,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    if task.media_owner_uuid is None:
        task.media_owner_uuid = uuid.uuid4()
    media = MediaFile(
        owner_type=MediaFileOwnerType.DRIVER_DELIVERY_TASK,
        owner_id=task.media_owner_uuid,
        kind=f"unload_dc_{dc_id}",
        blob_path=blob_path,
        content_type=content_type,
        size_bytes=len(content),
        sha256=sha256,
    )
    db.add(media)
    await db.flush()
    dc_delivery.unload_photo_media_id = media.id
    await db.commit()
    service = DeliveryTaskService(db)
    my_tasks = await service.get_my_assigned_tasks_for_driver(driver.id)
    for t in my_tasks:
        if t.task_id == task_id:
            return DriverDeliveryTaskResponse(
                task_id=t.task_id,
                order_id=t.order_id,
                order_number=t.order_number,
                warehouse_lat=t.warehouse_lat,
                warehouse_lon=t.warehouse_lon,
                deliveries=[
                    DCDeliveryResponse(
                        dc_id=d.dc_id,
                        dc_name=d.dc_name,
                        dc_address=d.dc_address,
                        dc_lat=d.dc_lat,
                        dc_lon=d.dc_lon,
                        items=[
                            DeliveryTaskItem(
                                sku_name=i.sku_name,
                                sku_code=i.sku_code or "",
                                quantity=i.quantity,
                            )
                            for i in d.items
                        ],
                        status=getattr(d, "dc_status", None),
                        delivered_at=getattr(d, "dc_delivered_at", None),
                        unload_photo_media_id=getattr(d, "unload_photo_media_id", None),
                    )
                    for d in t.deliveries
                ],
                status=t.status,
                loading_photo_media_id=t.loading_photo_media_id,
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found after update")
