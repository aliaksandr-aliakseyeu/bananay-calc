"""
PostgreSQL LISTEN for daily check-in moderation events.
All instances listen on the same channel; each pushes to its own SSE connections if it has the driver.
"""
import asyncio
import json
import logging
from typing import Any

import asyncpg

from app.core.config import settings
from app.services.sse_manager import driver_sse_manager

logger = logging.getLogger(__name__)

CHANNEL = "daily_checkin_events"


def _get_listen_dsn() -> str:
    """DSN for asyncpg (postgresql:// without +asyncpg)."""
    return (
        f"postgresql://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}"
        f"@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"
    )


def _on_notify(connection: asyncpg.Connection, pid: int, channel: str, payload: str) -> None:
    """Called when NOTIFY is received. Push to local SSE if we have this driver."""
    if channel != CHANNEL or not payload:
        return
    try:
        data: dict[str, Any] = json.loads(payload)
        driver_id = data.get("driver_id")
        if not driver_id:
            return
        event = data.get("event", "daily_checkin_status")
        # Payload for SSE: checkin_id, status, reject_reason (no driver_id/event in data)
        payload = {k: v for k, v in data.items() if k not in ("driver_id", "event")}
        driver_sse_manager.send_to_driver(driver_id, event, payload)
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning("daily_checkin_listener: invalid payload %s: %s", payload[:200], e)


async def run_daily_checkin_listener() -> None:
    """
    Connect to PostgreSQL, LISTEN on channel, and dispatch NOTIFY payloads to local SSE manager.
    Runs until cancelled. Reconnects on connection loss.
    """
    dsn = _get_listen_dsn()
    conn = None
    while True:
        try:
            conn = await asyncpg.connect(dsn)
            await conn.add_listener(CHANNEL, _on_notify)
            logger.info("daily_checkin_listener: LISTEN on %s", CHANNEL)
            # Keep connection alive; add_listener keeps it active for notifications
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("daily_checkin_listener: cancelled")
            if conn and not conn.is_closed():
                await conn.close()
            raise
        except Exception as e:
            logger.exception("daily_checkin_listener: connection error, reconnecting in 5s: %s", e)
            if conn and not conn.is_closed():
                await conn.close()
            conn = None
            await asyncio.sleep(5)
