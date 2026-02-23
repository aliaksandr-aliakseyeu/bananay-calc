"""Pydantic schemas for Delivery Orders (new structure with templates)."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.delivery_order import (DeliveryPointStatus, OrderPriority,
                                          OrderStatus)


class DeliveryCenterInfo(BaseModel):
    """Distribution center where goods were delivered (for producer when status is at_dc)."""

    id: int = Field(..., description="DC id")
    name: str = Field(..., description="DC name")
    address: str | None = Field(None, description="DC address")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")


class AssignedDriverInfo(BaseModel):
    """Driver assigned to the delivery order (for producer view)."""

    id: str = Field(..., description="Driver UUID")
    full_name: str | None = Field(None, description="Driver full name")
    phone: str | None = Field(None, description="Full phone number for order owner")
    phone_masked: str = Field(..., description="Masked phone, e.g. +7 *** *** 12 34")
    city: str | None = Field(None, description="Driver city")


class DeliveryOrderItemPointBase(BaseModel):
    """Base schema for delivery order item point."""
    delivery_point_id: int = Field(..., description="ID of the delivery point")
    quantity: int = Field(..., gt=0, description="Quantity for this point")
    delivery_notes: str | None = Field(None, max_length=1000, description="Delivery notes")


class DeliveryOrderItemPointUpdate(BaseModel):
    """Schema for updating an order item point."""
    status: DeliveryPointStatus | None = Field(None, description="Delivery status")
    quantity: int | None = Field(None, gt=0, description="Quantity")
    photo_url: str | None = Field(None, max_length=500, description="Photo proof URL")
    delivery_notes: str | None = Field(None, max_length=1000, description="Delivery notes")


class DeliveryOrderItemPointResponse(DeliveryOrderItemPointBase):
    """Schema for order item point response."""
    id: int
    order_item_id: int
    status: DeliveryPointStatus
    photo_url: str | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # When status is at_dc: media ID of driver's unload photo at the DC (producer can view via GET .../dc-unload-photo/{id})
    dc_unload_photo_media_id: UUID | None = None
    lat: float | None = Field(None, description="Point latitude (from delivery_point)")
    lon: float | None = Field(None, description="Point longitude (from delivery_point)")
    delivery_point_name: str | None = Field(None, description="Name of the delivery point (from delivery_point)")
    delivery_point_address: str | None = Field(None, description="Address of the delivery point (from delivery_point)")

    model_config = ConfigDict(from_attributes=True)


class DeliveryOrderItemResponse(BaseModel):
    """Schema for order item response."""
    id: int
    order_id: int
    template_id: int | None
    template_name: str
    producer_sku_id: int
    sku_snapshot: dict | None
    region_id: int
    warehouse_lat: float
    warehouse_lon: float
    quantity: int
    item_cost: Decimal | None
    cost_per_unit: Decimal | None
    created_at: datetime
    points: list[DeliveryOrderItemPointResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DeliveryOrderBase(BaseModel):
    """Base schema for delivery order."""
    producer_notes: str | None = Field(None, max_length=1000, description="Producer notes")
    priority: OrderPriority = Field(default=OrderPriority.NORMAL, description="Order priority")
    expected_pickup_date: datetime | None = Field(None, description="Expected pickup date")
    delivery_deadline: datetime | None = Field(None, description="Delivery deadline")


class DeliveryOrderCreateFromTemplates(DeliveryOrderBase):
    """
    Schema for creating a delivery order from templates.

    This is the main way to create orders - by selecting existing templates.
    """
    template_ids: list[int] = Field(
        ...,
        min_length=1,
        description="List of template IDs to include in this order"
    )
    status: OrderStatus = Field(
        default=OrderStatus.PENDING,
        description="Initial order status (draft or pending)"
    )


class DeliveryOrderUpdate(BaseModel):
    """Schema for updating a delivery order."""
    status: OrderStatus | None = Field(None, description="Order status")
    producer_notes: str | None = Field(None, max_length=1000, description="Producer notes")
    admin_notes: str | None = Field(None, max_length=1000, description="Admin notes")
    priority: OrderPriority | None = Field(None, description="Order priority")
    expected_pickup_date: datetime | None = Field(None, description="Expected pickup date")
    delivery_deadline: datetime | None = Field(None, description="Delivery deadline")


class DeliveryOrderStatusUpdate(BaseModel):
    """Schema for updating order status with notes."""
    status: OrderStatus = Field(..., description="New order status")
    notes: str | None = Field(None, max_length=1000, description="Status change notes")


class DeliveryOrderResponse(BaseModel):
    """Schema for delivery order response (list view)."""
    id: int
    order_number: str
    producer_id: int
    total_quantity: int
    total_cost: Decimal | None
    status: OrderStatus
    priority: OrderPriority
    producer_notes: str | None = None
    admin_notes: str | None = None
    expected_pickup_date: datetime | None = None
    actual_pickup_date: datetime | None = None
    delivery_deadline: datetime | None = None
    created_at: datetime
    updated_at: datetime
    sent_to_dc_at: datetime | None = None
    arrived_at_dc_at: datetime | None = None
    driver_assigned_at: datetime | None = None
    delivery_started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DeliveryOrderDetailResponse(DeliveryOrderResponse):
    """Detailed schema for delivery order with items."""
    items: list[DeliveryOrderItemResponse] = Field(default_factory=list)
    assigned_driver: AssignedDriverInfo | None = Field(
        None,
        description="Driver assigned to this order (when status is driver_assigned or later)",
    )
    delivery_centers: list[DeliveryCenterInfo] | None = Field(
        None,
        description="DCs where goods were delivered (when status is at_dc, for map and modal)",
    )

    model_config = ConfigDict(from_attributes=True)


class DeliveryOrderStatusHistoryResponse(BaseModel):
    """Schema for order status history."""
    id: int
    order_id: int
    changed_by_user_id: int | None = None
    old_status: OrderStatus | None = None
    new_status: OrderStatus
    notes: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeliveryOrderListResponse(BaseModel):
    """Schema for paginated list of delivery orders."""
    items: list[DeliveryOrderResponse]
    total: int
    page: int
    page_size: int
    pages: int
