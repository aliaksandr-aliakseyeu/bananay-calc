"""
Models for driver delivery tasks and DC allocation/status tracking.

- delivery_order_item_dc_allocation: pre-computed (order_item, dc) -> quantity
- delivery_order_item_dc_status: producer view - (order_item, dc) -> status
- driver_delivery_task: driver task (warehouse -> DCs)
- driver_task_dc_delivery: per-DC status within driver task
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.delivery_order import DeliveryOrder, DeliveryOrderItem
    from app.db.models.distribution_center import DistributionCenter
    from app.db.models.driver_account import DriverAccount


class ItemDCStatus(str, enum.Enum):
    """Status for (order_item, dc) - producer view."""

    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class DriverTaskStatus(str, enum.Enum):
    """Status for driver delivery task."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    LOADING = "loading"
    IN_TRANSIT = "in_transit"
    PARTIALLY_DELIVERED = "partially_delivered"
    DELIVERED = "delivered"


class DriverTaskDCStatus(str, enum.Enum):
    """Status for (task, dc) - driver view."""

    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"


class DeliveryOrderItemDCAllocation(Base):
    """
    Pre-computed allocation: how much of order_item goes to which DC.

    Created when order goes to pending. Aggregates delivery_order_item_points
    by sector -> DC.
    """

    __tablename__ = "delivery_order_item_dc_allocations"
    __table_args__ = (
        UniqueConstraint("order_item_id", "dc_id", name="uq_order_item_dc_allocation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dc_id: Mapped[int] = mapped_column(
        ForeignKey("geo_distribution_centers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    order_item: Mapped["DeliveryOrderItem"] = relationship(
        "DeliveryOrderItem",
        back_populates="dc_allocations",
    )
    dc: Mapped["DistributionCenter"] = relationship("DistributionCenter")


class DeliveryOrderItemDCStatus(Base):
    """
    Status for (order_item, dc) - producer view.

    Updated when driver delivers to DC. Producer sees which SKUs have reached which DCs.
    """

    __tablename__ = "delivery_order_item_dc_status"
    __table_args__ = (
        UniqueConstraint("order_item_id", "dc_id", name="uq_order_item_dc_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_item_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dc_id: Mapped[int] = mapped_column(
        ForeignKey("geo_distribution_centers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[ItemDCStatus] = mapped_column(
        String(20),
        nullable=False,
        default=ItemDCStatus.PENDING,
        index=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    order_item: Mapped["DeliveryOrderItem"] = relationship(
        "DeliveryOrderItem",
        back_populates="dc_status",
    )
    dc: Mapped["DistributionCenter"] = relationship("DistributionCenter")


class DriverDeliveryTask(Base):
    """
    Driver task: pick up at warehouse, deliver to several DCs.

    One task = one warehouse. Created from order items with same warehouse.
    """

    __tablename__ = "driver_delivery_tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_lat: Mapped[float] = mapped_column(Float, nullable=False)
    warehouse_lon: Mapped[float] = mapped_column(Float, nullable=False)
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("driver_accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[DriverTaskStatus] = mapped_column(
        String(30),
        nullable=False,
        default=DriverTaskStatus.PENDING,
        index=True,
    )

    taken_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    loading_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    in_transit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    media_owner_uuid: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    loading_photo_media_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    order: Mapped["DeliveryOrder"] = relationship("DeliveryOrder")
    driver: Mapped["DriverAccount | None"] = relationship("DriverAccount")
    dc_deliveries: Mapped[list["DriverTaskDCDelivery"]] = relationship(
        "DriverTaskDCDelivery",
        back_populates="task",
        cascade="all, delete-orphan",
    )


class DriverTaskDCDelivery(Base):
    """
    Per-DC delivery within a driver task.

    Driver marks each DC as delivered when he unloads there.
    """

    __tablename__ = "driver_task_dc_deliveries"
    __table_args__ = (
        UniqueConstraint("task_id", "dc_id", name="uq_task_dc_delivery"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("driver_delivery_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dc_id: Mapped[int] = mapped_column(
        ForeignKey("geo_distribution_centers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[DriverTaskDCStatus] = mapped_column(
        String(20),
        nullable=False,
        default=DriverTaskDCStatus.PENDING,
        index=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    unload_photo_media_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    task: Mapped["DriverDeliveryTask"] = relationship(
        "DriverDeliveryTask",
        back_populates="dc_deliveries",
    )
    dc: Mapped["DistributionCenter"] = relationship("DistributionCenter")
