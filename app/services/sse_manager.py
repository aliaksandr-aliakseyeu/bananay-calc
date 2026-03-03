"""In-memory SSE manager: broadcast events to driver connections by driver_id."""
import asyncio
from typing import Any
from uuid import UUID


class DriverSSEManager:
    """Holds one asyncio.Queue per driver SSE connection. Push events to a driver by id."""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, driver_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Register a new SSE connection for this driver. Returns a queue to consume."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        if driver_id not in self._queues:
            self._queues[driver_id] = []
        self._queues[driver_id].append(q)
        return q

    def unsubscribe(self, driver_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove this connection's queue."""
        if driver_id not in self._queues:
            return
        try:
            self._queues[driver_id].remove(queue)
        except ValueError:
            pass
        if not self._queues[driver_id]:
            del self._queues[driver_id]

    def send_to_driver(self, driver_id: str, event: str, data: dict[str, Any]) -> None:
        """Push one event to all SSE connections for this driver. Sync so LISTEN callback can call it."""
        driver_id_str = str(driver_id) if isinstance(driver_id, UUID) else driver_id
        if driver_id_str not in self._queues:
            return
        payload = {"event": event, **data}
        for q in list(self._queues[driver_id_str]):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass


driver_sse_manager = DriverSSEManager()
