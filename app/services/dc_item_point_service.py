"""Service for DC QR scanning over DeliveryOrderItemPoint."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    CourierDeliveryTask,
    DcAccount,
    DeliveryOrderItem,
    DeliveryOrderItemPoint,
    DeliveryOrderItemPointScanEvent,
    DeliveryPoint,
    DeliveryPointStatus,
    DistributionCenter,
    Sector,
)
from app.db.models.delivery_order import ItemPointScanPhase
from app.services.delivery_task_service import DeliveryTaskService


@dataclass(frozen=True)
class DcItemPointScanResult:
    """Scan result for DC API layer."""

    item_point: DeliveryOrderItemPoint
    event: DeliveryOrderItemPointScanEvent
    stage: ItemPointScanPhase
    is_idempotent: bool
    distribution_center_id: int


class DcItemPointService:
    """State machine + validation for DC scans tied to existing item points."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_item_point(self, qr_token: uuid.UUID) -> DeliveryOrderItemPoint | None:
        result = await self.db.execute(
            select(DeliveryOrderItemPoint)
            .where(DeliveryOrderItemPoint.qr_token == qr_token)
            .options(
                selectinload(DeliveryOrderItemPoint.order_item),
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                    DeliveryOrderItem.producer_sku
                ),
                selectinload(DeliveryOrderItemPoint.delivery_point),
            )
        )
        return result.scalar_one_or_none()

    async def _get_latest_event(
        self,
        item_point_id: int,
    ) -> DeliveryOrderItemPointScanEvent | None:
        result = await self.db.execute(
            select(DeliveryOrderItemPointScanEvent)
            .where(DeliveryOrderItemPointScanEvent.delivery_order_item_point_id == item_point_id)
            .order_by(
                DeliveryOrderItemPointScanEvent.scanned_at.desc(),
                DeliveryOrderItemPointScanEvent.id.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_event_by_operation(
        self,
        item_point_id: int,
        phase: ItemPointScanPhase,
        operation_id: uuid.UUID | None,
    ) -> DeliveryOrderItemPointScanEvent | None:
        if operation_id is None:
            return None
        result = await self.db.execute(
            select(DeliveryOrderItemPointScanEvent).where(
                DeliveryOrderItemPointScanEvent.delivery_order_item_point_id == item_point_id,
                DeliveryOrderItemPointScanEvent.phase == phase,
                DeliveryOrderItemPointScanEvent.operation_id == operation_id,
            )
        )
        return result.scalar_one_or_none()

    async def _resolve_point_dc_id(self, item_point: DeliveryOrderItemPoint) -> int | None:
        if item_point.delivery_point is None:
            return None
        delivery_point = item_point.delivery_point
        sector_result = await self.db.execute(
            select(Sector)
            .where(func.ST_Within(delivery_point.location, Sector.boundary))
            .limit(1)
        )
        sector = sector_result.scalar_one_or_none()
        if sector:
            dc_result = await self.db.execute(
                select(DistributionCenter)
                .where(
                    func.ST_Within(DistributionCenter.location, sector.boundary),
                    DistributionCenter.is_active == True,  # noqa: E712
                )
                .order_by(DistributionCenter.id)
                .limit(1)
            )
            dc = dc_result.scalar_one_or_none()
            if dc:
                return dc.id
        task_service = DeliveryTaskService(self.db)
        lat, lon = task_service.distance_service.extract_coordinates(delivery_point.location)
        nearest = await task_service._find_nearest_dc(lat, lon)  # noqa: SLF001
        return nearest.id if nearest else None

    async def _batch_resolve_point_dc_ids(
        self,
        item_points: list[DeliveryOrderItemPoint],
    ) -> dict[int, int | None]:
        """
        Resolve distribution_center_id for many item_points in batch (avoids N+1).
        Returns map: item_point.id -> dc_id or None.
        """
        if not item_points:
            return {}
        dp_ids = []
        for ip in item_points:
            if ip.delivery_point_id is not None:
                dp_ids.append(ip.delivery_point_id)
        dp_ids = list(dict.fromkeys(dp_ids))
        dp_to_dc: dict[int, int] = {}
        if dp_ids:
            batch_result = await self.db.execute(
                select(DeliveryPoint.id, DistributionCenter.id)
                .select_from(DeliveryPoint)
                .join(Sector, func.ST_Within(DeliveryPoint.location, Sector.boundary))
                .join(
                    DistributionCenter,
                    (DistributionCenter.is_active == True)  # noqa: E712
                    & func.ST_Within(DistributionCenter.location, Sector.boundary),
                )
                .where(DeliveryPoint.id.in_(dp_ids))
            )
            for row in batch_result.all():
                dp_id, dc_id = row[0], row[1]
                if dp_id not in dp_to_dc:
                    dp_to_dc[dp_id] = dc_id
        task_service = DeliveryTaskService(self.db)
        all_dcs: list[DistributionCenter] | None = None
        result: dict[int, int | None] = {}
        for ip in item_points:
            dc_id = None
            if ip.delivery_point_id is not None:
                dc_id = dp_to_dc.get(ip.delivery_point_id)
            if dc_id is None and ip.delivery_point is not None and ip.delivery_point.location is not None:
                if all_dcs is None:
                    all_dcs = await task_service._load_all_active_dcs()
                try:
                    lat, lon = task_service.distance_service.extract_coordinates(
                        ip.delivery_point.location
                    )
                    nearest = await task_service._find_nearest_dc(lat, lon, dcs=all_dcs)
                    dc_id = nearest.id if nearest else None
                except (ValueError, TypeError):
                    dc_id = None
            result[ip.id] = dc_id
        return result

    async def _ensure_dc_can_scan(
        self,
        dc: DcAccount,
        item_point: DeliveryOrderItemPoint,
    ) -> int:
        if dc.distribution_center_id is None:
            raise ValueError("dc_account_has_no_distribution_center")
        point_dc_id = await self._resolve_point_dc_id(item_point)
        if point_dc_id is None:
            raise ValueError("point_distribution_center_not_found")
        if point_dc_id != dc.distribution_center_id:
            raise ValueError("item_point_belongs_to_another_distribution_center")
        return point_dc_id

    async def _record_event(
        self,
        item_point_id: int,
        phase: ItemPointScanPhase,
        scanned_by_dc_id: uuid.UUID,
        operation_id: uuid.UUID | None,
        payload: dict | None = None,
    ) -> DeliveryOrderItemPointScanEvent:
        event = DeliveryOrderItemPointScanEvent(
            delivery_order_item_point_id=item_point_id,
            phase=phase,
            scanned_by_dc_id=scanned_by_dc_id,
            operation_id=operation_id,
            event_payload=payload,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def _transition(
        self,
        dc: DcAccount,
        qr_token: uuid.UUID,
        target_phase: ItemPointScanPhase,
        operation_id: uuid.UUID | None,
        payload: dict | None = None,
    ) -> DcItemPointScanResult:
        item_point = await self._get_item_point(qr_token)
        if not item_point:
            raise ValueError("item_point_not_found")
        dc_id = await self._ensure_dc_can_scan(dc, item_point)

        op_event = await self._get_event_by_operation(item_point.id, target_phase, operation_id)
        if op_event:
            return DcItemPointScanResult(item_point, op_event, op_event.phase, True, dc_id)

        latest = await self._get_latest_event(item_point.id)
        latest_phase = latest.phase if latest else None

        if target_phase == ItemPointScanPhase.RECEIVED_AT_DC:
            if latest_phase != ItemPointScanPhase.LOADING:
                if latest_phase == ItemPointScanPhase.RECEIVED_AT_DC and latest is not None:
                    return DcItemPointScanResult(item_point, latest, latest.phase, True, dc_id)
                raise ValueError("receive_requires_driver_loading_scan")
            if item_point.status != DeliveryPointStatus.IN_TRANSIT:
                raise ValueError("receive_requires_in_transit_status")
            item_point.status = DeliveryPointStatus.AT_DC
        else:
            required_prev = {
                ItemPointScanPhase.MOVED_TO_SORTING: ItemPointScanPhase.RECEIVED_AT_DC,
                ItemPointScanPhase.SORTED_TO_ZONE: ItemPointScanPhase.MOVED_TO_SORTING,
                ItemPointScanPhase.HANDED_TO_COURIER2: ItemPointScanPhase.SORTED_TO_ZONE,
            }[target_phase]
            if latest_phase == target_phase and latest is not None:
                return DcItemPointScanResult(item_point, latest, latest.phase, True, dc_id)
            if latest_phase != required_prev:
                raise ValueError("invalid_stage_transition")
            if target_phase == ItemPointScanPhase.HANDED_TO_COURIER2:
                item_point.status = DeliveryPointStatus.IN_TRANSIT

        event = await self._record_event(
            item_point_id=item_point.id,
            phase=target_phase,
            scanned_by_dc_id=dc.id,
            operation_id=operation_id,
            payload=payload,
        )
        return DcItemPointScanResult(item_point, event, target_phase, False, dc_id)

    @staticmethod
    def _is_in_receiving_pipeline(stage: ItemPointScanPhase | None) -> bool:
        return stage in {
            ItemPointScanPhase.LOADING,
            ItemPointScanPhase.RECEIVED_AT_DC,
            ItemPointScanPhase.MOVED_TO_SORTING,
            ItemPointScanPhase.SORTED_TO_ZONE,
            ItemPointScanPhase.HANDED_TO_COURIER2,
        }

    async def scan_receive(
        self,
        dc: DcAccount,
        qr_token: uuid.UUID,
        operation_id: uuid.UUID | None,
    ) -> DcItemPointScanResult:
        return await self._transition(
            dc=dc,
            qr_token=qr_token,
            target_phase=ItemPointScanPhase.RECEIVED_AT_DC,
            operation_id=operation_id,
        )

    async def scan_receive_for_order(
        self,
        dc: DcAccount,
        order_id: int,
        qr_token: uuid.UUID,
        operation_id: uuid.UUID | None,
    ) -> DcItemPointScanResult:
        item_point = await self._get_item_point(qr_token)
        if not item_point:
            raise ValueError("item_point_not_found")
        await self._ensure_dc_can_scan(dc, item_point)
        if item_point.order_item.order_id != order_id:
            raise ValueError("item_point_belongs_to_another_order")
        return await self._transition(
            dc=dc,
            qr_token=qr_token,
            target_phase=ItemPointScanPhase.RECEIVED_AT_DC,
            operation_id=operation_id,
        )

    async def scan_move_to_sorting(
        self,
        dc: DcAccount,
        qr_token: uuid.UUID,
        operation_id: uuid.UUID | None,
    ) -> DcItemPointScanResult:
        return await self._transition(
            dc=dc,
            qr_token=qr_token,
            target_phase=ItemPointScanPhase.MOVED_TO_SORTING,
            operation_id=operation_id,
        )

    async def scan_sort_to_zone(
        self,
        dc: DcAccount,
        qr_token: uuid.UUID,
        zone_key: str,
        operation_id: uuid.UUID | None,
    ) -> DcItemPointScanResult:
        return await self._transition(
            dc=dc,
            qr_token=qr_token,
            target_phase=ItemPointScanPhase.SORTED_TO_ZONE,
            operation_id=operation_id,
            payload={"zone_key": zone_key},
        )

    async def scan_handover_to_courier2(
        self,
        dc: DcAccount,
        qr_token: uuid.UUID,
        courier_name: str | None,
        courier_phone: str | None,
        courier_external_id: str | None,
        operation_id: uuid.UUID | None,
    ) -> DcItemPointScanResult:
        return await self._transition(
            dc=dc,
            qr_token=qr_token,
            target_phase=ItemPointScanPhase.HANDED_TO_COURIER2,
            operation_id=operation_id,
            payload={
                "courier_name": courier_name,
                "courier_phone": courier_phone,
                "courier_external_id": courier_external_id,
            },
        )

    async def get_latest_stage(self, item_point_id: int) -> ItemPointScanPhase | None:
        latest = await self._get_latest_event(item_point_id)
        return latest.phase if latest else None

    async def list_item_points(
        self,
        dc: DcAccount,
        limit: int,
        offset: int,
        order_id: int | None = None,
    ) -> list[tuple[DeliveryOrderItemPoint, int, ItemPointScanPhase | None]]:
        if dc.distribution_center_id is None:
            return []
        query = (
            select(DeliveryOrderItemPoint)
            .join(DeliveryOrderItem, DeliveryOrderItem.id == DeliveryOrderItemPoint.order_item_id)
            .options(
                selectinload(DeliveryOrderItemPoint.order_item),
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(DeliveryOrderItem.order),
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                    DeliveryOrderItem.producer_sku
                ),
                selectinload(DeliveryOrderItemPoint.delivery_point),
            )
            .order_by(DeliveryOrderItemPoint.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if order_id is not None:
            query = query.where(DeliveryOrderItem.order_id == order_id)
        result = await self.db.execute(query)
        rows = result.scalars().unique().all()

        if not rows:
            return []

        item_point_ids = [item_point.id for item_point in rows]
        latest_stage_map: dict[int, ItemPointScanPhase | None] = {}

        latest_event_subquery = (
            select(
                DeliveryOrderItemPointScanEvent.delivery_order_item_point_id.label(
                    "item_point_id"
                ),
                DeliveryOrderItemPointScanEvent.phase.label("phase"),
                func.row_number()
                .over(
                    partition_by=DeliveryOrderItemPointScanEvent.delivery_order_item_point_id,
                    order_by=(
                        DeliveryOrderItemPointScanEvent.scanned_at.desc(),
                        DeliveryOrderItemPointScanEvent.id.desc(),
                    ),
                )
                .label("rn"),
            )
            .where(
                DeliveryOrderItemPointScanEvent.delivery_order_item_point_id.in_(item_point_ids)
            )
            .subquery()
        )
        latest_result = await self.db.execute(
            select(
                latest_event_subquery.c.item_point_id,
                latest_event_subquery.c.phase,
            ).where(latest_event_subquery.c.rn == 1)
        )
        for item_point_id, phase in latest_result.all():
            latest_stage_map[item_point_id] = phase

        delivery_point_ids = list(
            {
                item_point.delivery_point.id
                for item_point in rows
                if item_point.delivery_point is not None
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
            for sector_id, dc_id in sector_dc_rows.all():
                sector_dc_map.setdefault(sector_id, dc_id)

        active_dcs_result = await self.db.execute(
            select(DistributionCenter).where(
                DistributionCenter.is_active == True  # noqa: E712
            )
        )
        active_dcs = active_dcs_result.scalars().all()
        task_service = DeliveryTaskService(self.db)

        nearest_dc_by_point_id: dict[int, int | None] = {}
        dc_by_delivery_point_id: dict[int, int | None] = {}
        out: list[tuple[DeliveryOrderItemPoint, int, ItemPointScanPhase | None]] = []
        for item_point in rows:
            if item_point.delivery_point is None:
                continue

            delivery_point_id = item_point.delivery_point.id
            if delivery_point_id not in dc_by_delivery_point_id:
                sector_id = point_sector_map.get(delivery_point_id)
                dc_id = sector_dc_map.get(sector_id) if sector_id is not None else None
                if dc_id is None:
                    if delivery_point_id not in nearest_dc_by_point_id:
                        lat, lon = task_service.distance_service.extract_coordinates(
                            item_point.delivery_point.location
                        )
                        nearest_id = None
                        best_dist = float("inf")
                        for active_dc in active_dcs:
                            dc_lat, dc_lon = task_service.distance_service.extract_coordinates(
                                active_dc.location
                            )
                            dist = task_service.distance_service.haversine_distance(
                                lat, lon, dc_lat, dc_lon
                            )
                            if dist < best_dist:
                                best_dist = dist
                                nearest_id = active_dc.id
                        nearest_dc_by_point_id[delivery_point_id] = nearest_id
                    dc_id = nearest_dc_by_point_id[delivery_point_id]
                dc_by_delivery_point_id[delivery_point_id] = dc_id
            dc_id = dc_by_delivery_point_id[delivery_point_id]
            if dc_id != dc.distribution_center_id:
                continue
            out.append((item_point, dc_id, latest_stage_map.get(item_point.id)))
        return out

    async def get_receiving_progress(
        self,
        dc: DcAccount,
        order_id: int,
    ) -> tuple[int, int]:
        rows = await self.list_item_points(
            dc=dc,
            limit=5000,
            offset=0,
            order_id=order_id,
        )
        expected_count = 0
        received_count = 0
        for _item_point, _dc_id, latest_stage in rows:
            if not self._is_in_receiving_pipeline(latest_stage):
                continue
            expected_count += 1
            if latest_stage != ItemPointScanPhase.LOADING:
                received_count += 1
        return expected_count, received_count

    async def list_receiving_orders(
        self,
        dc: DcAccount,
    ) -> list[dict]:
        rows = await self.list_item_points(
            dc=dc,
            limit=5000,
            offset=0,
        )
        grouped: dict[int, dict] = {}
        for item_point, _dc_id, latest_stage in rows:
            if not self._is_in_receiving_pipeline(latest_stage):
                continue
            order_id = item_point.order_item.order_id
            order_number = getattr(item_point.order_item.order, "order_number", None)
            bucket = grouped.setdefault(
                order_id,
                {
                    "order_id": order_id,
                    "order_number": order_number,
                    "expected_count": 0,
                    "received_count": 0,
                    "updated_at": None,
                },
            )
            bucket["expected_count"] += 1
            if latest_stage != ItemPointScanPhase.LOADING:
                bucket["received_count"] += 1
            current_updated = bucket["updated_at"]
            if current_updated is None or item_point.updated_at > current_updated:
                bucket["updated_at"] = item_point.updated_at

        out: list[dict] = []
        for row in grouped.values():
            remaining_count = row["expected_count"] - row["received_count"]
            if remaining_count <= 0:
                continue
            out.append(
                {
                    **row,
                    "remaining_count": remaining_count,
                }
            )
        out.sort(
            key=lambda x: x["updated_at"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        return out

    async def get_operation_events(
        self,
        dc: DcAccount,
        operation_id: uuid.UUID,
    ) -> list[tuple[DeliveryOrderItemPointScanEvent, DeliveryOrderItemPoint]]:
        if dc.distribution_center_id is None:
            return []
        result = await self.db.execute(
            select(DeliveryOrderItemPointScanEvent, DeliveryOrderItemPoint)
            .join(
                DeliveryOrderItemPoint,
                DeliveryOrderItemPointScanEvent.delivery_order_item_point_id == DeliveryOrderItemPoint.id,
            )
            .options(
                selectinload(DeliveryOrderItemPoint.delivery_point),
                selectinload(DeliveryOrderItemPoint.order_item),
            )
            .where(DeliveryOrderItemPointScanEvent.operation_id == operation_id)
            .order_by(
                DeliveryOrderItemPointScanEvent.scanned_at.asc(),
                DeliveryOrderItemPointScanEvent.id.asc(),
            )
        )
        rows = result.all()
        filtered: list[tuple[DeliveryOrderItemPointScanEvent, DeliveryOrderItemPoint]] = []
        for event, item_point in rows:
            dc_id = await self._resolve_point_dc_id(item_point)
            if dc_id == dc.distribution_center_id:
                filtered.append((event, item_point))
        return filtered

    async def list_history_events(
        self,
        dc: DcAccount,
        phase: ItemPointScanPhase,
        limit: int = 500,
        offset: int = 0,
    ) -> list[tuple[DeliveryOrderItemPointScanEvent, DeliveryOrderItemPoint]]:
        if dc.distribution_center_id is None:
            return []
        result = await self.db.execute(
            select(DeliveryOrderItemPointScanEvent, DeliveryOrderItemPoint)
            .join(
                DeliveryOrderItemPoint,
                DeliveryOrderItemPointScanEvent.delivery_order_item_point_id == DeliveryOrderItemPoint.id,
            )
            .options(
                selectinload(DeliveryOrderItemPointScanEvent.scanned_by_dc),
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(DeliveryOrderItem.order),
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                    DeliveryOrderItem.producer_sku
                ),
                selectinload(DeliveryOrderItemPoint.delivery_point),
            )
            .where(DeliveryOrderItemPointScanEvent.phase == phase)
            .order_by(
                DeliveryOrderItemPointScanEvent.scanned_at.desc(),
                DeliveryOrderItemPointScanEvent.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = result.all()
        item_points = [ip for _, ip in rows]
        dc_map = await self._batch_resolve_point_dc_ids(item_points)
        filtered: list[tuple[DeliveryOrderItemPointScanEvent, DeliveryOrderItemPoint]] = []
        for event, item_point in rows:
            if dc_map.get(item_point.id) == dc.distribution_center_id:
                filtered.append((event, item_point))
        return filtered

    async def list_delivered_events(
        self,
        dc: DcAccount,
        limit: int = 500,
        offset: int = 0,
    ) -> list[tuple[CourierDeliveryTask, DeliveryOrderItemPoint]]:
        """List courier deliveries to final points for items that passed through this DC."""
        if dc.distribution_center_id is None:
            return []
        result = await self.db.execute(
            select(CourierDeliveryTask, DeliveryOrderItemPoint)
            .join(
                DeliveryOrderItemPoint,
                CourierDeliveryTask.item_point_id == DeliveryOrderItemPoint.id,
            )
            .options(
                selectinload(CourierDeliveryTask.courier),
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                    DeliveryOrderItem.producer_sku
                ),
                selectinload(DeliveryOrderItemPoint.order_item).selectinload(DeliveryOrderItem.order),
                selectinload(DeliveryOrderItemPoint.delivery_point),
            )
            .where(CourierDeliveryTask.delivered_at.isnot(None))
            .order_by(
                CourierDeliveryTask.delivered_at.desc(),
                CourierDeliveryTask.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        rows = result.all()
        item_points = [ip for _, ip in rows]
        dc_map = await self._batch_resolve_point_dc_ids(item_points)
        filtered: list[tuple[CourierDeliveryTask, DeliveryOrderItemPoint]] = []
        for task, item_point in rows:
            if dc_map.get(item_point.id) == dc.distribution_center_id:
                filtered.append((task, item_point))
        return filtered
