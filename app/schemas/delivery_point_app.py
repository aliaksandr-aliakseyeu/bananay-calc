"""Schemas for delivery point mobile/web app."""
from datetime import datetime

from pydantic import BaseModel, Field


class DeliveryPointLinkedPoint(BaseModel):
    id: int
    name: str
    address: str | None = None


class DeliveryPointMeResponse(BaseModel):
    id: str
    phone_e164: str
    email: str | None = None
    tracking_list_name: str | None = None
    tracking_list_description: str | None = None
    status: str
    first_name: str | None = None
    last_name: str | None = None
    about_text: str | None = None
    application_submitted_at: datetime | None = None
    application_reject_reason: str | None = None
    points: list[DeliveryPointLinkedPoint]
    requested_points: list[DeliveryPointLinkedPoint]


class DeliveryPointMeUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None


class DeliveryPointSubmitApplicationRequest(BaseModel):
    about_text: str
    delivery_point_ids: list[int]


class DeliveryPointTrackingListUpsertRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str | None = Field(None, max_length=500)
    delivery_point_ids: list[int]


class DeliveryPointDeliveryItem(BaseModel):
    item_point_id: int
    order_id: int
    order_number: str | None = None
    order_status: str
    point_status: str
    delivery_point_id: int
    delivery_point_name: str | None = None
    delivery_point_address: str | None = None
    sku_name: str | None = None
    quantity: int
    courier_id: str | None = None
    courier_phone: str | None = None
    courier_name: str | None = None
    delivery_photo_media_id: str | None = None
    expected_pickup_date: datetime | None = None
    delivery_deadline: datetime | None = None
    delivered_at: datetime | None = None
    updated_at: datetime


class DeliveryPointHistoryResponse(BaseModel):
    total: int
    items: list[DeliveryPointDeliveryItem]
