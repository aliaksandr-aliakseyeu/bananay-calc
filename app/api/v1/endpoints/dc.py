"""DC endpoints: profile + QR operations over existing order item points."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DcAccount, DistributionCenter
from app.db.models.courier_delivery_task import CourierDeliveryTask
from app.db.models.delivery_order import ItemPointScanPhase
from app.db.models.enums import CourierTaskStatus, DcAccountStatus
from app.dependencies import get_current_dc
from app.schemas.dc import (
    DcBoxItemResponse,
    DcBoxScanResponse,
    DcDeliveredEventResponse,
    DcHistoryEventResponse,
    DcOperationEventResponse,
    DcOperationResponse,
    DcProfileResponse,
    DcProfileUpdate,
    DcReceiveForOrderResponse,
    DcReceivingOrderResponse,
    DcScanHandoverCourier2Request,
    DcScanMoveToSortingRequest,
    DcScanReceiveForOrderRequest,
    DcScanReceiveRequest,
    DcScanSortToZoneRequest,
)
from app.services.dc_item_point_service import DcItemPointService
from app.services.delivery_order_service import DeliveryOrderService
from app.services.driver_location_sse import driver_location_sse
from app.services.sse_manager import driver_sse_manager

router = APIRouter(prefix="/dc", tags=["DC"])
DEFAULT_SORTING_ZONE_KEY = "default_zone"


def _map_scan_error(err: str) -> HTTPException:
    if err == "item_point_not_found":
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR token not found")
    if err == "dc_account_has_no_distribution_center":
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DC account is not assigned to distribution center",
        )
    if err == "item_point_belongs_to_another_distribution_center":
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Item point belongs to another distribution center",
        )
    if err == "receive_requires_driver_loading_scan":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Receive scan requires prior driver loading scan",
        )
    if err == "receive_requires_in_transit_status":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Receive scan requires item point status in_transit",
        )
    if err == "invalid_stage_transition":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invalid stage transition",
        )
    if err == "item_point_belongs_to_another_order":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="QR token belongs to another order",
        )
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err)


@router.get("/me", response_model=DcProfileResponse)
async def get_me(
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcProfileResponse:
    """Get current DC account profile."""
    distribution_center_name = None
    if dc.distribution_center_id is not None:
        dc_name_result = await db.execute(
            select(DistributionCenter.name).where(DistributionCenter.id == dc.distribution_center_id)
        )
        distribution_center_name = dc_name_result.scalar_one_or_none()
    return DcProfileResponse.model_validate(
        {
            **dc.__dict__,
            "distribution_center_name": distribution_center_name,
        }
    )


@router.patch("/me", response_model=DcProfileResponse)
async def update_me(
    body: DcProfileUpdate,
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcProfileResponse:
    """Update current DC account profile."""
    if dc.status == DcAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
        )
    if body.first_name is not None:
        dc.first_name = body.first_name.strip() or None
    if body.last_name is not None:
        dc.last_name = body.last_name.strip() or None
    if body.distribution_center_id is not None:
        dc.distribution_center_id = body.distribution_center_id
    await db.commit()
    await db.refresh(dc)
    distribution_center_name = None
    if dc.distribution_center_id is not None:
        dc_name_result = await db.execute(
            select(DistributionCenter.name).where(DistributionCenter.id == dc.distribution_center_id)
        )
        distribution_center_name = dc_name_result.scalar_one_or_none()
    return DcProfileResponse.model_validate(
        {
            **dc.__dict__,
            "distribution_center_name": distribution_center_name,
        }
    )


@router.post("/boxes/scan-receive", response_model=DcBoxScanResponse)
async def scan_receive(
    body: DcScanReceiveRequest,
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcBoxScanResponse:
    """Step 1: accept producer box at DC."""
    service = DcItemPointService(db)
    operation_id = body.operation_id or uuid.uuid4()
    try:
        result = await service.scan_receive(
            dc=dc,
            qr_token=body.qr_token,
            operation_id=operation_id,
        )
    except ValueError as exc:
        raise _map_scan_error(str(exc))
    await db.commit()
    return DcBoxScanResponse(
        qr_token=result.item_point.qr_token,
        delivery_order_item_point_id=result.item_point.id,
        order_id=result.item_point.order_item.order_id,
        current_stage=result.stage.value,
        phase=result.event.phase.value,
        event_id=result.event.id,
        operation_id=result.event.operation_id,
        is_idempotent=result.is_idempotent,
    )


@router.post("/boxes/scan-move-to-sorting", response_model=DcBoxScanResponse)
async def scan_move_to_sorting(
    body: DcScanMoveToSortingRequest,
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcBoxScanResponse:
    """Step 2: move box to sorting area."""
    service = DcItemPointService(db)
    operation_id = body.operation_id or uuid.uuid4()
    try:
        result = await service.scan_move_to_sorting(
            dc=dc,
            qr_token=body.qr_token,
            operation_id=operation_id,
        )
    except ValueError as exc:
        raise _map_scan_error(str(exc))
    await db.commit()
    return DcBoxScanResponse(
        qr_token=result.item_point.qr_token,
        delivery_order_item_point_id=result.item_point.id,
        order_id=result.item_point.order_item.order_id,
        current_stage=result.stage.value,
        phase=result.event.phase.value,
        event_id=result.event.id,
        operation_id=result.event.operation_id,
        is_idempotent=result.is_idempotent,
    )


@router.post("/boxes/scan-sort-to-zone", response_model=DcBoxScanResponse)
async def scan_sort_to_zone(
    body: DcScanSortToZoneRequest,
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcBoxScanResponse:
    """Step 3: place box into delivery zone."""
    service = DcItemPointService(db)
    operation_id = body.operation_id or uuid.uuid4()
    zone_key = (body.zone_key or "").strip() or DEFAULT_SORTING_ZONE_KEY
    try:
        result = await service.scan_sort_to_zone(
            dc=dc,
            qr_token=body.qr_token,
            zone_key=zone_key,
            operation_id=operation_id,
        )
    except ValueError as exc:
        raise _map_scan_error(str(exc))
    await db.commit()
    return DcBoxScanResponse(
        qr_token=result.item_point.qr_token,
        delivery_order_item_point_id=result.item_point.id,
        order_id=result.item_point.order_item.order_id,
        current_stage=result.stage.value,
        phase=result.event.phase.value,
        event_id=result.event.id,
        operation_id=result.event.operation_id,
        is_idempotent=result.is_idempotent,
    )


@router.post("/boxes/scan-handover-courier2", response_model=DcBoxScanResponse)
async def scan_handover_courier2(
    body: DcScanHandoverCourier2Request,
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcBoxScanResponse:
    """Step 4: handover box to courier #2."""

    service = DcItemPointService(db)
    operation_id = body.operation_id or uuid.uuid4()
    try:
        result = await service.scan_handover_to_courier2(
            dc=dc,
            qr_token=body.qr_token,
            courier_name=body.courier_name,
            courier_phone=body.courier_phone,
            courier_external_id=body.courier_external_id,
            operation_id=operation_id,
        )
    except ValueError as exc:
        raise _map_scan_error(str(exc))

    if not result.is_idempotent:
        courier_task_result = await db.execute(
            select(CourierDeliveryTask).where(
                CourierDeliveryTask.item_point_id == result.item_point.id,
                CourierDeliveryTask.status == CourierTaskStatus.ASSIGNED.value,
            )
        )
        courier_task = courier_task_result.scalar_one_or_none()
        if courier_task:
            courier_task.status = CourierTaskStatus.IN_TRANSIT.value
            courier_task.in_transit_at = datetime.now(timezone.utc)
            await db.flush()
            driver_sse_manager.send_to_driver(
                str(courier_task.courier_id),
                "task_updated",
                {"task_id": courier_task.id, "status": "in_transit"},
            )

    await db.commit()

    if not result.is_idempotent:
        order_id = result.item_point.order_item.order_id
        snapshot = await DeliveryOrderService.get_order_snapshot_for_sse(db, order_id)
        if snapshot is not None:
            driver_location_sse.broadcast_to_order(
                order_id, {"event": "order_update", **snapshot}
            )

    return DcBoxScanResponse(
        qr_token=result.item_point.qr_token,
        delivery_order_item_point_id=result.item_point.id,
        order_id=result.item_point.order_item.order_id,
        current_stage=result.stage.value,
        phase=result.event.phase.value,
        event_id=result.event.id,
        operation_id=result.event.operation_id,
        is_idempotent=result.is_idempotent,
    )


