"""Service layer for delivery orders (new structure with templates)."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.delivery_order import (DeliveryOrder, DeliveryOrderItem,
                                          DeliveryOrderItemPoint,
                                          DeliveryOrderStatusHistory,
                                          OrderStatus)
from app.services.delivery_template_service import DeliveryTemplateService


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


class DeliveryOrderService:
    """Service for managing delivery orders."""

    @staticmethod
    async def create_order_from_templates(
        db: AsyncSession,
        user_id: int,
        template_ids: list[int],
        status: OrderStatus = OrderStatus.PENDING,
        producer_notes: str | None = None,
        priority: str = "normal",
        expected_pickup_date: datetime | None = None,
        delivery_deadline: datetime | None = None,
    ) -> DeliveryOrder:
        """
        Create a delivery order from one or more templates.

        This creates snapshots of the templates at the time of order creation.
        """
        templates = []
        for template_id in template_ids:
            template = await DeliveryTemplateService.get_template_by_id(
                db, template_id, user_id, with_points=True
            )
            if not template:
                raise ValueError(f"Template {template_id} not found")
            if not template.is_active:
                raise ValueError(f"Template {template_id} is not active")
            if not template.points:
                raise ValueError(f"Template {template_id} has no delivery points")

            templates.append(template)

        order_number = await generate_order_number(db)

        total_quantity = sum(t.total_quantity for t in templates)
        total_cost = sum(t.estimated_cost or 0 for t in templates)

        order = DeliveryOrder(
            order_number=order_number,
            producer_id=user_id,
            total_quantity=total_quantity,
            total_cost=total_cost,
            status=status,
            priority=priority,
            producer_notes=producer_notes,
            expected_pickup_date=expected_pickup_date,
            delivery_deadline=delivery_deadline,
        )
        db.add(order)
        await db.flush()

        for template in templates:
            await db.refresh(template, ["producer_sku"])
            sku = template.producer_sku

            sku_snapshot = {
                "name": sku.name,
                "sku_code": sku.sku_code,
                "weight_kg": float(sku.weight_kg),
                "length_cm": float(sku.length_cm),
                "width_cm": float(sku.width_cm),
                "height_cm": float(sku.height_cm),
                "items_per_box": sku.items_per_box,
            }

            order_item = DeliveryOrderItem(
                order_id=order.id,
                template_id=template.id,
                template_name=template.name,
                producer_sku_id=template.producer_sku_id,
                sku_snapshot=sku_snapshot,
                region_id=template.region_id,
                warehouse_lat=template.warehouse_lat,
                warehouse_lon=template.warehouse_lon,
                quantity=template.total_quantity,
                item_cost=template.estimated_cost,
                cost_per_unit=template.cost_per_unit,
            )
            db.add(order_item)
            await db.flush()

            for template_point in template.points:
                order_item_point = DeliveryOrderItemPoint(
                    order_item_id=order_item.id,
                    delivery_point_id=template_point.delivery_point_id,
                    quantity=template_point.quantity,
                    delivery_notes=template_point.notes,
                )
                db.add(order_item_point)

            await DeliveryTemplateService.increment_usage_count(db, template.id)

        history_entry = DeliveryOrderStatusHistory(
            order_id=order.id,
            changed_by_user_id=user_id,
            old_status=None,
            new_status=status,
            notes="Order created from templates",
        )
        db.add(history_entry)

        await db.commit()
        await db.refresh(order)

        return order

    @staticmethod
    async def get_order_by_id(
        db: AsyncSession,
        order_id: int,
        user_id: int,
        with_items: bool = False,
    ) -> DeliveryOrder | None:
        """Get order by ID (with ownership check)."""
        query = select(DeliveryOrder).where(
            DeliveryOrder.id == order_id,
            DeliveryOrder.producer_id == user_id,
        )

        if with_items:
            query = query.options(
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.points
                )
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_orders(
        db: AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
        status_filter: OrderStatus | None = None,
    ) -> tuple[list[DeliveryOrder], int]:
        """Get paginated orders for a user."""
        query = select(DeliveryOrder).where(DeliveryOrder.producer_id == user_id)

        if status_filter:
            query = query.where(DeliveryOrder.status == status_filter)

        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(DeliveryOrder.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        orders = list(result.scalars().all())

        return orders, total

    @staticmethod
    async def update_order_status(
        db: AsyncSession,
        order: DeliveryOrder,
        new_status: OrderStatus,
        user_id: int,
        notes: str | None = None,
    ) -> DeliveryOrder:
        """Update order status with history logging."""
        old_status = order.status
        order.status = new_status

        now = datetime.now(timezone.utc)
        if new_status == OrderStatus.IN_TRANSIT_TO_DC:
            order.sent_to_dc_at = now
        elif new_status == OrderStatus.AT_DC:
            order.arrived_at_dc_at = now
        elif new_status == OrderStatus.DRIVER_ASSIGNED:
            order.driver_assigned_at = now
        elif new_status == OrderStatus.IN_DELIVERY:
            order.delivery_started_at = now
        elif new_status == OrderStatus.COMPLETED:
            order.completed_at = now

        history_entry = DeliveryOrderStatusHistory(
            order_id=order.id,
            changed_by_user_id=user_id,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
        )
        db.add(history_entry)

        await db.commit()
        await db.refresh(order)

        return order

    @staticmethod
    async def delete_order(db: AsyncSession, order: DeliveryOrder) -> None:
        """Delete order (only if in PENDING or CANCELLED status)."""
        if order.status not in [OrderStatus.PENDING, OrderStatus.CANCELLED, OrderStatus.DRAFT]:
            raise ValueError("Can only delete orders in PENDING, DRAFT, or CANCELLED status")

        await db.delete(order)
        await db.commit()

    @staticmethod
    async def get_order_history(
        db: AsyncSession,
        order_id: int,
        user_id: int,
    ) -> list[DeliveryOrderStatusHistory]:
        """Get status change history for an order."""
        order = await DeliveryOrderService.get_order_by_id(db, order_id, user_id)
        if not order:
            raise ValueError("Order not found")

        result = await db.execute(
            select(DeliveryOrderStatusHistory)
            .where(DeliveryOrderStatusHistory.order_id == order_id)
            .order_by(DeliveryOrderStatusHistory.created_at.desc())
        )

        return list(result.scalars().all())
