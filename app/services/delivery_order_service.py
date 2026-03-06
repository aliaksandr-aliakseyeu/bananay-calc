"""Service layer for delivery orders (new structure with templates)."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.delivery_order import (
    DeliveryOrder,
    DeliveryOrderItem,
    DeliveryOrderItemPoint,
    DeliveryOrderStatusHistory,
    DeliveryPointStatus,
    OrderStatus,
)
from app.db.models.delivery_task import DriverDeliveryTask, DriverTaskDCDelivery
from app.db.models.driver_account import DriverAccount
from app.schemas.delivery_order_new import (
    AssignedDriverInfo,
    DeliveryCenterInfo,
    DeliveryOrderDetailResponse,
)
from app.services.delivery_task_service import DeliveryTaskService
from app.services.delivery_template_service import DeliveryTemplateService
from app.services.distance_service import DistanceService


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

        result = await db.execute(
            select(DeliveryOrder)
            .where(DeliveryOrder.id == order.id)
            .options(
                selectinload(DeliveryOrder.items)
                .selectinload(DeliveryOrderItem.points)
                .selectinload(DeliveryOrderItemPoint.delivery_point),
            )
        )
        order = result.scalar_one()
        task_service = DeliveryTaskService(db)
        await task_service.create_dc_allocations_for_order(order)
        if status == OrderStatus.PENDING:
            await task_service.create_driver_tasks_for_order(order)

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
    async def get_assigned_driver_for_order(
        db: AsyncSession, order_id: int
    ) -> dict | None:
        """Get assigned driver info for order (first driver who took a task)."""
        result = await db.execute(
            select(DriverDeliveryTask)
            .where(
                DriverDeliveryTask.order_id == order_id,
                DriverDeliveryTask.driver_id.isnot(None),
            )
            .limit(1)
        )
        task = result.scalar_one_or_none()
        if not task or not task.driver_id:
            return None
        driver = await db.get(DriverAccount, task.driver_id)
        if not driver:
            return None
        phone_full = driver.phone_e164 or ""
        phone = phone_full.replace(" ", "").replace("-", "")
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) >= 4:
            last4 = digits[-4:]
            phone_masked = f"+7 *** *** {last4[:2]} {last4[2:]}"
        else:
            phone_masked = "+7 *** *** ** **"
        return {
            "id": str(driver.id),
            "full_name": driver.full_name,
            "phone": phone_full or None,
            "phone_masked": phone_masked,
            "city": driver.city,
        }

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
                ).selectinload(DeliveryOrderItemPoint.delivery_point),
            )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_order_by_id_any(
        db: AsyncSession,
        order_id: int,
        with_items: bool = False,
    ) -> DeliveryOrder | None:
        """Get order by ID without producer check (for internal use, e.g. SSE broadcast)."""
        query = select(DeliveryOrder).where(DeliveryOrder.id == order_id)
        if with_items:
            query = query.options(
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.points
                ).selectinload(DeliveryOrderItemPoint.delivery_point),
            )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_order_snapshot_for_sse(
        db: AsyncSession, order_id: int
    ) -> dict | None:
        """
        Build full order detail snapshot for producer (same shape as GET order).
        Used to broadcast order_update over SSE. Returns JSON-serializable dict or None.
        """
        order = await DeliveryOrderService.get_order_by_id_any(
            db, order_id, with_items=True
        )
        if not order:
            return None
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
                orm_pt = (
                    order.items[idx_i].points[idx_p]
                    if idx_i < len(order.items)
                    else None
                )
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
                new_points.append(
                    pt.model_copy(
                        update={
                            "lat": lat,
                            "lon": lon,
                            "delivery_point_name": delivery_point_name,
                            "delivery_point_address": delivery_point_address,
                        }
                    )
                )
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
            dc_list = await DeliveryOrderService.get_order_delivery_centers(
                db, order_id
            )
            if dc_list:
                response = response.model_copy(
                    update={
                        "delivery_centers": [
                            DeliveryCenterInfo(**dc) for dc in dc_list
                        ]
                    }
                )
        return response.model_dump(mode="json")

    @staticmethod
    async def get_order_delivery_centers(
        db: AsyncSession, order_id: int
    ) -> list[dict]:
        """
        Get unique DCs where goods were delivered for this order (for producer when status is at_dc).
        Returns list of {id, name, address, lat, lon}.
        """
        result = await db.execute(
            select(DriverDeliveryTask)
            .where(DriverDeliveryTask.order_id == order_id)
            .options(
                selectinload(DriverDeliveryTask.dc_deliveries).selectinload(
                    DriverTaskDCDelivery.dc
                )
            )
        )
        tasks = list(result.scalars().all())
        seen_dc_ids: set[int] = set()
        out: list[dict] = []
        distance_service = DistanceService()
        for task in tasks:
            for dc_del in task.dc_deliveries or []:
                if not dc_del.dc or dc_del.dc_id in seen_dc_ids:
                    continue
                seen_dc_ids.add(dc_del.dc_id)
                dc = dc_del.dc
                try:
                    lat, lon = distance_service.extract_coordinates(dc.location)
                except Exception:
                    continue
                out.append({
                    "id": dc.id,
                    "name": dc.name,
                    "address": dc.address or None,
                    "lat": lat,
                    "lon": lon,
                })
        return out

    @staticmethod
    async def get_order_dc_unload_photos(
        db: AsyncSession,
        order: DeliveryOrder,
    ) -> dict[int, UUID]:
        """
        For producer view: map point_id -> unload_photo_media_id for points with status at_dc.
        Requires order loaded with items, points, and delivery_point.
        """
        result = await db.execute(
            select(DriverDeliveryTask)
            .where(DriverDeliveryTask.order_id == order.id)
            .options(selectinload(DriverDeliveryTask.dc_deliveries))
            .limit(1)
        )
        task = result.scalar_one_or_none()
        if not task or not task.dc_deliveries:
            return {}

        dc_photo_map: dict[int, UUID] = {}
        for d in task.dc_deliveries:
            if d.unload_photo_media_id:
                dc_photo_map[d.dc_id] = d.unload_photo_media_id

        if not dc_photo_map:
            return {}

        task_service = DeliveryTaskService(db)
        point_photo_map: dict[int, UUID] = {}
        for item in order.items or []:
            for pt in item.points or []:
                if pt.status != DeliveryPointStatus.AT_DC or not getattr(pt, "delivery_point", None):
                    continue
                dc = await task_service._get_dc_for_point(pt.delivery_point)
                if dc and dc.id in dc_photo_map:
                    point_photo_map[pt.id] = dc_photo_map[dc.id]
        return point_photo_map

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

        if old_status == OrderStatus.DRAFT and new_status == OrderStatus.PENDING:
            load_result = await db.execute(
                select(DeliveryOrder)
                .where(DeliveryOrder.id == order.id)
                .options(
                    selectinload(DeliveryOrder.items)
                    .selectinload(DeliveryOrderItem.points)
                    .selectinload(DeliveryOrderItemPoint.delivery_point),
                )
            )
            order = load_result.scalar_one()
            order.status = new_status  # restore after load (DB has old status)
            task_service = DeliveryTaskService(db)
            await task_service.create_driver_tasks_for_order(order)

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