@router.get("/boxes/courier-info", summary="Get assigned courier info by box QR token")
async def get_courier_info_by_qr(
    qr_token: str,
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return assigned courier name, phone and order details for a given box QR.
    Used by DC worker to verify the courier standing in front of them before handover."""
    from app.db.models.courier_account import CourierAccount
    from app.db.models.courier_delivery_task import CourierDeliveryTask
    from app.db.models.delivery_order import (
        DeliveryOrder,
        DeliveryOrderItem,
        DeliveryOrderItemPoint,
    )
    from app.db.models.enums import CourierTaskStatus, MediaFileOwnerType
    from app.db.models.media_file import MediaFile

    try:
        parsed_qr = uuid.UUID(qr_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid QR token format")

    ip_result = await db.execute(
        select(DeliveryOrderItemPoint).where(DeliveryOrderItemPoint.qr_token == parsed_qr)
    )
    item_point = ip_result.scalar_one_or_none()
    if not item_point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Box not found")

    task_result = await db.execute(
        select(CourierDeliveryTask).where(
            CourierDeliveryTask.item_point_id == item_point.id,
            CourierDeliveryTask.status == CourierTaskStatus.ASSIGNED.value,
        )
    )
    task = task_result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No courier assigned to this box")

    courier_result = await db.execute(
        select(CourierAccount).where(CourierAccount.id == task.courier_id)
    )
    courier = courier_result.scalar_one_or_none()
    if not courier:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Courier not found")

    order_item_result = await db.execute(
        select(DeliveryOrderItem, DeliveryOrder)
        .join(DeliveryOrder, DeliveryOrder.id == DeliveryOrderItem.order_id)
        .where(DeliveryOrderItem.id == item_point.order_item_id)
    )
    order_row = order_item_result.first()
    order_number = order_row[1].order_number if order_row else None
    order_id = order_row[1].id if order_row else None

    selfie_result = await db.execute(
        select(MediaFile).where(
            MediaFile.owner_id == courier.id,
            MediaFile.owner_type == MediaFileOwnerType.COURIER,
            MediaFile.kind == "selfie",
        ).order_by(MediaFile.created_at.desc()).limit(1)
    )
    selfie = selfie_result.scalar_one_or_none()

    return {
        "task_id": task.id,
        "item_point_id": item_point.id,
        "qr_token": str(item_point.qr_token),
        "order_id": order_id,
        "order_number": order_number,
        "courier_id": str(courier.id),
        "courier_name": courier.full_name or None,
        "courier_phone": courier.phone_e164,
        "courier_photo_media_id": str(selfie.id) if selfie else None,
    }


@router.get("/boxes", response_model=list[DcBoxItemResponse])
async def list_boxes(
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
    stage: ItemPointScanPhase | None = Query(None, description="Filter by latest DC stage"),
    order_id: int | None = Query(None, ge=1, description="Optional producer order id"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[DcBoxItemResponse]:
    """List QR-linked item points for current DC with optional stage filter."""
    service = DcItemPointService(db)
    rows = await service.list_item_points(dc=dc, limit=limit, offset=offset, order_id=order_id)
    out: list[DcBoxItemResponse] = []
    for item_point, dc_id, latest_stage in rows:
        current_stage = (latest_stage.value if latest_stage else ItemPointScanPhase.LOADING.value)
        if stage is not None and current_stage != stage.value:
            continue
        out.append(
            DcBoxItemResponse(
                qr_token=item_point.qr_token,
                delivery_order_item_point_id=item_point.id,
                order_id=item_point.order_item.order_id,
                order_number=getattr(item_point.order_item.order, "order_number", None),
                distribution_center_id=dc_id,
                current_stage=current_stage,
                phase=current_stage,
                phase_label=current_stage,
                operation_id=None,
                delivery_point_name=(
                    getattr(item_point.delivery_point, "name", None)
                    or getattr(item_point.delivery_point, "title", None)
                ),
                sku_name=getattr(item_point.order_item.producer_sku, "name", None),
                quantity=item_point.quantity,
                updated_at=item_point.updated_at,
            )
        )
    return out


@router.get("/operations/{operation_id}", response_model=DcOperationResponse)
async def get_operation(
    operation_id: uuid.UUID,
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcOperationResponse:
    """Get all box events recorded under one operation_id."""
    service = DcItemPointService(db)
    rows = await service.get_operation_events(dc=dc, operation_id=operation_id)
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operation not found")
    return DcOperationResponse(
        operation_id=operation_id,
        events=[
            DcOperationEventResponse(
                event_id=event.id,
                qr_token=item_point.qr_token,
                phase=event.phase.value,
                stage_after=event.phase.value,
                scanned_by_dc_id=event.scanned_by_dc_id,
                created_at=event.scanned_at,
                payload=event.event_payload,
            )
            for event, item_point in rows
        ],
    )


@router.get("/history/events", response_model=list[DcHistoryEventResponse])
async def list_history_events(
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
    phase: ItemPointScanPhase = Query(..., description="Audit phase to list"),
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> list[DcHistoryEventResponse]:
    """List audit scan events for current DC by phase."""
    service = DcItemPointService(db)
    rows = await service.list_history_events(dc=dc, phase=phase, limit=limit, offset=offset)
    out: list[DcHistoryEventResponse] = []
    for event, item_point in rows:
        actor_name = None
        if event.scanned_by_dc is not None:
            first_name = (event.scanned_by_dc.first_name or "").strip()
            last_name = (event.scanned_by_dc.last_name or "").strip()
            full_name = " ".join(part for part in [first_name, last_name] if part)
            actor_name = full_name or None
        out.append(
            DcHistoryEventResponse(
                event_id=event.id,
                scanned_at=event.scanned_at,
                phase=event.phase.value,
                qr_token=item_point.qr_token,
                delivery_order_item_point_id=item_point.id,
                order_id=item_point.order_item.order_id,
                order_number=getattr(item_point.order_item.order, "order_number", None),
                operation_id=event.operation_id,
                scanned_by_dc_id=event.scanned_by_dc_id,
                actor_name=actor_name,
                delivery_point_name=(
                    getattr(item_point.delivery_point, "name", None)
                    or getattr(item_point.delivery_point, "title", None)
                ),
                sku_name=getattr(item_point.order_item.producer_sku, "name", None),
                quantity=item_point.quantity,
                payload=event.event_payload,
            )
        )
    return out


@router.get("/history/delivered", response_model=list[DcDeliveredEventResponse])
async def list_delivered_events(
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> list[DcDeliveredEventResponse]:
    """List deliveries to final points (courier delivered to customer) for items that passed through this DC."""
    service = DcItemPointService(db)
    rows = await service.list_delivered_events(dc=dc, limit=limit, offset=offset)
    out: list[DcDeliveredEventResponse] = []
    for task, item_point in rows:
        courier_name = (task.courier.full_name or "").strip() or None if task.courier else None
        out.append(
            DcDeliveredEventResponse(
                task_id=task.id,
                delivered_at=task.delivered_at,
                courier_name=courier_name,
                qr_token=item_point.qr_token,
                delivery_order_item_point_id=item_point.id,
                order_id=item_point.order_item.order_id,
                order_number=getattr(item_point.order_item.order, "order_number", None),
                delivery_point_name=(
                    getattr(item_point.delivery_point, "name", None)
                    or getattr(item_point.delivery_point, "title", None)
                ),
                sku_name=getattr(item_point.order_item.producer_sku, "name", None),
                quantity=item_point.quantity,
            )
        )
    return out


@router.get("/receiving/orders", response_model=list[DcReceivingOrderResponse])
async def list_receiving_orders(
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DcReceivingOrderResponse]:
    """List active receiving orders for current DC with scan progress."""
    service = DcItemPointService(db)
    rows = await service.list_receiving_orders(dc=dc)
    return [DcReceivingOrderResponse(**row) for row in rows]


@router.post(
    "/receiving/orders/{order_id}/scan-receive",
    response_model=DcReceiveForOrderResponse,
)
async def scan_receive_for_order(
    order_id: int,
    body: DcScanReceiveForOrderRequest,
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcReceiveForOrderResponse:
    """
    Receive one QR token for a selected active order.

    Enforces that scanned token belongs to this order and current DC.
    """
    service = DcItemPointService(db)
    operation_id = body.operation_id or uuid.uuid4()
    try:
        result = await service.scan_receive_for_order(
            dc=dc,
            order_id=order_id,
            qr_token=body.qr_token,
            operation_id=operation_id,
        )
    except ValueError as exc:
        raise _map_scan_error(str(exc))

    expected_count, received_count = await service.get_receiving_progress(
        dc=dc,
        order_id=order_id,
    )
    await db.commit()
    return DcReceiveForOrderResponse(
        qr_token=result.item_point.qr_token,
        delivery_order_item_point_id=result.item_point.id,
        order_id=result.item_point.order_item.order_id,
        current_stage=result.stage.value,
        phase=result.event.phase.value,
        event_id=result.event.id,
        operation_id=result.event.operation_id,
        is_idempotent=result.is_idempotent,
        scanned_at=result.event.scanned_at,
        delivery_point_name=(
            getattr(result.item_point.delivery_point, "name", None)
            or getattr(result.item_point.delivery_point, "title", None)
        ),
        sku_name=getattr(result.item_point.order_item.producer_sku, "name", None),
        quantity=result.item_point.quantity,
        expected_count=expected_count,
        received_count=received_count,
        remaining_count=max(expected_count - received_count, 0),
    )


@router.get("/media/{media_id}", summary="Stream media file for DC workers (e.g. courier selfie)")
async def get_dc_media(
    media_id: uuid.UUID,
    dc: Annotated[DcAccount, Depends(get_current_dc)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Stream a media file. Used by DC workers to view courier photos during handover."""
    from app.db.models.media_file import MediaFile
    from app.services.azure_blob_service import download_blob

    result = await db.execute(select(MediaFile).where(MediaFile.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    out = download_blob(media.blob_path)
    if out is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found in storage")
    content, content_type = out
    return Response(content=content, media_type=content_type or "application/octet-stream")
