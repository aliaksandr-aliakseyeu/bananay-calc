"""SSE manager for driver location: broadcast to producers watching an order."""
import asyncio
from typing import Any


class DriverLocationSSEManager:
    """Holds one asyncio.Queue per order_id. Broadcast location when driver reports."""

    def __init__(self) -> None:
        self._queues: dict[int, list[asyncio.Queue[dict[str, Any]]]] = {}

    def subscribe(self, order_id: int) -> asyncio.Queue[dict[str, Any]]:
        """Register a new SSE connection for this order. Returns a queue to consume."""
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        if order_id not in self._queues:
            self._queues[order_id] = []
        self._queues[order_id].append(q)
        return q

    def unsubscribe(self, order_id: int, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove this connection's queue."""
        if order_id not in self._queues:
            return
        try:
            self._queues[order_id].remove(queue)
        except ValueError:
            pass
        if not self._queues[order_id]:
            del self._queues[order_id]

    def broadcast_to_order(self, order_id: int, data: dict[str, Any]) -> None:
        """Push location update to all SSE connections watching this order."""
        if order_id not in self._queues:
            return
        payload = {"event": "location", **data}
        for q in list(self._queues[order_id]):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass


driver_location_sse = DriverLocationSSEManager()
