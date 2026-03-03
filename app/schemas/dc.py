"""Schemas for DC auth/profile and QR operations over delivery order item points."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DcProfileUpdate(BaseModel):
    """Update DC account profile."""

    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    distribution_center_id: int | None = Field(None, ge=1)


class DcProfileResponse(BaseModel):
    """Current DC account profile."""

    id: UUID
    phone_e164: str
    status: str
    first_name: str | None
    last_name: str | None
    distribution_center_id: int | None
    distribution_center_name: str | None = None
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DcBoxScanBase(BaseModel):
    """Common scan request body with QR token (one point = one abstract box)."""

    qr_token: UUID
    operation_id: UUID | None = Field(
        None,
        description="Optional client-side idempotency operation ID",
    )


class DcScanReceiveRequest(DcBoxScanBase):
    """Receive producer box at DC."""


class DcScanReceiveForOrderRequest(DcBoxScanBase):
    """Receive producer box at DC for a specific active order."""


class DcScanMoveToSortingRequest(DcBoxScanBase):
    """Move box to sorting area."""


class DcScanSortToZoneRequest(DcBoxScanBase):
    """Sort box into delivery zone."""

    zone_key: str | None = Field(None, max_length=120)


class DcScanHandoverCourier2Request(DcBoxScanBase):
    """Handover box to courier #2."""

    courier_name: str | None = Field(None, min_length=1, max_length=150)
    courier_phone: str | None = Field(None, min_length=5, max_length=25)
    courier_external_id: str | None = Field(None, min_length=1, max_length=120)


class DcBoxScanResponse(BaseModel):
    """Result of DC scan operation."""

    qr_token: UUID
    delivery_order_item_point_id: int
    order_id: int
    current_stage: str
    phase: str
    event_id: int
    operation_id: UUID | None
    is_idempotent: bool = False


class DcBoxItemResponse(BaseModel):
    """Box item in DC list views."""

    qr_token: UUID
    delivery_order_item_point_id: int
    order_id: int
    order_number: str | None = None
    distribution_center_id: int
    current_stage: str
    phase: str
    phase_label: str
    operation_id: UUID | None = None
    delivery_point_name: str | None = None
    sku_name: str | None = None
    quantity: int | None = None
    updated_at: datetime


class DcOperationEventResponse(BaseModel):
    """One DC operation event row."""

    event_id: int
    qr_token: UUID
    phase: str
    stage_after: str
    scanned_by_dc_id: UUID | None
    created_at: datetime
    payload: dict | None = None


class DcOperationResponse(BaseModel):
    """Operation with grouped box events."""

    operation_id: UUID
    events: list[DcOperationEventResponse]


class DcHistoryEventResponse(BaseModel):
    """One DC audit event row for history screens."""

    event_id: int
    scanned_at: datetime
    phase: str
    qr_token: UUID
    delivery_order_item_point_id: int
    order_id: int
    order_number: str | None = None
    operation_id: UUID | None = None
    scanned_by_dc_id: UUID | None = None
    actor_name: str | None = None
    delivery_point_name: str | None = None
    sku_name: str | None = None
    quantity: int | None = None
    payload: dict | None = None


class DcReceivingOrderResponse(BaseModel):
    """One order in receiving queue for current DC."""

    order_id: int
    order_number: str | None
    expected_count: int
    received_count: int
    remaining_count: int
    updated_at: datetime | None = None


class DcReceiveForOrderResponse(BaseModel):
    """Scan-receive response with order progress counters."""

    qr_token: UUID
    delivery_order_item_point_id: int
    order_id: int
    current_stage: str
    phase: str
    event_id: int
    operation_id: UUID | None
    is_idempotent: bool = False
    scanned_at: datetime
    delivery_point_name: str | None = None
    sku_name: str | None = None
    quantity: int | None = None
    expected_count: int
    received_count: int
    remaining_count: int
