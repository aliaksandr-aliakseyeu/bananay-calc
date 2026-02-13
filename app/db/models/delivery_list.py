from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.delivery_point import DeliveryPoint
    from app.db.models.user import User


class DeliveryList(Base):
    """User's delivery list (collection of delivery points)."""

    __tablename__ = "geo_delivery_lists"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("geo_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="delivery_lists")
    items: Mapped[list["DeliveryListItem"]] = relationship(
        "DeliveryListItem", back_populates="delivery_list", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DeliveryList(id={self.id}, name='{self.name}', user_id={self.user_id})>"


class DeliveryListItem(Base):
    """Item in a delivery list (link between list and delivery point)."""

    __tablename__ = "geo_delivery_list_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    list_id: Mapped[int] = mapped_column(
        ForeignKey("geo_delivery_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delivery_point_id: Mapped[int] = mapped_column(
        ForeignKey("geo_delivery_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    custom_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    delivery_list: Mapped["DeliveryList"] = relationship("DeliveryList", back_populates="items")
    delivery_point: Mapped["DeliveryPoint"] = relationship("DeliveryPoint")

    def __repr__(self) -> str:
        return (
            f"<DeliveryListItem(id={self.id}, list_id={self.list_id}, "
            f"delivery_point_id={self.delivery_point_id})>"
        )
