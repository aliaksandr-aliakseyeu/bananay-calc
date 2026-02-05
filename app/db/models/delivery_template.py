"""
Delivery Template models for reusable delivery configurations.

A template is a saved configuration of:
- One SKU
- Multiple delivery points with quantities
- Warehouse location and region

Templates can be reused to quickly create delivery orders.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, Numeric,
                        String, Text, func)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.delivery_order import DeliveryOrderItem
    from app.db.models.delivery_point import DeliveryPoint
    from app.db.models.producer_sku import ProducerSKU
    from app.db.models.region import Region
    from app.db.models.user import User


class DeliveryTemplate(Base):
    """
    Reusable delivery template.

    A template is a "recipe" for delivery that can be used multiple times.
    Producer creates templates once and reuses them when creating orders.
    """
    __tablename__ = "delivery_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    producer_id: Mapped[int] = mapped_column(
        ForeignKey("geo_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    producer_sku_id: Mapped[int] = mapped_column(
        ForeignKey("producer_skus.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    region_id: Mapped[int] = mapped_column(
        ForeignKey("geo_regions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    warehouse_lat: Mapped[float] = mapped_column(Float, nullable=False)
    warehouse_lon: Mapped[float] = mapped_column(Float, nullable=False)

    total_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    cost_per_unit: Mapped[float] = mapped_column(Numeric(10, 2), nullable=True)
    last_calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    producer: Mapped["User"] = relationship("User", back_populates="delivery_templates")
    producer_sku: Mapped["ProducerSKU"] = relationship("ProducerSKU", back_populates="delivery_templates")
    region: Mapped["Region"] = relationship("Region")
    points: Mapped[list["DeliveryTemplatePoint"]] = relationship(
        "DeliveryTemplatePoint",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="DeliveryTemplatePoint.created_at"
    )
    order_items: Mapped[list["DeliveryOrderItem"]] = relationship(
        "DeliveryOrderItem",
        back_populates="template",
    )

    def __repr__(self) -> str:
        return f"<DeliveryTemplate(id={self.id}, name='{self.name}', producer_id={self.producer_id})>"


class DeliveryTemplatePoint(Base):
    """
    Delivery point within a template with quantity.

    Links a template to delivery points with specific quantities for each point.
    """
    __tablename__ = "delivery_template_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delivery_point_id: Mapped[int] = mapped_column(
        ForeignKey("geo_delivery_points.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    template: Mapped["DeliveryTemplate"] = relationship("DeliveryTemplate", back_populates="points")
    delivery_point: Mapped["DeliveryPoint"] = relationship("DeliveryPoint")

    def __repr__(self) -> str:
        return (
            f"<DeliveryTemplatePoint(id={self.id}, template_id={self.template_id}, "
            f"delivery_point_id={self.delivery_point_id}, quantity={self.quantity})>"
        )
