"""Delivery Order API endpoints (new structure with templates)."""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models.delivery_order import OrderStatus
from app.db.models.user import User
from app.dependencies import get_current_user
from app.schemas.delivery_order_new import (DeliveryOrderCreateFromTemplates,
                                            DeliveryOrderDetailResponse,
                                            DeliveryOrderListResponse,
                                            DeliveryOrderResponse,
                                            DeliveryOrderStatusHistoryResponse,
                                            DeliveryOrderStatusUpdate)
from app.services.delivery_order_service import DeliveryOrderService

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

    return DeliveryOrderDetailResponse.model_validate(order)


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
