"""Courier delivery tasks endpoints."""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from geoalchemy2.shape import to_shape
from sqlalchemy import and_, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.base import get_db
from app.db.models import (CourierAccount, CourierDeliveryTask, DistributionCenter,
                           MediaFile, MediaFileOwnerType)
from app.db.models.delivery_order import (DeliveryOrder, DeliveryOrderItem,
                                          DeliveryOrderItemPoint,
                                          DeliveryOrderItemPointScanEvent,
                                          DeliveryPointStatus, ItemPointScanPhase)
from app.db.models.enums import CourierAccountStatus, CourierTaskStatus
from app.dependencies import get_current_courier, get_current_courier_from_query
from app.schemas.courier_delivery_task import (AvailableCourierTask,
                                               CompletedCourierTaskResponse,
                                               ConfirmDeliveryRequest,
                                               CourierDeliveryTaskResponse)
from app.schemas.driver_location import (DriverLocationConfigResponse,
                                         DriverLocationReport)
from app.services.azure_blob_service import upload_blob
from app.services.driver_location_service import report_location
from app.services.sse_manager import driver_sse_manager

from .courier_common import MAX_FILE_SIZE

router = APIRouter()


async def _build_task_response(
    task: CourierDeliveryTask,
    db: AsyncSession,
) -> CourierDeliveryTaskResponse:
    """Build a full CourierDeliveryTaskResponse from a task row."""
    item_point_result = await db.execute(
        select(DeliveryOrderItemPoint)
        .options(
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(DeliveryOrderItem.order),
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(DeliveryOrderItem.producer_sku),
            selectinload(DeliveryOrderItemPoint.delivery_point),
        )
        .where(DeliveryOrderItemPoint.id == task.item_point_id)
    )
    item_point = item_point_result.scalar_one_or_none()
    if not item_point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item point not found")

    from app.db.models.delivery_task import DeliveryOrderItemDCAllocation
    alloc_result = await db.execute(
        select(DeliveryOrderItemDCAllocation, DistributionCenter)
        .join(DistributionCenter, DistributionCenter.id == DeliveryOrderItemDCAllocation.dc_id)
        .where(DeliveryOrderItemDCAllocation.order_item_id == item_point.order_item_id)
        .limit(1)
    )
    alloc_row = alloc_result.first()
    dc = alloc_row[1] if alloc_row else None

    dp = item_point.delivery_point
    order = item_point.order_item.order
    sku = item_point.order_item.producer_sku

    dc_address = dc.address if dc else None
    dp_address = getattr(dp, "address", None)
    dc_lat = float(to_shape(dc.location).y) if dc and dc.location else 0.0
    dc_lon = float(to_shape(dc.location).x) if dc and dc.location else 0.0
    dp_lat = float(to_shape(dp.location).y) if dp and dp.location else 0.0
    dp_lon = float(to_shape(dp.location).x) if dp and dp.location else 0.0
    return CourierDeliveryTaskResponse(
        task_id=task.id,
        item_point_id=task.item_point_id,
        order_id=order.id,
        order_number=order.order_number,
        status=task.status if isinstance(task.status, str) else task.status.value,
        dc_id=dc.id if dc else 0,
        dc_name=dc.name if dc else "",
        dc_address=dc_address,
        dc_lat=dc_lat,
        dc_lon=dc_lon,
        delivery_point_id=dp.id if dp else 0,
        delivery_point_name=getattr(dp, "name", None) or getattr(dp, "title", None),
        delivery_point_address=dp_address,
        delivery_point_lat=dp_lat,
        delivery_point_lon=dp_lon,
        sku_name=sku.name if sku else None,
        quantity=item_point.quantity,
        taken_at=task.taken_at,
        in_transit_at=task.in_transit_at,
        delivered_at=task.delivered_at,
        qr_scanned=task.qr_scanned,
        qr_token=item_point.qr_token,
        delivery_photo_media_id=task.delivery_photo_media_id,
        from_address=dc_address,
        from_lat=dc_lat,
        from_lon=dc_lon,
        to_address=dp_address,
        to_lat=dp_lat,
        to_lon=dp_lon,
    )


