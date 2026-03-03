"""Model for driver last reported location (per order)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.delivery_order import DeliveryOrder
    from app.db.models.driver_account import DriverAccount


class DriverLastLocation(Base):
    """
    Last reported location for a driver on a given order.

    One row per (driver_id, delivery_order_id). UPSERT on each report.
    """

    __tablename__ = "driver_last_location"
    __table_args__ = (
        UniqueConstraint("driver_id", "delivery_order_id", name="uq_driver_order_location"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    driver_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("driver_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    delivery_order_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    reported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    device_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    driver: Mapped["DriverAccount"] = relationship("DriverAccount")
    order: Mapped["DeliveryOrder"] = relationship("DeliveryOrder")
