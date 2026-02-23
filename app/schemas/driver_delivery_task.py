"""Pydantic schemas for driver delivery tasks."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DeliveryTaskItem(BaseModel):
    """SKU + quantity to deliver to a DC."""

    sku_name: str = Field(..., description="SKU name")
    sku_code: str = Field(..., description="SKU code")
    quantity: int = Field(..., gt=0, description="Quantity")


class DCDeliveryResponse(BaseModel):
    """What to deliver to one distribution center."""

    dc_id: int = Field(..., description="Distribution center ID")
    dc_name: str = Field(..., description="DC name")
    dc_address: str | None = Field(None, description="DC address")
    dc_lat: float = Field(..., description="DC latitude")
    dc_lon: float = Field(..., description="DC longitude")
    items: list[DeliveryTaskItem] = Field(
        default_factory=list,
        description="Items to unload at this DC",
    )
    status: str | None = Field(
        None,
        description="Per-DC status for my tasks: pending, in_transit, delivered",
    )
    delivered_at: datetime | None = Field(
        None,
        description="When this DC was unloaded (for my tasks)",
    )
    unload_photo_media_id: UUID | None = Field(
        None,
        description="Media ID of optional unload photo (use /driver/media/{id} to view)",
    )


class DriverDeliveryTaskResponse(BaseModel):
    """One driver task: pick up at warehouse, deliver to several DCs."""

    task_id: int = Field(..., description="Task ID (use to take the task)")
    order_id: int = Field(..., description="Order ID")
    order_number: str = Field(..., description="Order number")
    warehouse_lat: float = Field(..., description="Warehouse pickup latitude")
    warehouse_lon: float = Field(..., description="Warehouse pickup longitude")
    deliveries: list[DCDeliveryResponse] = Field(
        default_factory=list,
        description="List of DCs and items to deliver",
    )
    status: str | None = Field(
        None,
        description="Task status for my tasks: assigned, loading, in_transit, etc.",
    )
    loading_photo_media_id: UUID | None = Field(
        None,
        description="Media ID of optional loading photo (use /driver/media/{id} to view)",
    )


class CompletedTaskResponse(BaseModel):
    """One completed delivery task for driver history."""

    task_id: int = Field(..., description="Task ID")
    order_id: int = Field(..., description="Order ID")
    order_number: str = Field(..., description="Order number")
    delivered_at: datetime = Field(..., description="When the task was completed")