@router.get(
    "/delivery-tasks",
    response_model=list[AvailableCourierTask],
    summary="Get available delivery tasks for courier",
)
async def get_available_tasks(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AvailableCourierTask]:
    """
    Get item points available for courier pickup.

    Returns item points where latest scan phase is sorted_to_zone
    and no active (non-failed) CourierDeliveryTask exists.
    """
    if courier.status != CourierAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active couriers can view delivery tasks",
        )

    active_task_subq = (
        select(CourierDeliveryTask.item_point_id)
        .where(CourierDeliveryTask.status != CourierTaskStatus.DELIVERED.value)
        .scalar_subquery()
    )

    result = await db.execute(
        select(DeliveryOrderItemPoint)
        .options(
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(DeliveryOrderItem.order),
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(DeliveryOrderItem.producer_sku),
            selectinload(DeliveryOrderItemPoint.delivery_point),
            selectinload(DeliveryOrderItemPoint.scan_events),
        )
        .where(
            DeliveryOrderItemPoint.status == DeliveryPointStatus.AT_DC,
            not_(DeliveryOrderItemPoint.id.in_(active_task_subq)),
        )
    )
    item_points = result.scalars().all()

    from app.db.models.delivery_task import DeliveryOrderItemDCAllocation

    out: list[AvailableCourierTask] = []
    for ip in item_points:
        if not ip.scan_events:
            continue
        latest_phase = max(ip.scan_events, key=lambda e: e.scanned_at).phase
        if latest_phase != ItemPointScanPhase.SORTED_TO_ZONE:
            continue

        alloc_result = await db.execute(
            select(DeliveryOrderItemDCAllocation, DistributionCenter)
            .join(DistributionCenter, DistributionCenter.id == DeliveryOrderItemDCAllocation.dc_id)
            .where(DeliveryOrderItemDCAllocation.order_item_id == ip.order_item_id)
            .limit(1)
        )
        alloc_row = alloc_result.first()
        dc = alloc_row[1] if alloc_row else None

        dp = ip.delivery_point
        order = ip.order_item.order
        sku = ip.order_item.producer_sku

        dc_address = dc.address if dc else None
        dp_address = getattr(dp, "address", None)
        dc_lat = float(to_shape(dc.location).y) if dc and dc.location else 0.0
        dc_lon = float(to_shape(dc.location).x) if dc and dc.location else 0.0
        dp_lat = float(to_shape(dp.location).y) if dp and dp.location else 0.0
        dp_lon = float(to_shape(dp.location).x) if dp and dp.location else 0.0
        out.append(AvailableCourierTask(
            item_point_id=ip.id,
            order_id=order.id,
            order_number=order.order_number,
            dc_id=dc.id if dc else 0,
            dc_name=dc.name if dc else "",
            dc_address=dc_address,
            dc_lat=dc_lat,
            dc_lon=dc_lon,
            delivery_point_id=dp.id if dp else 0,
            delivery_point_name=getattr(dp, "name", None) or getattr(dp, "title", None),
            delivery_point_address=dp_address,
            delivery_point_lat=dp_lat,
            delivery_point_lon=dp_lon,
            sku_name=sku.name if sku else None,
            quantity=ip.quantity,
            task_id=ip.id,
            status="available",
            from_address=dc_address,
            from_lat=dc_lat,
            from_lon=dc_lon,
            to_address=dp_address,
            to_lat=dp_lat,
            to_lon=dp_lon,
        ))

    return out


async def _task_sse_stream(courier_id: str, queue: asyncio.Queue):
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
        driver_sse_manager.unsubscribe(courier_id, queue)


