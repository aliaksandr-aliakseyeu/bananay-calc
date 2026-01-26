"""Pydantic schemas for Delivery Orders."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.delivery_order import (DeliveryPointStatus, OrderPriority,
                                          OrderStatus)


class DeliveryOrderPointBase(BaseModel):
    """Base schema for delivery order point."""
    delivery_point_id: int = Field(..., description="ID of the delivery point")
    quantity: int = Field(..., gt=0, description="Number of SKU units for this point")
    delivery_notes: Optional[str] = Field(None, max_length=1000, description="Notes about delivery")


class DeliveryOrderPointCreate(DeliveryOrderPointBase):
    """Schema for creating a delivery order point."""
    pass


class DeliveryOrderPointUpdate(BaseModel):
    """Schema for updating a delivery order point."""
    status: Optional[DeliveryPointStatus] = Field(None, description="Delivery status")
    quantity: Optional[int] = Field(None, gt=0, description="Number of SKU units")
    photo_url: Optional[str] = Field(None, max_length=500, description="Photo proof URL")
    delivery_notes: Optional[str] = Field(None, max_length=1000, description="Delivery notes")


class DeliveryOrderPointResponse(DeliveryOrderPointBase):
    """Schema for delivery order point response."""
    id: int
    order_id: int
    status: DeliveryPointStatus
    photo_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    delivered_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DeliveryOrderBase(BaseModel):
    """Base schema for delivery order."""
    producer_sku_id: int = Field(..., description="ID of the producer SKU")
    producer_notes: Optional[str] = Field(None, max_length=1000, description="Producer notes")


class DeliveryOrderCreate(DeliveryOrderBase):
    """
    Schema for creating a delivery order.
    Cost and quantity are calculated on frontend and passed here.
    """
    points: list[DeliveryOrderPointCreate] = Field(
        ...,
        min_length=1,
        description="Delivery points for this order (list of tuples: delivery_point_id, quantity)"
    )
    total_cost: Decimal = Field(..., description="Total delivery cost (calculated on frontend)")
    cost_per_unit: Decimal = Field(..., description="Cost per SKU unit (calculated on frontend)")
    quantity: int = Field(..., gt=0, description="Total number of SKU units")
    status: OrderStatus = Field(default=OrderStatus.DRAFT, description="Order status (draft or pending)")
    priority: OrderPriority = Field(default=OrderPriority.NORMAL, description="Order priority")
    expected_pickup_date: Optional[datetime] = Field(None, description="When producer plans to hand over")
    delivery_deadline: Optional[datetime] = Field(None, description="Delivery deadline")


class DeliveryOrderUpdate(BaseModel):
    """Schema for updating a delivery order."""
    status: Optional[OrderStatus] = Field(None, description="Order status")
    producer_notes: Optional[str] = Field(None, max_length=1000, description="Producer notes")
    admin_notes: Optional[str] = Field(None, max_length=1000, description="Admin notes")


class DeliveryOrderStatusUpdate(BaseModel):
    """Schema for updating order status with notes."""
    status: OrderStatus = Field(..., description="New order status")
    notes: Optional[str] = Field(None, max_length=1000, description="Status change notes")


class DeliveryOrderResponse(DeliveryOrderBase):
    """Schema for delivery order response."""
    id: int
    order_number: str
    producer_id: int
    quantity: int
    status: OrderStatus
    priority: OrderPriority
    total_cost: Optional[Decimal] = None
    cost_per_unit: Optional[Decimal] = None
    admin_notes: Optional[str] = None
    expected_pickup_date: Optional[datetime] = None
    actual_pickup_date: Optional[datetime] = None
    delivery_deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sent_to_dc_at: Optional[datetime] = None
    arrived_at_dc_at: Optional[datetime] = None
    driver_assigned_at: Optional[datetime] = None
    delivery_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class DeliveryOrderDetailResponse(DeliveryOrderResponse):
    """Detailed schema for delivery order with points and history."""
    points: list[DeliveryOrderPointResponse] = Field(default_factory=list, alias="delivery_points", serialization_alias="points")

    model_config = {"from_attributes": True, "populate_by_name": True}


class DeliveryOrderStatusHistoryResponse(BaseModel):
    """Schema for order status history."""
    id: int
    order_id: int
    changed_by_user_id: Optional[int] = None
    old_status: Optional[OrderStatus] = None
    new_status: OrderStatus
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryOrderListResponse(BaseModel):
    """Schema for paginated list of delivery orders."""
    items: list[DeliveryOrderResponse]
    total: int
    page: int
    page_size: int
    pages: int


class DeliveryPointQuantityItem(BaseModel):
    """Delivery point with quantity for order calculation."""
    point_id: int = Field(..., gt=0, description="Delivery point ID")
    quantity: int = Field(..., gt=0, description="Quantity for this delivery point")


class DeliveryOrderCalculationRequest(BaseModel):
    """Schema for requesting delivery cost calculation."""
    producer_sku_id: int = Field(..., description="ID of the producer SKU")
    point_quantities: list[DeliveryPointQuantityItem] = Field(
        ..., min_length=1, description="List of delivery points with quantities"
    )
    warehouse_lat: float = Field(..., ge=-90, le=90, description="Warehouse latitude")
    warehouse_lon: float = Field(..., ge=-180, le=180, description="Warehouse longitude")
    region_id: int = Field(..., description="Region ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "producer_sku_id": 123,
                "point_quantities": [
                    {"point_id": 4510, "quantity": 10},
                    {"point_id": 328, "quantity": 5},
                    {"point_id": 1299, "quantity": 15},
                    {"point_id": 4877, "quantity": 8},
                    {"point_id": 2590, "quantity": 12}
                ],
                "warehouse_lat": 43.653366116451195,
                "warehouse_lon": 39.64989059534503,
                "region_id": 1
            }
        }
    )


class DeliveryOrderCalculationResponse(BaseModel):
    """Schema for delivery cost calculation response."""
    total_cost: Decimal = Field(..., description="Total delivery cost")
    cost_per_unit: Decimal = Field(..., description="Cost per SKU unit")
    calculation_details: dict = Field(..., description="Detailed calculation breakdown")
