"""Service for driver/courier location: report, get, and broadcast via SSE."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import CourierLastLocation, DriverLastLocation
from app.db.models.delivery_task import DriverDeliveryTask

from app.services.driver_location_sse import driver_location_sse


async def _resolve_order_id(db: AsyncSession, actor_id: UUID, task_id: int) -> tuple[int, bool] | None:
    """Resolve order_id for a location report. Returns (order_id, is_courier) or None."""
    # Try DriverDeliveryTask first
    result = await db.execute(
        select(DriverDeliveryTask.order_id).where(
            DriverDeliveryTask.id == task_id,
            DriverDeliveryTask.driver_id == actor_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is not None:
        return (row, False)

    # Fallback: CourierDeliveryTask → item_point → order_item → order
    from app.db.models.courier_delivery_task import CourierDeliveryTask
    from app.db.models.delivery_order import DeliveryOrderItem, DeliveryOrderItemPoint

    courier_result = await db.execute(
        select(DeliveryOrderItem.order_id)
        .join(DeliveryOrderItemPoint, DeliveryOrderItemPoint.order_item_id == DeliveryOrderItem.id)
        .join(CourierDeliveryTask, CourierDeliveryTask.item_point_id == DeliveryOrderItemPoint.id)
        .where(
            CourierDeliveryTask.id == task_id,
            CourierDeliveryTask.courier_id == actor_id,
        )
    )
    row = courier_result.scalar_one_or_none()
    if row is not None:
        return (row, True)
    return None


async def report_location(
    db: AsyncSession,
    driver_id: UUID,
    task_id: int,
    lat: float,
    lon: float,
    accuracy: float | None = None,
    device_info: str | None = None,
) -> int | None:
    """
    Report location for a task. Works for both drivers and couriers.
    Returns delivery_order_id if success, else None.
    Drivers → driver_last_location; couriers → courier_last_location.
    """
    resolved = await _resolve_order_id(db, driver_id, task_id)
    if resolved is None:
        return None
    order_id, is_courier = resolved
    reported = datetime.now(timezone.utc)

    if is_courier:
        stmt = pg_insert(CourierLastLocation).values(
            courier_id=driver_id,
            delivery_order_id=order_id,
            lat=lat,
            lon=lon,
            accuracy=accuracy,
            device_info=device_info,
            reported_at=reported,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["courier_id", "delivery_order_id"],
            set_={
                "lat": stmt.excluded.lat,
                "lon": stmt.excluded.lon,
                "accuracy": stmt.excluded.accuracy,
                "device_info": stmt.excluded.device_info,
                "reported_at": stmt.excluded.reported_at,
                "updated_at": reported,
            },
        )
    else:
        stmt = pg_insert(DriverLastLocation).values(
            driver_id=driver_id,
            delivery_order_id=order_id,
            lat=lat,
            lon=lon,
            accuracy=accuracy,
            device_info=device_info,
            reported_at=reported,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["driver_id", "delivery_order_id"],
            set_={
                "lat": stmt.excluded.lat,
                "lon": stmt.excluded.lon,
                "accuracy": stmt.excluded.accuracy,
                "device_info": stmt.excluded.device_info,
                "reported_at": stmt.excluded.reported_at,
                "updated_at": reported,
            },
        )
    await db.execute(stmt)
    await db.flush()

    driver_location_sse.broadcast_to_order(
        order_id,
        {
            "lat": lat,
            "lon": lon,
            "accuracy": accuracy,
            "reported_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    return order_id


def _is_stale(reported_at: datetime) -> bool:
    threshold = settings.DRIVER_LOCATION_STALE_AFTER_SEC
    age = (datetime.now(timezone.utc) - reported_at.replace(tzinfo=timezone.utc)).total_seconds()
    return age > threshold


async def get_location_for_order(
    db: AsyncSession,
    order_id: int,
) -> dict | None:
    """
    Get last driver or courier location for an order. Returns the most recent.
    """
    driver_result = await db.execute(
        select(DriverLastLocation)
        .where(DriverLastLocation.delivery_order_id == order_id)
        .order_by(DriverLastLocation.reported_at.desc())
        .limit(1)
    )
    driver_loc = driver_result.scalar_one_or_none()

    courier_result = await db.execute(
        select(CourierLastLocation)
        .where(CourierLastLocation.delivery_order_id == order_id)
        .order_by(CourierLastLocation.reported_at.desc())
        .limit(1)
    )
    courier_loc = courier_result.scalar_one_or_none()

    loc = None
    if driver_loc and courier_loc:
        loc = driver_loc if driver_loc.reported_at >= courier_loc.reported_at else courier_loc
    elif driver_loc:
        loc = driver_loc
    elif courier_loc:
        loc = courier_loc

    if not loc:
        return None

    return {
        "lat": loc.lat,
        "lon": loc.lon,
        "accuracy": loc.accuracy,
        "reported_at": loc.reported_at,
        "is_stale": _is_stale(loc.reported_at),
    }