@router.get("/delivery-tasks/events", summary="SSE stream for courier task updates")
async def stream_task_events(
    courier: Annotated[CourierAccount, Depends(get_current_courier_from_query)],
):
    """SSE stream: sends 'task_updated' events when a task status changes (e.g. DC hands over)."""
    courier_id = str(courier.id)
    queue = driver_sse_manager.subscribe(courier_id)
    return StreamingResponse(
        _task_sse_stream(courier_id, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/delivery-tasks/my",
    response_model=list[CourierDeliveryTaskResponse],
    summary="Get my active delivery tasks",
)
async def get_my_tasks(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CourierDeliveryTaskResponse]:
    """Get delivery tasks assigned to the current courier (in progress)."""
    if courier.status != CourierAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active couriers can view their tasks",
        )
    result = await db.execute(
        select(CourierDeliveryTask).where(
            CourierDeliveryTask.courier_id == courier.id,
            CourierDeliveryTask.status.in_([
                CourierTaskStatus.ASSIGNED.value,
                CourierTaskStatus.IN_TRANSIT.value,
            ]),
        ).order_by(CourierDeliveryTask.taken_at.desc())
    )
    tasks = result.scalars().all()
    out = []
    for task in tasks:
        out.append(await _build_task_response(task, db))
    return out


@router.get(
    "/delivery-tasks/completed",
    response_model=list[CompletedCourierTaskResponse],
    summary="Get my completed delivery tasks (history)",
)
async def get_completed_tasks(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
) -> list[CompletedCourierTaskResponse]:
    """Get delivery tasks completed by the current courier."""
    if courier.status != CourierAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active couriers can view history",
        )
    result = await db.execute(
        select(CourierDeliveryTask)
        .where(
            CourierDeliveryTask.courier_id == courier.id,
            CourierDeliveryTask.status == CourierTaskStatus.DELIVERED.value,
        )
        .order_by(CourierDeliveryTask.delivered_at.desc())
        .limit(limit)
        .offset(offset)
    )
    tasks = result.scalars().all()
    out = []
    for task in tasks:
        ip_result = await db.execute(
            select(DeliveryOrderItemPoint)
            .options(
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(DeliveryOrderItem.order),
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(DeliveryOrderItem.producer_sku),
                selectinload(DeliveryOrderItemPoint.delivery_point),
            )
            .where(DeliveryOrderItemPoint.id == task.item_point_id)
        )
        ip = ip_result.scalar_one_or_none()
        if not ip:
            continue
        dp = ip.delivery_point
        order = ip.order_item.order
        sku = ip.order_item.producer_sku
        out.append(CompletedCourierTaskResponse(
            task_id=task.id,
            order_id=order.id,
            order_number=order.order_number,
            delivery_point_name=getattr(dp, "name", None) or getattr(dp, "title", None),
            delivery_point_address=getattr(dp, "address", None),
            sku_name=sku.name if sku else None,
            quantity=ip.quantity,
            delivered_at=task.delivered_at,
        ))
    return out


@router.get(
    "/delivery-tasks/location-config",
    response_model=DriverLocationConfigResponse,
    summary="Get location tracking config",
)
async def get_location_config() -> DriverLocationConfigResponse:
    """Returns config for courier app: how often to send location."""
    return DriverLocationConfigResponse(
        send_interval_sec=settings.DRIVER_LOCATION_SEND_INTERVAL_SEC,
        poll_interval_sec=settings.DRIVER_LOCATION_POLL_INTERVAL_SEC,
        stale_after_sec=settings.DRIVER_LOCATION_STALE_AFTER_SEC,
    )


