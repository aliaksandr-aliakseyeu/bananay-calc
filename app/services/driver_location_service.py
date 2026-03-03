"""Service for driver location: report, get, and broadcast via SSE."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import DriverLastLocation
from app.db.models.delivery_task import DriverDeliveryTask

from app.services.driver_location_sse import driver_location_sse


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
    Report driver location for a task. Returns delivery_order_id if success, else None.

    Validates task is assigned to driver, then upserts driver_last_location.
    Broadcasts to SSE subscribers for that order.
    """
    result = await db.execute(
        select(DriverDeliveryTask.order_id).where(
            DriverDeliveryTask.id == task_id,
            DriverDeliveryTask.driver_id == driver_id,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        return None

    order_id = row
    reported = datetime.now(timezone.utc)

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
    Get last driver location for an order. Returns None if no location.
    """
    result = await db.execute(
        select(DriverLastLocation)
        .where(DriverLastLocation.delivery_order_id == order_id)
        .order_by(DriverLastLocation.reported_at.desc())
        .limit(1)
    )
    loc = result.scalar_one_or_none()
    if not loc:
        return None

    return {
        "lat": loc.lat,
        "lon": loc.lon,
        "accuracy": loc.accuracy,
        "reported_at": loc.reported_at,
        "is_stale": _is_stale(loc.reported_at),
    }
