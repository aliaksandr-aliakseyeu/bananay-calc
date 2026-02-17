"""
Delivery Order models for tracking product deliveries from producer to delivery points.

A delivery order is created from one or more delivery templates.
It contains snapshots of templates at the time of order creation.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.delivery_point import DeliveryPoint
    from app.db.models.delivery_template import DeliveryTemplate
    from app.db.models.producer_sku import ProducerSKU
    from app.db.models.region import Region
    from app.db.models.user import User


class OrderStatus(str, enum.Enum):
    """Order status enum reflecting multi-stage delivery process"""
    DRAFT = "draft"  # Draft, not yet submitted
    PENDING = "pending"  # Created, waiting to be sent
    IN_TRANSIT_TO_DC = "in_transit_to_dc"  # In transit to Distribution Center
    AT_DC = "at_dc"  # At Distribution Center
    DRIVER_ASSIGNED = "driver_assigned"  # Driver assigned for delivery
    IN_DELIVERY = "in_delivery"  # In delivery process to points
    PARTIALLY_DELIVERED = "partially_delivered"  # Some points delivered
    COMPLETED = "completed"  # All points delivered
    CANCELLED = "cancelled"  # Order cancelled


class OrderPriority(str, enum.Enum):
    """Order priority enum"""
    NORMAL = "normal"  # Normal priority
    HIGH = "high"  # High priority
    URGENT = "urgent"  # Urgent priority


class DeliveryPointStatus(str, enum.Enum):
    """Status for individual delivery points"""
    PENDING = "pending"  # Not yet delivered
    IN_TRANSIT = "in_transit"  # Driver on the way
    DELIVERED = "delivered"  # Successfully delivered
    FAILED = "failed"  # Delivery failed


class DeliveryOrder(Base):
    """
    Delivery order for tracking product deliveries.

    Now supports multiple SKUs (via multiple items/templates).
    Each order is created from one or more delivery templates.
    """
    __tablename__ = "delivery_orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    producer_id: Mapped[int] = mapped_column(
        ForeignKey("geo_users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    total_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OrderStatus.DRAFT,
        index=True
    )
    priority: Mapped[OrderPriority] = mapped_column(
        SQLEnum(OrderPriority, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OrderPriority.NORMAL,
    )

    expected_pickup_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_pickup_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    producer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sent_to_dc_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at_dc_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    driver_assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivery_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    producer: Mapped["User"] = relationship("User", back_populates="delivery_orders")
    items: Mapped[list["DeliveryOrderItem"]] = relationship(
        "DeliveryOrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="DeliveryOrderItem.created_at"
    )
    status_history: Mapped[list["DeliveryOrderStatusHistory"]] = relationship(
        "DeliveryOrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="DeliveryOrderStatusHistory.created_at.desc()",
    )


class DeliveryOrderItem(Base):
    """
    Snapshot of a delivery template within an order.

    When an order is created from templates, each template is copied
    into a DeliveryOrderItem. This ensures that changes to the template
    don't affect existing orders.
    """
    __tablename__ = "delivery_order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("delivery_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )

    template_name: Mapped[str] = mapped_column(String(200), nullable=False)
    producer_sku_id: Mapped[int] = mapped_column(
        ForeignKey("producer_skus.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sku_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    region_id: Mapped[int] = mapped_column(
        ForeignKey("geo_regions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    warehouse_lat: Mapped[float] = mapped_column(Float, nullable=False)
    warehouse_lon: Mapped[float] = mapped_column(Float, nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    item_cost: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    cost_per_unit: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    order: Mapped["DeliveryOrder"] = relationship("DeliveryOrder", back_populates="items")
    template: Mapped["DeliveryTemplate | None"] = relationship("DeliveryTemplate", back_populates="order_items")
    producer_sku: Mapped["ProducerSKU"] = relationship("ProducerSKU")
    region: Mapped["Region"] = relationship("Region")
    points: Mapped[list["DeliveryOrderItemPoint"]] = relationship(
        "DeliveryOrderItemPoint",
        back_populates="order_item",
        cascade="all, delete-orphan",
        order_by="DeliveryOrderItemPoint.created_at"
    )


class DeliveryOrderItemPoint(Base):
    """
    Individual delivery point within an order item.

    Tracks delivery status, quantity, and proof of delivery for each point.
    """
    __tablename__ = "delivery_order_item_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_order_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delivery_point_id: Mapped[int] = mapped_column(
        ForeignKey("geo_delivery_points.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[DeliveryPointStatus] = mapped_column(
        SQLEnum(DeliveryPointStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=DeliveryPointStatus.PENDING,
        index=True
    )
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    order_item: Mapped["DeliveryOrderItem"] = relationship("DeliveryOrderItem", back_populates="points")
    delivery_point: Mapped["DeliveryPoint"] = relationship("DeliveryPoint")


class DeliveryOrderStatusHistory(Base):
    """
    Audit log for order status changes.

    Tracks who changed status, when, and any notes about the change.
    """
    __tablename__ = "delivery_order_status_history"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("geo_users.id", ondelete="SET NULL"), nullable=True
    )
    old_status: Mapped[OrderStatus | None] = mapped_column(
        SQLEnum(OrderStatus, values_callable=lambda x: [e.value for e in x]), nullable=True
    )
    new_status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    order: Mapped["DeliveryOrder"] = relationship("DeliveryOrder", back_populates="status_history")
    changed_by: Mapped["User | None"] = relationship("User")
