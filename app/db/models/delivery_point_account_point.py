from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.delivery_point import DeliveryPoint
    from app.db.models.delivery_point_account import DeliveryPointAccount


class DeliveryPointAccountPoint(Base):
    """Link table between delivery point accounts and delivery points."""

    __tablename__ = "delivery_point_account_points"
    __table_args__ = (
        UniqueConstraint("account_id", "delivery_point_id", name="uq_delivery_point_account_point"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id = mapped_column(
        ForeignKey("delivery_point_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    delivery_point_id = mapped_column(
        ForeignKey("geo_delivery_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    account: Mapped["DeliveryPointAccount"] = relationship(
        "DeliveryPointAccount",
        back_populates="point_links",
    )
    delivery_point: Mapped["DeliveryPoint"] = relationship("DeliveryPoint")
