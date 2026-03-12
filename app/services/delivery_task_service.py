"""Service for building driver delivery tasks from delivery orders.

Aggregates order items by warehouse and distribution center:
- Groups by warehouse (warehouse_lat, warehouse_lon from DeliveryOrderItem)
- For each DeliveryOrderItemPoint: point -> sector (ST_Within) -> DC (ST_Within in sector, or nearest by distance)
- Aggregates by (warehouse, DC, SKU)
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    DeliveryOrder,
    DeliveryOrderItem,
    DeliveryOrderItemDCAllocation,
    DeliveryOrderItemDCStatus,
    DeliveryOrderItemPoint,
    DeliveryOrderItemPointScanEvent,
    DeliveryPoint,
    DistributionCenter,
    Sector,
)
from app.db.models.delivery_order import (
    DeliveryOrderStatusHistory,
    DeliveryPointStatus,
    ItemPointScanPhase,
    OrderStatus,
)
from app.db.models.delivery_task import (
    DriverDeliveryTask,
    DriverTaskDCDelivery,
    DriverTaskDCStatus,
    DriverTaskStatus,
    ItemDCStatus,
)
from app.services.distance_service import DistanceService

logger = logging.getLogger(__name__)


@dataclass
class WarehouseKey:
    """Unique key for warehouse (pickup location)."""

    lat: float
    lon: float

    def __hash__(self) -> int:
        return hash((round(self.lat, 6), round(self.lon, 6)))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, WarehouseKey):
            return False
        return (
            round(self.lat, 6) == round(other.lat, 6)
            and round(self.lon, 6) == round(other.lon, 6)
        )


@dataclass
class TaskItem:
    """SKU + quantity for delivery to one DC."""

    sku_name: str
    sku_code: str
    quantity: int


@dataclass
class DCDelivery:
    """What to deliver to one distribution center."""

    dc_id: int
    dc_name: str
    dc_address: str | None
    dc_lat: float
    dc_lon: float
    items: list[TaskItem] = field(default_factory=list)
    dc_status: str | None = None  # pending, in_transit, delivered (for my tasks)
    dc_delivered_at: datetime | None = None
    unload_photo_media_id: uuid.UUID | None = None


@dataclass
class DriverTask:
    """One driver task: pick up at warehouse, deliver to several DCs."""

    task_id: int
    order_id: int
    order_number: str
    warehouse_lat: float
    warehouse_lon: float
    deliveries: list[DCDelivery] = field(default_factory=list)
    status: str | None = None  # For my tasks: assigned, loading, in_transit, etc.
    loading_photo_media_id: "uuid.UUID | None" = None


class DeliveryTaskService:
    """Builds driver delivery tasks from delivery orders."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.distance_service = DistanceService()

    async def get_orders_ready_for_drivers(
        self, statuses: tuple[OrderStatus, ...] = (OrderStatus.PENDING, OrderStatus.IN_TRANSIT_TO_DC)
    ) -> list[DeliveryOrder]:
        """Get orders that are ready for driver pickup (no producer filter)."""
        query = (
            select(DeliveryOrder)
            .where(DeliveryOrder.status.in_(statuses))
            .order_by(DeliveryOrder.created_at.desc())
        )
        result = await self.db.execute(
            query.options(
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.points
                ).selectinload(DeliveryOrderItemPoint.delivery_point),
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.producer_sku
                ),
            )
        )
        return list(result.scalars().unique().all())

    async def _find_dc_in_sector(
        self,
        sector: Sector,
        sector_dc_cache: dict[int, DistributionCenter | None] | None = None,
    ) -> DistributionCenter | None:
        """Find first DC whose location is within sector boundary (ST_Within)."""
        if sector_dc_cache is not None and sector.id in sector_dc_cache:
            return sector_dc_cache[sector.id]
        result = await self.db.execute(
            select(DistributionCenter)
            .where(
                func.ST_Within(DistributionCenter.location, sector.boundary),
                DistributionCenter.is_active == True,  # noqa: E712
            )
            .order_by(DistributionCenter.id)
            .limit(1)
        )
        dc = result.scalar_one_or_none()
        if sector_dc_cache is not None:
            sector_dc_cache[sector.id] = dc
        return dc

    async def _load_all_active_dcs(
        self,
    ) -> list[DistributionCenter]:
        """Load all active DCs once (avoid N+1 in _find_nearest_dc)."""
        result = await self.db.execute(
            select(DistributionCenter).where(
                DistributionCenter.is_active == True  # noqa: E712
            )
        )
        return list(result.scalars().unique().all())

    async def _find_nearest_dc(
        self,
        point_lat: float,
        point_lon: float,
        dcs: list[DistributionCenter] | None = None,
    ) -> DistributionCenter | None:
        """Find nearest active DC by straight-line distance (haversine)."""
        if dcs is None:
            dcs = await self._load_all_active_dcs()
        if not dcs:
            return None

        best_dc = None
        best_dist = float("inf")
        for dc in dcs:
            dc_lat, dc_lon = self.distance_service.extract_coordinates(dc.location)
            d = self.distance_service.haversine_distance(
                point_lat, point_lon, dc_lat, dc_lon
            )
            if d < best_dist:
                best_dist = d
                best_dc = dc
        return best_dc

    async def _get_dc_for_point(
        self,
        point: DeliveryPoint,
        all_dcs: list[DistributionCenter] | None = None,
        sector_dc_cache: dict[int, DistributionCenter | None] | None = None,
    ) -> DistributionCenter | None:
        """Get DC for delivery point: sector -> DC in sector, or nearest if not in sector."""
        sector_result = await self.db.execute(
            select(Sector)
            .select_from(DeliveryPoint)
            .join(Sector, func.ST_Within(DeliveryPoint.location, Sector.boundary))
            .where(DeliveryPoint.id == point.id)
            .limit(1)
        )
        sector = sector_result.scalar_one_or_none()

        if sector:
            dc = await self._find_dc_in_sector(sector, sector_dc_cache=sector_dc_cache)
            if dc:
                return dc

        point_lat, point_lon = self.distance_service.extract_coordinates(point.location)
        return await self._find_nearest_dc(point_lat, point_lon, dcs=all_dcs)

    async def create_dc_allocations_for_order(
        self, order: DeliveryOrder
    ) -> None:
        """
        Create DeliveryOrderItemDCAllocation and DeliveryOrderItemDCStatus
        for order. For each point: sector -> first DC, or nearest DC if not in sector.
        Aggregates by (order_item_id, dc_id).
        """
        allocation_map: dict[tuple[int, int], int] = defaultdict(int)

        for item in order.items:
            for pt in item.points:
                dp = pt.delivery_point
                if not dp:
                    continue
                dc = await self._get_dc_for_point(dp)
                if not dc:
                    logger.warning(
                        "No DC found for delivery point %s (order_item %s), skipping",
                        dp.id,
                        item.id,
                    )
                    continue
                allocation_map[(item.id, dc.id)] += pt.quantity

        for (order_item_id, dc_id), quantity in allocation_map.items():
            alloc = DeliveryOrderItemDCAllocation(
                order_item_id=order_item_id,
                dc_id=dc_id,
                quantity=quantity,
            )
            self.db.add(alloc)
            await self.db.flush()

            status_rec = DeliveryOrderItemDCStatus(
                order_item_id=order_item_id,
                dc_id=dc_id,
                status=ItemDCStatus.PENDING.value,
            )
            self.db.add(status_rec)

    async def create_driver_tasks_for_order(self, order: DeliveryOrder) -> None:
        """
        Create DriverDeliveryTask and DriverTaskDCDelivery when order goes PENDING.

        Same logic as build_driver_tasks: groups by warehouse, for each warehouse
        creates one task with DC deliveries.         Uses point -> sector -> DC.
        """
        tasks_data: dict[tuple[int, WarehouseKey], set[int]] = defaultdict(set)

        for item in order.items:
            wh_key = WarehouseKey(
                lat=item.warehouse_lat,
                lon=item.warehouse_lon,
            )
            task_key = (order.id, wh_key)

            for pt in item.points:
                dp = pt.delivery_point
                if not dp:
                    continue
                dc = await self._get_dc_for_point(dp)
                if not dc:
                    logger.warning(
                        "No DC found for delivery point %s, skipping",
                        dp.id,
                    )
                    continue
                tasks_data[task_key].add(dc.id)

        for (order_id, wh_key), dc_ids in tasks_data.items():
            task = DriverDeliveryTask(
                order_id=order_id,
                warehouse_lat=wh_key.lat,
                warehouse_lon=wh_key.lon,
                status=DriverTaskStatus.PENDING.value,
            )
            self.db.add(task)
            await self.db.flush()

            for dc_id in dc_ids:
                dc_delivery = DriverTaskDCDelivery(
                    task_id=task.id,
                    dc_id=dc_id,
                    status=DriverTaskDCStatus.PENDING.value,
                )
                self.db.add(dc_delivery)

    async def get_available_tasks_for_driver(
        self,
    ) -> list[DriverTask]:
        """
        Get driver tasks available to take (not yet assigned).

        Returns tasks from DriverDeliveryTask where driver_id is None,
        with full delivery details built from order data.
        """
        result = await self.db.execute(
            select(DriverDeliveryTask)
            .join(DeliveryOrder, DriverDeliveryTask.order_id == DeliveryOrder.id)
            .where(
                DriverDeliveryTask.driver_id.is_(None),
                DriverDeliveryTask.status == DriverTaskStatus.PENDING.value,
                DeliveryOrder.status.in_((OrderStatus.PENDING, OrderStatus.IN_TRANSIT_TO_DC)),
            )
        )
        available_tasks = result.scalars().unique().all()
        if not available_tasks:
            return []

        order_ids = list({t.order_id for t in available_tasks})
        task_by_wh: dict[tuple[int, WarehouseKey], int] = {}
        for t in available_tasks:
            wh = WarehouseKey(lat=t.warehouse_lat, lon=t.warehouse_lon)
            task_by_wh[(t.order_id, wh)] = t.id

        orders_result = await self.db.execute(
            select(DeliveryOrder)
            .where(DeliveryOrder.id.in_(order_ids))
            .options(
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.points
                ).selectinload(DeliveryOrderItemPoint.delivery_point),
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.producer_sku
                ),
            )
        )
        orders = list(orders_result.scalars().unique().all())
        return await self._build_driver_tasks_internal(
            orders, task_id_map=task_by_wh
        )

    async def get_my_assigned_tasks_for_driver(
        self, driver_id: "uuid.UUID"
    ) -> list[DriverTask]:
        """
        Get tasks assigned to this driver (taken, in progress).

        Returns tasks from DriverDeliveryTask where driver_id = driver_id
        and status is not PENDING or DELIVERED.
        """
        active_statuses = (
            DriverTaskStatus.ASSIGNED.value,
            DriverTaskStatus.LOADING.value,
            DriverTaskStatus.IN_TRANSIT.value,
            DriverTaskStatus.PARTIALLY_DELIVERED.value,
        )
        result = await self.db.execute(
            select(DriverDeliveryTask)
            .join(DeliveryOrder, DriverDeliveryTask.order_id == DeliveryOrder.id)
            .where(
                DriverDeliveryTask.driver_id == driver_id,
                DriverDeliveryTask.status.in_(active_statuses),
            )
            .options(selectinload(DriverDeliveryTask.dc_deliveries))
        )
        my_tasks = result.scalars().unique().all()
        if not my_tasks:
            return []

        order_ids = list({t.order_id for t in my_tasks})
        task_by_wh: dict[tuple[int, WarehouseKey], int] = {}
        dc_deliveries_by_task: dict[int, list] = {t.id: list(t.dc_deliveries) for t in my_tasks}
        for t in my_tasks:
            wh = WarehouseKey(lat=t.warehouse_lat, lon=t.warehouse_lon)
            task_by_wh[(t.order_id, wh)] = t.id

        orders_result = await self.db.execute(
            select(DeliveryOrder)
            .where(DeliveryOrder.id.in_(order_ids))
            .options(
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.points
                ).selectinload(DeliveryOrderItemPoint.delivery_point),
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.producer_sku
                ),
            )
        )
        orders = list(orders_result.scalars().unique().all())
        status_by_task: dict[int, str] = {t.id: t.status for t in my_tasks}
        loading_photo_by_task: dict[int, uuid.UUID] = {
            t.id: t.loading_photo_media_id
            for t in my_tasks
            if t.loading_photo_media_id is not None
        }
        return await self._build_driver_tasks_internal(
            orders,
            task_id_map=task_by_wh,
            status_map=status_by_task,
            dc_deliveries_by_task=dc_deliveries_by_task,
            loading_photo_media_id_map=loading_photo_by_task,
        )

    async def get_completed_tasks_for_driver(
        self, driver_id: "uuid.UUID", limit: int = 100
    ) -> list[tuple[int, int, str, datetime]]:
        """
        Get completed delivery tasks for this driver (status=DELIVERED).

        Returns list of (task_id, order_id, order_number, delivered_at) ordered by delivered_at desc.
        """
        result = await self.db.execute(
            select(
                DriverDeliveryTask.id,
                DriverDeliveryTask.order_id,
                DeliveryOrder.order_number,
                DriverDeliveryTask.delivered_at,
            )
            .join(DeliveryOrder, DriverDeliveryTask.order_id == DeliveryOrder.id)
            .where(
                DriverDeliveryTask.driver_id == driver_id,
                DriverDeliveryTask.status == DriverTaskStatus.DELIVERED.value,
                DriverDeliveryTask.delivered_at.isnot(None),
            )
            .order_by(DriverDeliveryTask.delivered_at.desc())
            .limit(limit)
        )
        rows = result.all()
        return [(r[0], r[1], r[2], r[3]) for r in rows]

    async def get_completed_tasks_count_for_driver(
        self, driver_id: "uuid.UUID"
    ) -> int:
        """Return total number of completed tasks for this driver."""
        result = await self.db.execute(
            select(func.count(DriverDeliveryTask.id))
            .where(
                DriverDeliveryTask.driver_id == driver_id,
                DriverDeliveryTask.status == DriverTaskStatus.DELIVERED.value,
                DriverDeliveryTask.delivered_at.isnot(None),
            )
        )
        return result.scalar() or 0

    async def get_completed_tasks_with_deliveries_for_driver(
        self, driver_id: "uuid.UUID", limit: int = 100, offset: int = 0
    ) -> list[tuple[DriverTask, datetime]]:
        """
        Get completed delivery tasks with full DC and SKU details for history.

        Returns list of (DriverTask, delivered_at) ordered by delivered_at desc.
        """
        result = await self.db.execute(
            select(DriverDeliveryTask)
            .join(DeliveryOrder, DriverDeliveryTask.order_id == DeliveryOrder.id)
            .where(
                DriverDeliveryTask.driver_id == driver_id,
                DriverDeliveryTask.status == DriverTaskStatus.DELIVERED.value,
                DriverDeliveryTask.delivered_at.isnot(None),
            )
            .order_by(DriverDeliveryTask.delivered_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(DriverDeliveryTask.dc_deliveries))
        )
        completed_tasks = list(result.scalars().unique().all())
        if not completed_tasks:
            return []

        task_id_map: dict[tuple[int, WarehouseKey], int] = {}
        delivered_at_by_task: dict[int, datetime] = {}
        dc_deliveries_by_task: dict[int, list] = {}
        for t in completed_tasks:
            wh_key = WarehouseKey(lat=t.warehouse_lat, lon=t.warehouse_lon)
            task_id_map[(t.order_id, wh_key)] = t.id
            delivered_at_by_task[t.id] = t.delivered_at
            dc_deliveries_by_task[t.id] = list(t.dc_deliveries)

        order_ids = list({t.order_id for t in completed_tasks})
        orders_result = await self.db.execute(
            select(DeliveryOrder)
            .where(DeliveryOrder.id.in_(order_ids))
            .options(
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.points
                ).selectinload(DeliveryOrderItemPoint.delivery_point),
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.producer_sku
                ),
            )
        )
        orders = list(orders_result.scalars().unique().all())
        driver_tasks = await self._build_driver_tasks_internal(
            orders,
            task_id_map=task_id_map,
            dc_deliveries_by_task=dc_deliveries_by_task,
        )
        # Preserve order by delivered_at desc
        driver_tasks_sorted = sorted(
            driver_tasks,
            key=lambda t: delivered_at_by_task[t.task_id],
            reverse=True,
        )
        return [(t, delivered_at_by_task[t.task_id]) for t in driver_tasks_sorted]

    async def take_task(
        self, task_id: int, driver_id: "uuid.UUID"
    ) -> DriverDeliveryTask | None:
        """
        Assign driver to task. Returns task if successful, None if not available.

        Also updates producer view:
        - All DeliveryOrderItemPoints in this task -> IN_TRANSIT
        - Order status -> DRIVER_ASSIGNED, driver_assigned_at
        """
        from datetime import datetime, timezone

        result = await self.db.execute(
            select(DriverDeliveryTask)
            .where(DriverDeliveryTask.id == task_id)
            .options(selectinload(DriverDeliveryTask.dc_deliveries))
            .with_for_update()
        )
        task = result.scalar_one_or_none()
        if not task:
            return None
        if task.driver_id is not None or task.status != DriverTaskStatus.PENDING.value:
            return None
        task.driver_id = driver_id
        task.status = DriverTaskStatus.ASSIGNED.value
        task.taken_at = datetime.now(timezone.utc)
        await self.db.flush()

        task_dc_ids = {d.dc_id for d in task.dc_deliveries}
        wh_key = WarehouseKey(lat=task.warehouse_lat, lon=task.warehouse_lon)

        orders_result = await self.db.execute(
            select(DeliveryOrder)
            .where(DeliveryOrder.id == task.order_id)
            .options(
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.points
                ).selectinload(DeliveryOrderItemPoint.delivery_point),
            )
        )
        order = orders_result.scalar_one_or_none()
        if not order:
            return task

        points_updated = 0
        for item in order.items:
            if WarehouseKey(lat=item.warehouse_lat, lon=item.warehouse_lon) != wh_key:
                continue
            for pt in item.points:
                if not pt.delivery_point:
                    continue
                dc = await self._get_dc_for_point(pt.delivery_point)
                if dc and dc.id in task_dc_ids and pt.status == DeliveryPointStatus.PENDING.value:
                    pt.status = DeliveryPointStatus.IN_TRANSIT
                    points_updated += 1

        old_order_status = order.status
        order.status = OrderStatus.DRIVER_ASSIGNED
        order.driver_assigned_at = datetime.now(timezone.utc)
        self.db.add(
            DeliveryOrderStatusHistory(
                order_id=order.id,
                changed_by_user_id=None,
                old_status=old_order_status,
                new_status=OrderStatus.DRIVER_ASSIGNED,
                notes="Driver took delivery task",
            )
        )
        logger.info(
            "Driver %s took task %s: updated %d points, order %s -> DRIVER_ASSIGNED",
            driver_id,
            task_id,
            points_updated,
            order.id,
        )
        return task

    async def release_task(
        self, task_id: int, driver_id: "uuid.UUID"
    ) -> DriverDeliveryTask | None:
        """
        Release (cancel) task - return to pending. Only allowed before loading is complete.

        Reverts: task unassigned, order -> PENDING, points -> PENDING.
        """
        cancelable_statuses = (
            DriverTaskStatus.ASSIGNED.value,
            DriverTaskStatus.LOADING.value,
        )
        result = await self.db.execute(
            select(DriverDeliveryTask)
            .where(DriverDeliveryTask.id == task_id)
            .options(selectinload(DriverDeliveryTask.dc_deliveries))
            .with_for_update()
        )
        task = result.scalar_one_or_none()
        if not task:
            return None
        if task.driver_id != driver_id:
            return None
        if task.status not in cancelable_statuses:
            return None

        task.driver_id = None
        task.status = DriverTaskStatus.PENDING.value
        task.taken_at = None
        await self.db.flush()

        task_dc_ids = {d.dc_id for d in task.dc_deliveries}
        wh_key = WarehouseKey(lat=task.warehouse_lat, lon=task.warehouse_lon)

        orders_result = await self.db.execute(
            select(DeliveryOrder)
            .where(DeliveryOrder.id == task.order_id)
            .options(
                selectinload(DeliveryOrder.items).selectinload(
                    DeliveryOrderItem.points
                ).selectinload(DeliveryOrderItemPoint.delivery_point),
            )
        )
        order = orders_result.scalar_one_or_none()
        if order:
            points_reverted = 0
            for item in order.items:
                if WarehouseKey(lat=item.warehouse_lat, lon=item.warehouse_lon) != wh_key:
                    continue
                for pt in item.points:
                    if not pt.delivery_point:
                        continue
                    dc = await self._get_dc_for_point(pt.delivery_point)
                    if dc and dc.id in task_dc_ids and pt.status == DeliveryPointStatus.IN_TRANSIT.value:
                        pt.status = DeliveryPointStatus.PENDING
                        points_reverted += 1

            old_order_status = order.status
            order.status = OrderStatus.PENDING
            order.driver_assigned_at = None
            self.db.add(
                DeliveryOrderStatusHistory(
                    order_id=order.id,
                    changed_by_user_id=None,
                    old_status=old_order_status,
                    new_status=OrderStatus.PENDING,
                    notes="Driver released delivery task",
                )
            )
            logger.info(
                "Driver %s released task %s: reverted %d points, order %s -> PENDING",
                driver_id,
                task_id,
                points_reverted,
                order.id,
            )
        return task

    async def start_loading(
        self, task_id: int, driver_id: "uuid.UUID"
    ) -> DriverDeliveryTask | None:
        """Mark loading started at warehouse. Task must be ASSIGNED. Updates order status for producer."""
        result = await self.db.execute(
            select(DriverDeliveryTask)
            .where(DriverDeliveryTask.id == task_id)
            .with_for_update()
        )
        task = result.scalar_one_or_none()
        if not task or task.driver_id != driver_id:
            return None
        if task.status != DriverTaskStatus.ASSIGNED.value:
            return None
        now = datetime.now(timezone.utc)
        task.status = DriverTaskStatus.LOADING.value
        task.loading_started_at = now
        await self.db.flush()

        order_result = await self.db.execute(
            select(DeliveryOrder)
            .where(DeliveryOrder.id == task.order_id)
            .with_for_update()
        )
        order = order_result.scalar_one_or_none()
        if order and order.status == OrderStatus.DRIVER_ASSIGNED:
            old_status = order.status
            order.status = OrderStatus.LOADING_AT_WAREHOUSE
            self.db.add(
                DeliveryOrderStatusHistory(
                    order_id=order.id,
                    changed_by_user_id=None,
                    old_status=old_status,
                    new_status=OrderStatus.LOADING_AT_WAREHOUSE,
                    notes="Driver arrived, loading at warehouse",
                )
            )
            logger.info("Order %s -> LOADING_AT_WAREHOUSE (driver started loading)", order.id)
        await self.db.flush()
        logger.info("Driver %s started loading task %s", driver_id, task_id)
        return task

    async def depart_from_warehouse(
        self, task_id: int, driver_id: "uuid.UUID"
    ) -> DriverDeliveryTask | None:
        """Mark departed from warehouse (loading done). Task must be LOADING. Updates order → IN_TRANSIT_TO_DC."""
        result = await self.db.execute(
            select(DriverDeliveryTask)
            .where(DriverDeliveryTask.id == task_id)
            .with_for_update()
        )
        task = result.scalar_one_or_none()
        if not task or task.driver_id != driver_id:
            return None
        if task.status != DriverTaskStatus.LOADING.value:
            return None
        now = datetime.now(timezone.utc)
        task.status = DriverTaskStatus.IN_TRANSIT.value
        task.in_transit_at = now
        await self.db.flush()

        order_result = await self.db.execute(
            select(DeliveryOrder)
            .where(DeliveryOrder.id == task.order_id)
            .with_for_update()
        )
        order = order_result.scalar_one_or_none()
        if order and order.status == OrderStatus.LOADING_AT_WAREHOUSE:
            old_status = order.status
            order.status = OrderStatus.IN_TRANSIT_TO_DC
            if order.sent_to_dc_at is None:
                order.sent_to_dc_at = now
            self.db.add(
                DeliveryOrderStatusHistory(
                    order_id=order.id,
                    changed_by_user_id=None,
                    old_status=old_status,
                    new_status=OrderStatus.IN_TRANSIT_TO_DC,
                    notes="Driver departed from warehouse",
                )
            )
            logger.info("Order %s -> IN_TRANSIT_TO_DC (driver departed)", order.id)
        await self.db.flush()
        logger.info("Driver %s departed from warehouse, task %s", driver_id, task_id)
        return task

    async def unload_at_dc(
        self, task_id: int, dc_id: int, driver_id: "uuid.UUID"
    ) -> DriverDeliveryTask | None:
        """
        Mark DC as unloaded (delivered). Updates DriverTaskDCDelivery, DeliveryOrderItemDCStatus.
        If all DCs of task are delivered, sets task DELIVERED; if all tasks of order delivered, sets order COMPLETED.
        """
        result = await self.db.execute(
            select(DriverDeliveryTask)
            .where(DriverDeliveryTask.id == task_id)
            .options(selectinload(DriverDeliveryTask.dc_deliveries))
            .with_for_update()
        )
        task = result.scalar_one_or_none()
        if not task or task.driver_id != driver_id:
            return None
        if task.status not in (
            DriverTaskStatus.IN_TRANSIT.value,
            DriverTaskStatus.PARTIALLY_DELIVERED.value,
        ):
            return None
        dc_del = next((d for d in task.dc_deliveries if d.dc_id == dc_id), None)
        if not dc_del or dc_del.status == DriverTaskDCStatus.DELIVERED.value:
            return None

        now = datetime.now(timezone.utc)
        dc_del.status = DriverTaskDCStatus.DELIVERED.value
        dc_del.delivered_at = now
        await self.db.flush()

        order_item_ids_result = await self.db.execute(
            select(DeliveryOrderItem.id).where(
                DeliveryOrderItem.order_id == task.order_id
            )
        )
        order_item_ids = [r[0] for r in order_item_ids_result.all()]
        if order_item_ids:
            await self.db.execute(
                update(DeliveryOrderItemDCStatus)
                .where(
                    DeliveryOrderItemDCStatus.order_item_id.in_(order_item_ids),
                    DeliveryOrderItemDCStatus.dc_id == dc_id,
                )
                .values(
                    status=ItemDCStatus.DELIVERED.value,
                    delivered_at=now,
                )
            )
            await self.db.flush()

            # Point-level acceptance at DC is now confirmed by RC QR scan,
            # so unload_at_dc no longer changes DeliveryOrderItemPoint status.

        all_dc_delivered = all(
            d.status == DriverTaskDCStatus.DELIVERED.value
            for d in task.dc_deliveries
        )
        if all_dc_delivered:
            task.status = DriverTaskStatus.PARTIALLY_DELIVERED.value
        else:
            task.status = DriverTaskStatus.PARTIALLY_DELIVERED.value
        await self.db.flush()

        logger.info(
            "Driver %s unloaded at DC %s, task %s",
            driver_id,
            dc_id,
            task_id,
        )
        return task

    async def get_dc_receiving_scan_status_for_unload(
        self,
        task_id: int,
        dc_id: int,
        driver_id: "uuid.UUID",
    ) -> tuple[int, int] | None:
        """
        For a task+dc, return (expected_count, received_count) of item-point QR scans at DC.

        expected_count: number of item points in this task (same order + warehouse)
        that belong to the specified DC.
        received_count: how many of expected points already have a DC receiving-stage event
        (RECEIVED_AT_DC or later).

        Returns None when task/DC is not valid for this driver/context.
        """
        task_result = await self.db.execute(
            select(DriverDeliveryTask)
            .where(DriverDeliveryTask.id == task_id)
            .options(selectinload(DriverDeliveryTask.dc_deliveries))
        )
        task = task_result.scalar_one_or_none()
        if not task or task.driver_id != driver_id:
            return None
        if task.status not in (
            DriverTaskStatus.IN_TRANSIT.value,
            DriverTaskStatus.PARTIALLY_DELIVERED.value,
        ):
            return None
        dc_del = next((d for d in task.dc_deliveries if d.dc_id == dc_id), None)
        if not dc_del or dc_del.status == DriverTaskDCStatus.DELIVERED.value:
            return None

        points_result = await self.db.execute(
            select(DeliveryOrderItemPoint)
            .join(DeliveryOrderItem, DeliveryOrderItem.id == DeliveryOrderItemPoint.order_item_id)
            .options(selectinload(DeliveryOrderItemPoint.delivery_point))
            .where(
                DeliveryOrderItem.order_id == task.order_id,
                DeliveryOrderItem.warehouse_lat == task.warehouse_lat,
                DeliveryOrderItem.warehouse_lon == task.warehouse_lon,
            )
        )
        points = points_result.scalars().unique().all()
        if not points:
            return (0, 0)

        delivery_point_ids = list(
            {
                point.delivery_point.id
                for point in points
                if point.delivery_point is not None
            }
        )

        point_sector_map: dict[int, int] = {}
        if delivery_point_ids:
            point_sector_rows = await self.db.execute(
                select(DeliveryPoint.id, Sector.id)
                .select_from(DeliveryPoint)
                .join(Sector, func.ST_Within(DeliveryPoint.location, Sector.boundary))
                .where(DeliveryPoint.id.in_(delivery_point_ids))
                .order_by(DeliveryPoint.id.asc(), Sector.id.asc())
            )
            for point_id, sector_id in point_sector_rows.all():
                point_sector_map.setdefault(point_id, sector_id)

        sector_ids = list(set(point_sector_map.values()))
        sector_dc_map: dict[int, int] = {}
        if sector_ids:
            sector_dc_rows = await self.db.execute(
                select(Sector.id, DistributionCenter.id)
                .select_from(Sector)
                .join(
                    DistributionCenter,
                    func.ST_Within(DistributionCenter.location, Sector.boundary),
                )
                .where(
                    Sector.id.in_(sector_ids),
                    DistributionCenter.is_active == True,  # noqa: E712
                )
                .order_by(Sector.id.asc(), DistributionCenter.id.asc())
            )
            for sector_id, resolved_dc_id in sector_dc_rows.all():
                sector_dc_map.setdefault(sector_id, resolved_dc_id)

        active_dcs_result = await self.db.execute(
            select(DistributionCenter).where(
                DistributionCenter.is_active == True  # noqa: E712
            )
        )
        active_dcs = active_dcs_result.scalars().all()

        point_to_dc_map: dict[int, int | None] = {}
        nearest_dc_by_delivery_point_id: dict[int, int | None] = {}
        for point in points:
            if point.delivery_point is None:
                point_to_dc_map[point.id] = None
                continue
            dp_id = point.delivery_point.id
            sector_id = point_sector_map.get(dp_id)
            resolved_dc_id = sector_dc_map.get(sector_id) if sector_id is not None else None
            if resolved_dc_id is None:
                if dp_id not in nearest_dc_by_delivery_point_id:
                    lat, lon = self.distance_service.extract_coordinates(
                        point.delivery_point.location
                    )
                    best_dc_id = None
                    best_dist = float("inf")
                    for active_dc in active_dcs:
                        dc_lat, dc_lon = self.distance_service.extract_coordinates(
                            active_dc.location
                        )
                        dist = self.distance_service.haversine_distance(
                            lat, lon, dc_lat, dc_lon
                        )
                        if dist < best_dist:
                            best_dist = dist
                            best_dc_id = active_dc.id
                    nearest_dc_by_delivery_point_id[dp_id] = best_dc_id
                resolved_dc_id = nearest_dc_by_delivery_point_id[dp_id]
            point_to_dc_map[point.id] = resolved_dc_id

        expected_point_ids = {
            point.id for point in points if point_to_dc_map.get(point.id) == dc_id
        }
        if not expected_point_ids:
            return (0, 0)

        received_phases = (
            ItemPointScanPhase.RECEIVED_AT_DC,
            ItemPointScanPhase.MOVED_TO_SORTING,
            ItemPointScanPhase.SORTED_TO_ZONE,
            ItemPointScanPhase.HANDED_TO_COURIER2,
        )
        received_rows = await self.db.execute(
            select(func.distinct(DeliveryOrderItemPointScanEvent.delivery_order_item_point_id))
            .where(
                DeliveryOrderItemPointScanEvent.delivery_order_item_point_id.in_(
                    list(expected_point_ids)
                ),
                DeliveryOrderItemPointScanEvent.phase.in_(received_phases),
            )
        )
        received_point_ids = {row[0] for row in received_rows.all()}
        return (len(expected_point_ids), len(received_point_ids))

    async def complete_task(
        self, task_id: int, driver_id: "uuid.UUID"
    ) -> DriverDeliveryTask | None:
        """
        Manually complete the task (after all DCs are unloaded). Sets task DELIVERED.
        If all tasks of the order are delivered, sets order AT_DC and completed_at.
        """
        result = await self.db.execute(
            select(DriverDeliveryTask)
            .where(
                DriverDeliveryTask.id == task_id,
                DriverDeliveryTask.driver_id == driver_id,
            )
            .options(selectinload(DriverDeliveryTask.dc_deliveries))
            .with_for_update()
        )
        task = result.scalar_one_or_none()
        if not task:
            return None
        if task.status not in (
            DriverTaskStatus.IN_TRANSIT.value,
            DriverTaskStatus.PARTIALLY_DELIVERED.value,
        ):
            return None
        all_dc_delivered = all(
            d.status == DriverTaskDCStatus.DELIVERED.value
            for d in task.dc_deliveries
        )
        if not all_dc_delivered:
            return None

        now = datetime.now(timezone.utc)
        task.status = DriverTaskStatus.DELIVERED.value
        task.delivered_at = now
        await self.db.flush()

        all_tasks_result = await self.db.execute(
            select(DriverDeliveryTask).where(
                DriverDeliveryTask.order_id == task.order_id
            )
        )
        all_tasks = all_tasks_result.scalars().all()
        if all(
            t.status == DriverTaskStatus.DELIVERED.value for t in all_tasks
        ):
            order_result = await self.db.execute(
                select(DeliveryOrder)
                .where(DeliveryOrder.id == task.order_id)
                .with_for_update()
            )
            order = order_result.scalar_one_or_none()
            if order:
                old_status = order.status
                order.status = OrderStatus.AT_DC
                order.completed_at = now
                self.db.add(
                    DeliveryOrderStatusHistory(
                        order_id=order.id,
                        changed_by_user_id=None,
                        old_status=old_status,
                        new_status=OrderStatus.AT_DC,
                        notes="Driver completed delivery to DCs",
                    )
                )
                logger.info(
                    "Order %s completed by driver (at_dc)",
                    order.id,
                )
        logger.info("Driver %s completed task %s", driver_id, task_id)
        return task

    async def build_driver_tasks(
        self, orders: list[DeliveryOrder]
    ) -> list[DriverTask]:
        """
        Build driver tasks from orders (legacy, no task_id filtering).

        Groups by (order, warehouse). Different warehouses in one order
        produce separate tasks. Each task: warehouse -> list of (DC, items).
        """
        return await self._build_driver_tasks_internal(orders, task_id_map=None)

    async def _build_driver_tasks_internal(
        self,
        orders: list[DeliveryOrder],
        task_id_map: dict[tuple[int, WarehouseKey], int] | None = None,
        status_map: dict[int, str] | None = None,
        dc_deliveries_by_task: dict[int, list] | None = None,
        loading_photo_media_id_map: dict[int, uuid.UUID] | None = None,
    ) -> list[DriverTask]:
        """Internal: build DriverTask list, optionally with task_id and per-DC status from map."""
        tasks_data: dict[
            tuple[int, str, WarehouseKey],
            dict[int, dict[tuple[str, str], int]],
        ] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        dc_by_point_id: dict[int, DistributionCenter | None] = {}
        sector_dc_cache: dict[int, DistributionCenter | None] = {}
        all_dcs = await self._load_all_active_dcs()

        for order in orders:
            for item in order.items:
                wh_key = WarehouseKey(
                    lat=item.warehouse_lat,
                    lon=item.warehouse_lon,
                )
                task_key = (order.id, order.order_number, wh_key)

                sku_name = "Unknown"
                sku_code = ""
                if item.sku_snapshot:
                    sku_name = item.sku_snapshot.get("name", "Unknown")
                    sku_code = item.sku_snapshot.get("sku_code", "")
                elif item.producer_sku:
                    sku_name = item.producer_sku.name
                    sku_code = item.producer_sku.sku_code or ""

                for pt in item.points:
                    dp = pt.delivery_point
                    if not dp:
                        continue
                    if dp.id not in dc_by_point_id:
                        dc_by_point_id[dp.id] = await self._get_dc_for_point(
                            dp, all_dcs=all_dcs, sector_dc_cache=sector_dc_cache
                        )
                    dc = dc_by_point_id[dp.id]
                    if not dc:
                        logger.warning(
                            "No DC found for delivery point %s, skipping",
                            dp.id,
                        )
                        continue

                    tasks_data[task_key][dc.id][(sku_name, sku_code)] += pt.quantity

        all_dc_ids: set[int] = set()
        for dc_sku_qtys in tasks_data.values():
            all_dc_ids |= set(dc_sku_qtys.keys())
        dc_rows_map: dict[int, DistributionCenter] = {}
        if all_dc_ids:
            dc_result = await self.db.execute(
                select(DistributionCenter).where(DistributionCenter.id.in_(all_dc_ids))
            )
            for row in dc_result.scalars().unique().all():
                dc_rows_map[row.id] = row

        result: list[DriverTask] = []
        for (order_id, order_number, wh_key), dc_sku_qtys in tasks_data.items():
            task_id = (task_id_map or {}).get((order_id, wh_key), 0)
            if task_id_map is not None and task_id == 0:
                continue
            deliveries: list[DCDelivery] = []
            dc_status_map: dict[int, tuple[str, datetime | None, uuid.UUID | None]] = {}
            if dc_deliveries_by_task and task_id:
                for d in dc_deliveries_by_task.get(task_id, []):
                    dc_status_map[d.dc_id] = (
                        d.status,
                        d.delivered_at,
                        getattr(d, "unload_photo_media_id", None),
                    )
            for dc_id, sku_qtys in dc_sku_qtys.items():
                dc_row = dc_rows_map.get(dc_id)
                if not dc_row:
                    continue
                dc_lat, dc_lon = self.distance_service.extract_coordinates(
                    dc_row.location
                )
                items = [
                    TaskItem(sku_name=name, sku_code=code, quantity=qty)
                    for (name, code), qty in sku_qtys.items()
                ]
                st, delivered_at, unload_photo = dc_status_map.get(
                    dc_id, (None, None, None)
                )
                deliveries.append(
                    DCDelivery(
                        dc_id=dc_row.id,
                        dc_name=dc_row.name,
                        dc_address=dc_row.address,
                        dc_lat=dc_lat,
                        dc_lon=dc_lon,
                        items=items,
                        dc_status=st,
                        dc_delivered_at=delivered_at,
                        unload_photo_media_id=unload_photo,
                    )
                )
            task_status = (status_map or {}).get(task_id) if task_id else None
            loading_photo_media_id = (loading_photo_media_id_map or {}).get(task_id) if task_id else None
            result.append(
                DriverTask(
                    task_id=task_id,
                    order_id=order_id,
                    order_number=order_number,
                    warehouse_lat=wh_key.lat,
                    warehouse_lon=wh_key.lon,
                    deliveries=deliveries,
                    status=task_status,
                    loading_photo_media_id=loading_photo_media_id,
                )
            )
        return result
