"""Pydantic schemas for Delivery Templates."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class DeliveryTemplatePointBase(BaseModel):
    """Base schema for delivery template point."""
    delivery_point_id: int = Field(..., description="ID of the delivery point")
    quantity: int = Field(..., gt=0, description="Quantity for this point")
    notes: str | None = Field(None, max_length=1000, description="Notes for this point")


class DeliveryTemplatePointCreate(DeliveryTemplatePointBase):
    """Schema for creating a template point."""
    pass


class DeliveryTemplatePointUpdate(BaseModel):
    """Schema for updating a template point."""
    quantity: int | None = Field(None, gt=0, description="Quantity for this point")
    notes: str | None = Field(None, max_length=1000, description="Notes for this point")


class DeliveryTemplatePointSync(BaseModel):
    """Schema for syncing a point (create or update)."""
    delivery_point_id: int = Field(..., description="ID of the delivery point")
    quantity: int = Field(..., gt=0, description="Quantity for this point")
    notes: str | None = Field(None, max_length=1000, description="Notes for this point")


class DeliveryTemplateSyncPointsRequest(BaseModel):
    """Schema for batch syncing template points."""
    points: list[DeliveryTemplatePointSync] = Field(..., description="Points to sync")


class DeliveryTemplatePointResponse(DeliveryTemplatePointBase):
    """Schema for template point response."""
    id: int
    template_id: int
    created_at: datetime
    delivery_point_name: str | None = Field(None, description="Name of the delivery point")
    delivery_point_address: str | None = Field(None, description="Address of the delivery point")

    model_config = ConfigDict(from_attributes=True)


class DeliveryTemplateBase(BaseModel):
    """Base schema for delivery template."""
    name: str = Field(..., min_length=3, max_length=200, description="Template name")
    description: str | None = Field(None, max_length=1000, description="Template description")
    producer_sku_id: int = Field(..., description="Producer SKU ID")
    region_id: int = Field(..., description="Region ID")
    warehouse_lat: float = Field(..., ge=-90, le=90, description="Warehouse latitude")
    warehouse_lon: float = Field(..., ge=-180, le=180, description="Warehouse longitude")


class DeliveryTemplateCreate(DeliveryTemplateBase):
    """
    Schema for creating a delivery template.

    Points can be added separately via the add-point endpoint.
    """
    points: list[DeliveryTemplatePointCreate] = Field(
        default_factory=list,
        description="Initial delivery points (optional, can be added later)"
    )


class DeliveryTemplateUpdate(BaseModel):
    """Schema for updating a delivery template."""
    name: str | None = Field(None, min_length=3, max_length=200, description="Template name")
    description: str | None = Field(None, max_length=1000, description="Template description")
    warehouse_lat: float | None = Field(None, ge=-90, le=90, description="Warehouse latitude")
    warehouse_lon: float | None = Field(None, ge=-180, le=180, description="Warehouse longitude")
    is_active: bool | None = Field(None, description="Active status")


class DeliveryTemplateResponse(DeliveryTemplateBase):
    """Schema for delivery template response (list view)."""
    id: int
    producer_id: int
    total_quantity: int
    estimated_cost: Decimal | None = None
    cost_per_unit: Decimal | None = None
    last_calculated_at: datetime | None = None
    usage_count: int
    last_used_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer('estimated_cost', 'cost_per_unit')
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Convert Decimal to float for JSON serialization."""
        return float(value) if value is not None else None

    model_config = ConfigDict(from_attributes=True)


class DeliveryTemplateDetailResponse(DeliveryTemplateResponse):
    """Schema for detailed template response with points."""
    points: list[DeliveryTemplatePointResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DeliveryTemplateCalculateRequest(BaseModel):
    """Schema for requesting template cost calculation."""
    pass


class DeliveryTemplateCalculateResponse(BaseModel):
    """Schema for template cost calculation response."""
    total_quantity: int = Field(..., description="Total quantity across all points")
    estimated_cost: Decimal = Field(..., description="Estimated delivery cost")
    cost_per_unit: Decimal = Field(..., description="Cost per SKU unit")
    calculation_details: dict = Field(..., description="Detailed calculation breakdown")

    @field_serializer('estimated_cost', 'cost_per_unit')
    def serialize_decimal(self, value: Decimal | None) -> float | None:
        """Convert Decimal to float for JSON serialization."""
        return float(value) if value is not None else None


class DeliveryTemplateUsageHistoryResponse(BaseModel):
    """Schema for template usage history."""
    template_id: int
    template_name: str
    usage_count: int
    last_used_at: datetime | None
    orders: list[dict] = Field(
        default_factory=list,
        description="List of orders that used this template"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "template_id": 1,
                "template_name": "Йогурты по основным точкам",
                "usage_count": 15,
                "last_used_at": "2026-02-05T10:00:00Z",
                "orders": [
                    {
                        "order_id": 42,
                        "order_number": "ORD-2026-0042",
                        "created_at": "2026-02-05T10:00:00Z",
                        "status": "completed"
                    }
                ]
            }
        }
    )
