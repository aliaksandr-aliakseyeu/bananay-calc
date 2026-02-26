"""Delivery Order API endpoints (new structure with templates)."""
import asyncio
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_db
from app.db.models.delivery_order import OrderStatus
from app.db.models.delivery_task import DriverDeliveryTask
from app.db.models.enums import MediaFileOwnerType
from app.db.models.media_file import MediaFile
from app.db.models.user import User
from app.dependencies import get_current_user, get_current_user_from_query
from app.schemas.delivery_order_new import (AssignedDriverInfo,
                                            DeliveryCenterInfo,
                                            DeliveryOrderCreateFromTemplates,
                                            DeliveryOrderDetailResponse,
                                            DeliveryOrderListResponse,
                                            DeliveryOrderResponse,
                                            DeliveryOrderStatusHistoryResponse,
                                            DeliveryOrderStatusUpdate,
                                            OrderQrPayloadItem,
                                            OrderQrPayloadsResponse)
from app.schemas.driver_location import DriverLocationResponse
from app.services.azure_blob_service import download_blob
from app.services.delivery_order_service import DeliveryOrderService
from app.services.distance_service import DistanceService
from app.services.driver_location_service import get_location_for_order
from app.services.driver_location_sse import driver_location_sse

router = APIRouter(prefix="/delivery-orders", tags=["delivery-orders"])

logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=DeliveryOrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new delivery order from templates",
)
async def create_order(
    order_data: DeliveryOrderCreateFromTemplates,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryOrderDetailResponse:
    """
    Create a new delivery order from one or more templates.

    - **template_ids**: List of template IDs to include in this order
    - **status**: Initial order status (draft or pending)
    - **priority**: Order priority (normal, high, urgent)
    - **producer_notes**: Optional notes from producer
    - **expected_pickup_date**: When producer plans to hand over
    - **delivery_deadline**: Deadline for delivery

    The order will contain snapshots of all selected templates,
    so changes to templates won't affect this order.
    """
    try:
        order = await DeliveryOrderService.create_order_from_templates(
            db=db,
            user_id=current_user.id,
            template_ids=order_data.template_ids,
            status=order_data.status,
            producer_notes=order_data.producer_notes,
            priority=order_data.priority,
            expected_pickup_date=order_data.expected_pickup_date,
            delivery_deadline=order_data.delivery_deadline,
        )

        order_with_items = await DeliveryOrderService.get_order_by_id(
            db, order.id, current_user.id, with_items=True
        )

        return DeliveryOrderDetailResponse.model_validate(order_with_items)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "",
    response_model=DeliveryOrderListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get list of delivery orders",
)
async def get_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: OrderStatus | None = Query(None, description="Filter by status"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> DeliveryOrderListResponse:
    """
    Get paginated list of delivery orders for current producer.

    - Supports filtering by status
    - Orders sorted by creation date (newest first)
    """
    orders, total = await DeliveryOrderService.get_user_orders(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
    )

    return DeliveryOrderListResponse(
        items=[DeliveryOrderResponse.model_validate(order) for order in orders],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/{order_id}",
    response_model=DeliveryOrderDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get delivery order details",
)
async def get_order(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryOrderDetailResponse:
    """
    Get detailed information about a delivery order.

    - Includes all items (template snapshots)
    - Includes all delivery points for each item
    - Shows current status and timestamps
    """
    order = await DeliveryOrderService.get_order_by_id(
        db, order_id, current_user.id, with_items=True
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )

    response = DeliveryOrderDetailResponse.model_validate(order)
    photo_map = await DeliveryOrderService.get_order_dc_unload_photos(db, order)
    if photo_map:
        new_items = []
        for item in response.items:
            new_points = [
                p.model_copy(update={"dc_unload_photo_media_id": photo_map[p.id]})
                if p.id in photo_map
                else p
                for p in item.points
            ]
            new_items.append(item.model_copy(update={"points": new_points}))
        response = response.model_copy(update={"items": new_items})

    distance_service = DistanceService()
    new_items = []
    for idx_i, item in enumerate(response.items):
        new_points = []
        for idx_p, pt in enumerate(item.points):
            lat, lon = None, None
            delivery_point_name = None
            delivery_point_address = None
            orm_pt = order.items[idx_i].points[idx_p] if idx_i < len(order.items) else None
            if orm_pt and getattr(orm_pt, "delivery_point", None):
                dp = orm_pt.delivery_point
                if getattr(dp, "location", None):
                    try:
                        lat, lon = distance_service.extract_coordinates(dp.location)
                    except Exception:
                        pass
                if getattr(dp, "name", None):
                    delivery_point_name = dp.name
                if getattr(dp, "address", None):
                    delivery_point_address = dp.address
            new_points.append(pt.model_copy(update={
                "lat": lat, "lon": lon,
                "delivery_point_name": delivery_point_name,
                "delivery_point_address": delivery_point_address,
            }))
        new_items.append(item.model_copy(update={"points": new_points}))
    response = response.model_copy(update={"items": new_items})

    if order.status in (
        OrderStatus.DRIVER_ASSIGNED,
        OrderStatus.LOADING_AT_WAREHOUSE,
        OrderStatus.IN_DELIVERY,
        OrderStatus.PARTIALLY_DELIVERED,
        OrderStatus.IN_TRANSIT_TO_DC,
        OrderStatus.AT_DC,
    ):
        driver_info = await DeliveryOrderService.get_assigned_driver_for_order(
            db, order_id
        )
        if driver_info:
            response = response.model_copy(
                update={"assigned_driver": AssignedDriverInfo(**driver_info)}
            )
    if order.status in (
        OrderStatus.DRIVER_ASSIGNED,
        OrderStatus.LOADING_AT_WAREHOUSE,
        OrderStatus.IN_TRANSIT_TO_DC,
        OrderStatus.AT_DC,
    ):
        dc_list = await DeliveryOrderService.get_order_delivery_centers(db, order_id)
        if dc_list:
            response = response.model_copy(
                update={"delivery_centers": [DeliveryCenterInfo(**dc) for dc in dc_list]}
            )
    return response


@router.get(
    "/{order_id}/qr-payloads",
    response_model=OrderQrPayloadsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get QR payloads for order (print labels)",
)
async def get_order_qr_payloads(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrderQrPayloadsResponse:
    """
    Get list of QR payloads for this order (one per delivery_order_item_point).

    For producer: print QR codes and stick on boxes. Each payload includes
    qr_token (encode in QR), quantity, delivery point and SKU name for labels.
    Only the order owner (producer) can access.
    """
    order = await DeliveryOrderService.get_order_by_id(
        db, order_id, current_user.id, with_items=True
    )
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )
    items: list[OrderQrPayloadItem] = []
    for item in order.items:
        sku_name = getattr(item, "template_name", None)
        for pt in item.points:
            delivery_point_name = None
            delivery_point_address = None
            if getattr(pt, "delivery_point", None):
                dp = pt.delivery_point
                delivery_point_name = getattr(dp, "name", None) or getattr(dp, "title", None)
                delivery_point_address = getattr(dp, "address", None)
            items.append(
                OrderQrPayloadItem(
                    qr_token=pt.qr_token,
                    order_item_id=pt.order_item_id,
                    delivery_point_id=pt.delivery_point_id,
                    quantity=pt.quantity,
                    delivery_point_name=delivery_point_name,
                    delivery_point_address=delivery_point_address,
                    sku_name=sku_name,
                )
            )
    return OrderQrPayloadsResponse(
        order_id=order.id,
        order_number=order.order_number,
        items=items,
    )


@router.get(
    "/{order_id}/dc-unload-photo/{media_id}",
    status_code=status.HTTP_200_OK,
    summary="Get DC unload photo (producer view)",
)
async def get_dc_unload_photo(
    order_id: int,
    media_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Stream the driver's unload-at-DC photo for this order.
    Only allowed if the media belongs to a driver task for this order and the current user is the order's producer.
    """
    from uuid import UUID

    order = await DeliveryOrderService.get_order_by_id(db, order_id, current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )
    try:
        uid = UUID(media_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid media ID",
        )
    result = await db.execute(select(MediaFile).where(MediaFile.id == uid))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )
    if media.owner_type != MediaFileOwnerType.DRIVER_DELIVERY_TASK:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )
    task_result = await db.execute(
        select(DriverDeliveryTask).where(
            DriverDeliveryTask.media_owner_uuid == media.owner_id,
            DriverDeliveryTask.order_id == order_id,
        )
    )
    if not task_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found",
        )
    out = download_blob(media.blob_path)
    if not out:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage unavailable",
        )
    content, _ = out
    return Response(
        content=content,
        media_type=media.content_type or "application/octet-stream",
    )


@router.patch(
    "/{order_id}/status",
    response_model=DeliveryOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update order status",
)
async def update_order_status(
    order_id: int,
    status_update: DeliveryOrderStatusUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryOrderResponse:
    """
    Update order status with optional notes.

    - Dedicated endpoint for status changes
    - Automatically updates timestamp fields
    - Logs change in history
    """
    order = await DeliveryOrderService.get_order_by_id(db, order_id, current_user.id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )

    updated_order = await DeliveryOrderService.update_order_status(
        db=db,
        order=order,
        new_status=status_update.status,
        user_id=current_user.id,
        notes=status_update.notes,
    )

    return DeliveryOrderResponse.model_validate(updated_order)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete delivery order",
)
async def delete_order(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a delivery order.

    - Can only delete orders in PENDING, DRAFT, or CANCELLED status
    - Cascades to order items, points, and history
    """
    order = await DeliveryOrderService.get_order_by_id(db, order_id, current_user.id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )

    try:
        await DeliveryOrderService.delete_order(db, order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{order_id}/driver-location",
    response_model=DriverLocationResponse | None,
    status_code=status.HTTP_200_OK,
    summary="Get driver location for order",
)
async def get_driver_location(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverLocationResponse | None:
    """
    Get last reported driver location for an order.
    Returns null if no location yet. User must own the order.
    """
    order = await DeliveryOrderService.get_order_by_id(db, order_id, current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )
    loc = await get_location_for_order(db, order_id)
    if not loc:
        return None
    return DriverLocationResponse(**loc)


async def _sse_stream_for_order(order_id: int, queue: asyncio.Queue):
    """Async generator: yield SSE-formatted location messages. Heartbeat if no event."""
    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=settings.SSE_HEARTBEAT_INTERVAL)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
                continue
            event_name = payload.get("event", "location")
            data_str = json.dumps(payload, ensure_ascii=False)
            yield f"event: {event_name}\ndata: {data_str}\n\n"
    finally:
        driver_location_sse.unsubscribe(order_id, queue)


@router.get(
    "/{order_id}/driver-location/stream",
    summary="SSE stream of driver location updates",
)
async def stream_driver_location(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user_from_query)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Server-Sent Events stream for driver location on this order.
    Pass token in query: ?token=<access_token>
    """
    order = await DeliveryOrderService.get_order_by_id(db, order_id, current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )
    queue = driver_location_sse.subscribe(order_id)
    return StreamingResponse(
        _sse_stream_for_order(order_id, queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{order_id}/history",
    response_model=list[DeliveryOrderStatusHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get order status history",
)
async def get_order_history(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DeliveryOrderStatusHistoryResponse]:
    """
    Get status change history for an order.

    - Shows who changed status, when, and notes
    - Ordered by timestamp (newest first)
    """
    try:
        history = await DeliveryOrderService.get_order_history(
            db, order_id, current_user.id
        )
        return [
            DeliveryOrderStatusHistoryResponse.model_validate(entry)
            for entry in history
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
