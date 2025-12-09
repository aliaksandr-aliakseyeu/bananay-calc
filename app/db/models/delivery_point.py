from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Table, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.category import Category, Subcategory, Tag
    from app.db.models.district import District
    from app.db.models.settlement import Settlement

delivery_point_tags = Table(
    "geo_delivery_point_tags",
    Base.metadata,
    Column("delivery_point_id", Integer, ForeignKey("geo_delivery_points.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("geo_tags.id"), primary_key=True),
)


class DeliveryPoint(Base):
    """Delivery point."""

    __tablename__ = "geo_delivery_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name_normalized: Mapped[str] = mapped_column(Text, nullable=False, index=True)
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
        Geometry(geometry_type='POINT', srid=4326, spatial_index=True),
        nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("geo_categories.id"), nullable=True, index=True
    )
    subcategory_id: Mapped[int | None] = mapped_column(
        ForeignKey("geo_subcategories.id"), nullable=True, index=True
    )
    # TODO: MVP - contacts in main table.
    # TODO: For production: move to separate DeliveryPointContact table (many-to-one)
    phone: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="May contain multiple phone numbers separated by comma"
    )
    mobile: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="May contain multiple mobile numbers separated by comma"
    )
    email: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="May contain multiple emails separated by comma"
    )

    # TODO: MVP - schedule as text.
    # TODO: For production: separate DeliveryPointSchedule table with fields:
    # TODO: - day_of_week (0-6), open_time, close_time, is_24_hours
    # TODO: This will allow "open now" filter
    schedule: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    settlement: Mapped["Settlement"] = relationship("Settlement", back_populates="delivery_points")
    district: Mapped["District | None"] = relationship("District")
    category: Mapped["Category | None"] = relationship("Category")
    subcategory: Mapped["Subcategory | None"] = relationship("Subcategory")
    tags: Mapped[list["Tag"]] = relationship(
        "Tag", secondary=delivery_point_tags, lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<DeliveryPoint(id={self.id}, name='{self.name}')>"
