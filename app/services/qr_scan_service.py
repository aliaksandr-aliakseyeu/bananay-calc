"""
QR scan service: resolve token, validate phase, record audit events.

Scans are audit-only; order/point status transitions stay in DeliveryTaskService.
Extensible: phase validation is delegated so at_dc / handover can be added later.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    DeliveryOrderItemPoint,
    DeliveryOrderItemPointScanEvent,
    DriverDeliveryTask,
    ItemPointScanPhase,
)
from app.db.models.delivery_order import DeliveryOrderItem
from app.db.models.delivery_task import DriverTaskStatus


@dataclass(frozen=True)
class ScanResult:
    """Result of a successful scan (for API response)."""

    delivery_order_item_point_id: int
    order_id: int
    quantity: int
    delivery_point_name: str | None
    sku_name: str | None


class QrScanService:
    """Service for recording and validating QR scans. Audit-only; no status changes."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_item_point_by_token(
        self, qr_token: uuid.UUID
    ) -> DeliveryOrderItemPoint | None:
        """Resolve qr_token to DeliveryOrderItemPoint with order_item (for order_id)."""
        result = await self.db.execute(
            select(DeliveryOrderItemPoint)
            .where(DeliveryOrderItemPoint.qr_token == qr_token)
            .options(
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                    DeliveryOrderItem.producer_sku
                ),
                selectinload(DeliveryOrderItemPoint.delivery_point),
            )
        )
        return result.scalar_one_or_none()

    async def get_loading_scan_status(
        self, task_id: int
    ) -> tuple[int, int] | None:
        """
        For a driver task, return (expected_count, scanned_count) for loading phase.

        expected_count = number of delivery_order_item_points that belong to this task
        (same order_id + same warehouse_lat/lon on order_item).
        scanned_count = number of distinct item_points that have at least one
        DeliveryOrderItemPointScanEvent with phase=loading.

        Returns None if task not found.
        """
        result = await self.db.execute(
            select(DriverDeliveryTask)
            .where(DriverDeliveryTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            return None

        # expected: count item_points where order_item.order_id = task.order_id
        # and order_item.warehouse_lat/lon = task.warehouse_lat/lon
        expected_q = (
            select(func.count(DeliveryOrderItemPoint.id))
            .join(DeliveryOrderItem, DeliveryOrderItemPoint.order_item_id == DeliveryOrderItem.id)
            .where(
                DeliveryOrderItem.order_id == task.order_id,
                DeliveryOrderItem.warehouse_lat == task.warehouse_lat,
                DeliveryOrderItem.warehouse_lon == task.warehouse_lon,
            )
        )
        expected_result = await self.db.execute(expected_q)
        expected_count = expected_result.scalar() or 0

        # scanned: count distinct item_point_id from scan_events (phase=loading)
        # where item_point belongs to this task
        scanned_q = (
            select(func.count(distinct(DeliveryOrderItemPointScanEvent.delivery_order_item_point_id)))
            .join(
                DeliveryOrderItemPoint,
                DeliveryOrderItemPointScanEvent.delivery_order_item_point_id == DeliveryOrderItemPoint.id,
            )
            .join(DeliveryOrderItem, DeliveryOrderItemPoint.order_item_id == DeliveryOrderItem.id)
            .where(
                DeliveryOrderItem.order_id == task.order_id,
                DeliveryOrderItem.warehouse_lat == task.warehouse_lat,
                DeliveryOrderItem.warehouse_lon == task.warehouse_lon,
                DeliveryOrderItemPointScanEvent.phase == ItemPointScanPhase.LOADING,
            )
        )
        scanned_result = await self.db.execute(scanned_q)
        scanned_count = scanned_result.scalar() or 0

        return (expected_count, scanned_count)

    def _validate_loading(
        self,
        task: DriverDeliveryTask,
        item_point: DeliveryOrderItemPoint,
        driver_id: uuid.UUID,
    ) -> bool:
        """
        Validate that this driver can record a loading scan for this item point.

        Task must be assigned to driver, in status assigned or loading,
        and task.order_id must match the item point's order.
        """
        if task.driver_id != driver_id:
            return False
        if task.status not in (
            DriverTaskStatus.ASSIGNED.value,
            DriverTaskStatus.LOADING.value,
        ):
            return False
        order_id = item_point.order_item.order_id
        return task.order_id == order_id

    async def record_loading_scan(
        self,
        task_id: int,
        driver_id: uuid.UUID,
        qr_token: uuid.UUID,
    ) -> ScanResult:
        """
        Record a loading-phase scan for the given task and qr_token.

        Validates: token resolves to an item point; task is assigned to driver
        and in assigned/loading; item point belongs to task's order.
        Writes audit event only; does not change order/point status.

        Returns ScanResult on success.
        Raises ValueError with a message key for 404/403.
        """
        item_point = await self.get_item_point_by_token(qr_token)
        if not item_point:
            raise ValueError("qr_token_not_found")

        result = await self.db.execute(
            select(DriverDeliveryTask).where(DriverDeliveryTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise ValueError("task_not_found")

        if not self._validate_loading(task, item_point, driver_id):
            if task.driver_id != driver_id:
                raise ValueError("task_not_assigned_to_driver")
            if task.order_id != item_point.order_item.order_id:
                raise ValueError("item_point_not_in_task_order")
            raise ValueError("invalid_state_for_scan")

        event = DeliveryOrderItemPointScanEvent(
            delivery_order_item_point_id=item_point.id,
            phase=ItemPointScanPhase.LOADING,
            scanned_by_driver_id=driver_id,
        )
        self.db.add(event)
        await self.db.flush()

        delivery_point_name = None
        if item_point.delivery_point:
            delivery_point_name = getattr(
                item_point.delivery_point, "name", None
            ) or getattr(item_point.delivery_point, "title", None)

        sku_name = None
        if item_point.order_item and getattr(
            item_point.order_item, "producer_sku", None
        ):
            sku_name = getattr(
                item_point.order_item.producer_sku, "name", None
            )

        return ScanResult(
            delivery_order_item_point_id=item_point.id,
            order_id=item_point.order_item.order_id,
            quantity=item_point.quantity,
            delivery_point_name=delivery_point_name,
            sku_name=sku_name,
        )
