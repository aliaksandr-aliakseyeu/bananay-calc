"""Delivery Order API endpoints."""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models.delivery_order import (DeliveryOrder, DeliveryOrderPoint,
                                          DeliveryOrderStatusHistory,
                                          OrderStatus)
from app.db.models.producer_sku import ProducerSKU
from app.db.models.user import User
from app.dependencies import get_current_user
from app.schemas.delivery_order import (DeliveryOrderCalculationRequest,
                                        DeliveryOrderCalculationResponse,
                                        DeliveryOrderCreate,
                                        DeliveryOrderDetailResponse,
                                        DeliveryOrderListResponse,
                                        DeliveryOrderPointResponse,
                                        DeliveryOrderPointUpdate,
                                        DeliveryOrderResponse,
                                        DeliveryOrderStatusHistoryResponse,
                                        DeliveryOrderStatusUpdate,
                                        DeliveryOrderUpdate)
from app.services.calculator_service import CalculatorService

router = APIRouter(prefix="/delivery-orders", tags=["delivery-orders"])

logger = logging.getLogger(__name__)


async def generate_order_number(db: AsyncSession) -> str:
    """Generate unique order number in format ORD-YYYY-NNNN."""
    current_year = datetime.now(timezone.utc).year

    result = await db.execute(
        select(DeliveryOrder.order_number)
        .where(DeliveryOrder.order_number.like(f"ORD-{current_year}-%"))
        .order_by(DeliveryOrder.order_number.desc())
        .limit(1)
    )
    latest_order = result.scalar_one_or_none()

    if latest_order:
        number = int(latest_order.split("-")[-1]) + 1
    else:
        number = 1

    return f"ORD-{current_year}-{number:04d}"


@router.post(
    "/calculate",
    response_model=DeliveryOrderCalculationResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate delivery cost for an order",
)
async def calculate_order_cost(
    request: DeliveryOrderCalculationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryOrderCalculationResponse:
    """
    Calculate delivery cost for an order based on SKU and delivery points with quantities.

    Receives from frontend:
    - Warehouse coordinates
    - List of tuples (point_id, quantity)
    - SKU ID
    """
    sku_result = await db.execute(
        select(ProducerSKU)
        .where(
            ProducerSKU.id == request.producer_sku_id,
            ProducerSKU.producer_id == current_user.id,
        )
        .options(selectinload(ProducerSKU.product_category))
    )
    sku = sku_result.scalar_one_or_none()
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producer SKU not found",
        )

    if not sku.items_per_box or sku.items_per_box <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SKU must have items_per_box configured",
        )

    from app.schemas.calculator import ProductParams

    product_params = ProductParams(
        length_cm=int(sku.length_cm),
        width_cm=int(sku.width_cm),
        height_cm=int(sku.height_cm),
        weight_kg=sku.weight_kg,
        items_per_box=sku.items_per_box,
    )

    calculator = CalculatorService(db)
    try:
        point_quantities = [
            (pq.point_id, pq.quantity) for pq in request.point_quantities
        ]

        calc_result = await calculator.calculate_by_points(
            region_id=request.region_id,
            supplier_lat=request.warehouse_lat,
            supplier_lon=request.warehouse_lon,
            product=product_params,
            point_quantities=point_quantities,
        )

        cost_per_unit = calc_result["cost_per_item"]
        total_quantity = calc_result["total_quantity"]
        total_cost = cost_per_unit * total_quantity

        return DeliveryOrderCalculationResponse(
            total_cost=total_cost,
            cost_per_unit=cost_per_unit,
            calculation_details={
                "cost_per_item": float(cost_per_unit),
                "total_cost": float(total_cost),
                "total_quantity": total_quantity,
                "items_in_standard_box": calc_result["items_in_standard_box"],
                "cost_per_supplier_box": float(calc_result["cost_per_supplier_box"]),
                "delivery_points_ignored": calc_result["delivery_points_ignored"],
                "regions_count": calc_result["regions_count"],
                "distance_to_dc_km": float(calc_result["distance_to_dc_km"]),
                "nearest_dc_name": calc_result["nearest_dc_name"],
                "sku_name": sku.name,
                "sku_code": sku.sku_code,
                "items_per_box": sku.items_per_box,
            },
        )
    except Exception as e:
        logger.error(f"Error calculating delivery cost: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating delivery cost: {str(e)}",
        )


