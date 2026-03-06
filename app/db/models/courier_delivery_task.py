from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import CourierTaskStatus

if TYPE_CHECKING:
    from app.db.models.courier_account import CourierAccount
    from app.db.models.delivery_order import DeliveryOrderItemPoint
    from app.db.models.media_file import MediaFile


class CourierDeliveryTask(Base):
    """
    Courier delivery task: pick up from DC, deliver to DeliveryOrderItemPoint.

    One task = one item point (one box/batch to one delivery point).
    """

    __tablename__ = "courier_delivery_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    item_point_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_order_item_points.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    courier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courier_accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[CourierTaskStatus] = mapped_column(
        String(20),
        nullable=False,
        default=CourierTaskStatus.ASSIGNED,
        index=True,
    )
    taken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    in_transit_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    qr_scanned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivery_photo_media_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    media_owner_uuid: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
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

    courier: Mapped["CourierAccount"] = relationship("CourierAccount")
    item_point: Mapped["DeliveryOrderItemPoint"] = relationship("DeliveryOrderItemPoint")
    delivery_photo: Mapped[Optional["MediaFile"]] = relationship(
        "MediaFile",
        foreign_keys=[delivery_photo_media_id],
        lazy="raise_on_sql",
    )

    def __repr__(self) -> str:
        return f"<CourierDeliveryTask(id={self.id}, courier_id={self.courier_id}, status='{self.status}')>"