@router.post(
    "/delivery-tasks/{item_point_id}/take",
    response_model=CourierDeliveryTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Take a delivery task",
)
async def take_task(
    item_point_id: int,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourierDeliveryTaskResponse:
    """Claim an available delivery task."""
    if courier.status != CourierAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active couriers can take tasks",
        )

    existing_result = await db.execute(
        select(CourierDeliveryTask).where(
            CourierDeliveryTask.item_point_id == item_point_id,
            CourierDeliveryTask.status != CourierTaskStatus.DELIVERED.value,
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task already taken by another courier",
        )

    ip_result = await db.execute(
        select(DeliveryOrderItemPoint)
        .options(selectinload(DeliveryOrderItemPoint.scan_events))
        .where(
            DeliveryOrderItemPoint.id == item_point_id,
            DeliveryOrderItemPoint.status == DeliveryPointStatus.AT_DC,
        )
    )
    ip = ip_result.scalar_one_or_none()
    if not ip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item point not found or not available")

    task = CourierDeliveryTask(
        item_point_id=item_point_id,
        courier_id=courier.id,
        status=CourierTaskStatus.ASSIGNED.value,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return await _build_task_response(task, db)


@router.post(
    "/delivery-tasks/{task_id}/confirm-delivery",
    response_model=CourierDeliveryTaskResponse,
    summary="Confirm delivery (QR scan + optional photo)",
)
async def confirm_delivery(
    task_id: int,
    body: ConfirmDeliveryRequest,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourierDeliveryTaskResponse:
    """
    Confirm delivery at destination point.

    Validates QR token, marks task and item_point as delivered.
    """
    if courier.status != CourierAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active couriers can confirm delivery",
        )
    result = await db.execute(
        select(CourierDeliveryTask).where(
            CourierDeliveryTask.id == task_id,
            CourierDeliveryTask.courier_id == courier.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found or not assigned to you")
    if task.status == CourierTaskStatus.DELIVERED.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task already delivered")
    if task.status not in (CourierTaskStatus.ASSIGNED.value, CourierTaskStatus.IN_TRANSIT.value):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task is not in a deliverable state")

    ip_result = await db.execute(
        select(DeliveryOrderItemPoint).where(DeliveryOrderItemPoint.id == task.item_point_id)
    )
    item_point = ip_result.scalar_one_or_none()
    if not item_point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item point not found")

    if str(item_point.qr_token) != str(body.qr_token):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="QR token does not match this task")

    now = datetime.now(timezone.utc)
    task.status = CourierTaskStatus.DELIVERED.value
    task.delivered_at = now
    task.qr_scanned = True

    item_point.status = DeliveryPointStatus.DELIVERED
    item_point.delivered_at = now

    await db.commit()
    await db.refresh(task)
    return await _build_task_response(task, db)


@router.post(
    "/delivery-tasks/{task_id}/upload-delivery-photo",
    response_model=CourierDeliveryTaskResponse,
    summary="Upload optional delivery proof photo",
)
async def upload_delivery_photo(
    task_id: int,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> CourierDeliveryTaskResponse:
    """Upload a delivery proof photo (can be uploaded before or after confirm-delivery)."""
    if courier.status != CourierAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active couriers can upload photos",
        )
    result = await db.execute(
        select(CourierDeliveryTask).where(
            CourierDeliveryTask.id == task_id,
            CourierDeliveryTask.courier_id == courier.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max {MAX_FILE_SIZE // (1024*1024)} MB",
        )
    content_type = file.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only image files are allowed")

    if task.media_owner_uuid is None:
        task.media_owner_uuid = uuid.uuid4()

    blob_path = upload_blob(
        f"couriers/{courier.id}/tasks/{task_id}/delivery_photo",
        content,
        content_type,
    )
    media = MediaFile(
        owner_type=MediaFileOwnerType.COURIER_DELIVERY_TASK,
        owner_id=task.media_owner_uuid,
        kind="delivery_photo",
        blob_path=blob_path,
        content_type=content_type,
        size_bytes=len(content),
    )
    db.add(media)
    await db.flush()
    task.delivery_photo_media_id = media.id
    await db.commit()
    await db.refresh(task)
    return await _build_task_response(task, db)


@router.post(
    "/delivery-tasks/{task_id}/location",
    status_code=status.HTTP_200_OK,
    summary="Report current location for a task",
)
async def post_location(
    task_id: int,
    body: DriverLocationReport,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Report courier's current GPS location for an active task."""
    if courier.status != CourierAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only active couriers can report location",
        )
    result = await db.execute(
        select(CourierDeliveryTask).where(
            CourierDeliveryTask.id == task_id,
            CourierDeliveryTask.courier_id == courier.id,
            CourierDeliveryTask.status.in_([
                CourierTaskStatus.ASSIGNED.value,
                CourierTaskStatus.IN_TRANSIT.value,
            ]),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active task not found")

    ip_result = await db.execute(
        select(DeliveryOrderItemPoint)
        .options(selectinload(DeliveryOrderItemPoint.order_item))
        .where(DeliveryOrderItemPoint.id == task.item_point_id)
    )
    ip = ip_result.scalar_one_or_none()
    if ip:
        await report_location(
            db=db,
            driver_id=courier.id,
            task_id=task.id,
            lat=body.lat,
            lon=body.lon,
            accuracy=body.accuracy,
        )
    return {"status": "ok"}