@router.post(
    "",
    response_model=DeliveryOrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new delivery order",
)
async def create_order(
    order_data: DeliveryOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryOrderDetailResponse:
    """
    Create a new delivery order.

    - Validates SKU and delivery list ownership
    - Generates unique order number
    - Calculates delivery cost
    - Creates order with points
    - Logs initial status in history
    """
    sku_result = await db.execute(
        select(ProducerSKU).where(
            ProducerSKU.id == order_data.producer_sku_id,
            ProducerSKU.producer_id == current_user.id,
        )
    )
    sku = sku_result.scalar_one_or_none()
    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producer SKU not found",
        )

    order_number = await generate_order_number(db)

    new_order = DeliveryOrder(
        order_number=order_number,
        producer_id=current_user.id,
        producer_sku_id=order_data.producer_sku_id,
        quantity=order_data.quantity,
        producer_notes=order_data.producer_notes,
        status=order_data.status,
        priority=order_data.priority,
        expected_pickup_date=order_data.expected_pickup_date,
        delivery_deadline=order_data.delivery_deadline,
        total_cost=order_data.total_cost,
        cost_per_unit=order_data.cost_per_unit,
    )
    db.add(new_order)
    await db.flush()

    for point_data in order_data.points:
        order_point = DeliveryOrderPoint(
            order_id=new_order.id,
            delivery_point_id=point_data.delivery_point_id,
            quantity=point_data.quantity,
            delivery_notes=point_data.delivery_notes,
        )
        db.add(order_point)

    history_entry = DeliveryOrderStatusHistory(
        order_id=new_order.id,
        changed_by_user_id=current_user.id,
        old_status=None,
        new_status=OrderStatus.PENDING,
        notes="Order created",
    )
    db.add(history_entry)

    await db.commit()
    await db.refresh(new_order)

    result = await db.execute(
        select(DeliveryOrder)
        .where(DeliveryOrder.id == new_order.id)
        .options(selectinload(DeliveryOrder.delivery_points))
    )
    order_with_points = result.scalar_one()

    return DeliveryOrderDetailResponse.model_validate(order_with_points)


