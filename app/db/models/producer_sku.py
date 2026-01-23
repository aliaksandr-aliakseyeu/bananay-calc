"""Producer SKU model."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (Boolean, DateTime, ForeignKey, Integer, Numeric,
                        String, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.product_category import ProductCategory
    from app.db.models.temperature_mode import TemperatureMode
    from app.db.models.user import User


class ProducerSKU(Base):
    """Producer SKU (Stock Keeping Unit) with calculator parameters."""

    __tablename__ = "producer_skus"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    producer_id: Mapped[int] = mapped_column(
        ForeignKey("geo_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Producer (user) ID"
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True,
        comment="SKU name"
    )
    sku_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="SKU code/articul (unique per producer)"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="SKU description"
    )
    length_cm: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Product length in cm"
    )
    width_cm: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Product width in cm"
    )
    height_cm: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Product height in cm"
    )
    weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 3), nullable=False,
        comment="Weight of one item in kg"
    )
    items_per_box: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Number of items in producer's box"
    )
    product_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("geo_product_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Product category ID"
    )
    temperature_mode_id: Mapped[int | None] = mapped_column(
        ForeignKey("geo_temperature_modes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Temperature mode ID"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True,
        comment="Is SKU active"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation timestamp"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp"
    )

    producer: Mapped["User"] = relationship("User", back_populates="producer_skus")
    product_category: Mapped["ProductCategory | None"] = relationship("ProductCategory")
    temperature_mode: Mapped["TemperatureMode | None"] = relationship("TemperatureMode")

    def __repr__(self) -> str:
        return (
            f"<ProducerSKU(id={self.id}, name='{self.name}', "
            f"producer_id={self.producer_id}, sku_code='{self.sku_code}')>"
        )

