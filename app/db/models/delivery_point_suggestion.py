"""Delivery point suggestion model (producer-submitted, pending moderation)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.category import Tag
    from app.db.models.settlement import Settlement
    from app.db.models.user import User

delivery_point_suggestion_tags = Table(
    "geo_delivery_point_suggestion_tags",
    Base.metadata,
    Column(
        "suggestion_id",
        Integer,
        ForeignKey("geo_delivery_point_suggestions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("tag_id", Integer, ForeignKey("geo_tags.id"), primary_key=True),
)


class DeliveryPointSuggestion(Base):
    """
    Producer-submitted delivery point (pending moderation).

    Same fields as DeliveryPoint (except name_normalized). On approval,
    data is copied to DeliveryPoint and this record can be removed.
    """

    __tablename__ = "geo_delivery_point_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Title (additional description)"
    )
    settlement_id: Mapped[int] = mapped_column(
        ForeignKey("geo_settlements.id"), nullable=False, index=True
    )
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("geo_districts.id"), nullable=True, index=True
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    landmark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=False,
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("geo_categories.id"), nullable=True, index=True
    )
    subcategory_id: Mapped[int | None] = mapped_column(
        ForeignKey("geo_subcategories.id"), nullable=True, index=True
    )
    phone: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="May contain multiple phone numbers separated by comma"
    )
    mobile: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="May contain multiple mobile numbers separated by comma"
    )
    email: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="May contain multiple emails separated by comma"
    )
    schedule: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("geo_users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    settlement: Mapped["Settlement"] = relationship("Settlement")
    created_by: Mapped["User"] = relationship("User", back_populates="delivery_point_suggestions")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=delivery_point_suggestion_tags, lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<DeliveryPointSuggestion(id={self.id}, name='{self.name}', created_by_id={self.created_by_id})>"