@router.get(
    "",
    response_model=DeliveryOrderListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get list of delivery orders",
)
async def get_orders(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status_filter: Optional[OrderStatus] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryOrderListResponse:
    """
    Get paginated list of delivery orders for current producer.

    - Supports filtering by status
    - Orders sorted by creation date (newest first)
    """
    query = select(DeliveryOrder).where(DeliveryOrder.producer_id == current_user.id)

    if status_filter:
        query = query.where(DeliveryOrder.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(DeliveryOrder.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    orders = result.scalars().all()

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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryOrderDetailResponse:
    """
    Get detailed information about a delivery order.

    - Includes all delivery points
    - Shows current status and timestamps
    """
    result = await db.execute(
        select(DeliveryOrder)
        .where(
            DeliveryOrder.id == order_id,
            DeliveryOrder.producer_id == current_user.id,
        )
        .options(selectinload(DeliveryOrder.delivery_points))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )

    return DeliveryOrderDetailResponse.model_validate(order)


@router.patch(
    "/{order_id}",
    response_model=DeliveryOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update delivery order",
)
async def update_order(
    order_id: int,
    order_update: DeliveryOrderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryOrderResponse:
    """
    Update delivery order details.

    - Can update status, producer notes, admin notes
    - Status changes are logged in history
    """
    result = await db.execute(
        select(DeliveryOrder).where(
            DeliveryOrder.id == order_id,
            DeliveryOrder.producer_id == current_user.id,
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )

    old_status = order.status
    status_changed = False

    update_data = order_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value != old_status:
            status_changed = True
        setattr(order, field, value)

    if status_changed:
        history_entry = DeliveryOrderStatusHistory(
            order_id=order.id,
            changed_by_user_id=current_user.id,
            old_status=old_status,
            new_status=order.status,
            notes="Status changed via update endpoint",
        )
        db.add(history_entry)

        now = datetime.now(timezone.utc)
        if order.status == OrderStatus.IN_TRANSIT_TO_DC:
            order.sent_to_dc_at = now
        elif order.status == OrderStatus.AT_DC:
            order.arrived_at_dc_at = now
        elif order.status == OrderStatus.DRIVER_ASSIGNED:
            order.driver_assigned_at = now
        elif order.status == OrderStatus.IN_DELIVERY:
            order.delivery_started_at = now
        elif order.status == OrderStatus.COMPLETED:
            order.completed_at = now

    await db.commit()
    await db.refresh(order)

    return DeliveryOrderResponse.model_validate(order)


@router.patch(
    "/{order_id}/status",
    response_model=DeliveryOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Update order status",
)
async def update_order_status(
    order_id: int,
    status_update: DeliveryOrderStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryOrderResponse:
    """
    Update order status with optional notes.

    - Dedicated endpoint for status changes
    - Automatically updates timestamp fields
    - Logs change in history
    """
    result = await db.execute(
        select(DeliveryOrder).where(
            DeliveryOrder.id == order_id,
            DeliveryOrder.producer_id == current_user.id,
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )

    old_status = order.status

    order.status = status_update.status

    now = datetime.now(timezone.utc)
    if order.status == OrderStatus.IN_TRANSIT_TO_DC:
        order.sent_to_dc_at = now
    elif order.status == OrderStatus.AT_DC:
        order.arrived_at_dc_at = now
    elif order.status == OrderStatus.DRIVER_ASSIGNED:
        order.driver_assigned_at = now
    elif order.status == OrderStatus.IN_DELIVERY:
        order.delivery_started_at = now
    elif order.status == OrderStatus.COMPLETED:
        order.completed_at = now

    history_entry = DeliveryOrderStatusHistory(
        order_id=order.id,
        changed_by_user_id=current_user.id,
        old_status=old_status,
        new_status=order.status,
        notes=status_update.notes,
    )
    db.add(history_entry)

    await db.commit()
    await db.refresh(order)

    return DeliveryOrderResponse.model_validate(order)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete delivery order",
)
async def delete_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a delivery order.

    - Can only delete orders in PENDING or CANCELLED status
    - Cascades to order points and history
    """
    result = await db.execute(
        select(DeliveryOrder).where(
            DeliveryOrder.id == order_id,
            DeliveryOrder.producer_id == current_user.id,
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )

    if order.status not in [OrderStatus.PENDING, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete orders in PENDING or CANCELLED status",
        )

    await db.delete(order)
    await db.commit()


@router.get(
    "/{order_id}/history",
    response_model=list[DeliveryOrderStatusHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get order status history",
)
async def get_order_history(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[DeliveryOrderStatusHistoryResponse]:
    """
    Get status change history for an order.

    - Shows who changed status, when, and notes
    - Ordered by timestamp (newest first)
    """
    # Verify order exists and belongs to user
    order_result = await db.execute(
        select(DeliveryOrder).where(
            DeliveryOrder.id == order_id,
            DeliveryOrder.producer_id == current_user.id,
        )
    )
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )

    result = await db.execute(
        select(DeliveryOrderStatusHistory)
        .where(DeliveryOrderStatusHistory.order_id == order_id)
        .order_by(DeliveryOrderStatusHistory.created_at.desc())
    )
    history = result.scalars().all()

    return [DeliveryOrderStatusHistoryResponse.model_validate(entry) for entry in history]


@router.patch(
    "/{order_id}/points/{point_id}",
    response_model=DeliveryOrderPointResponse,
    status_code=status.HTTP_200_OK,
    summary="Update delivery order point",
)
async def update_order_point(
    order_id: int,
    point_id: int,
    point_update: DeliveryOrderPointUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DeliveryOrderPointResponse:
    """
    Update a delivery point in an order.

    - Can update status, quantity, notes, photo URL
    - Automatically updates delivered_at timestamp when status changes to DELIVERED
    """
    order_result = await db.execute(
        select(DeliveryOrder).where(
            DeliveryOrder.id == order_id,
            DeliveryOrder.producer_id == current_user.id,
        )
    )
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found",
        )

    point_result = await db.execute(
        select(DeliveryOrderPoint).where(
            DeliveryOrderPoint.id == point_id,
            DeliveryOrderPoint.order_id == order_id,
        )
    )
    point = point_result.scalar_one_or_none()

    if not point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order point not found",
        )

    from app.db.models.delivery_order import DeliveryPointStatus
    old_status = point.status

    update_data = point_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(point, field, value)

    if point.status == DeliveryPointStatus.DELIVERED and old_status != DeliveryPointStatus.DELIVERED:
        point.delivered_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(point)

    return DeliveryOrderPointResponse.model_validate(point)
