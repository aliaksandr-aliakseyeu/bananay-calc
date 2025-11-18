"""Region Pricing model."""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.region import Region


class RegionPricing(Base):
    """Pricing and calculation parameters for region."""

    __tablename__ = "region_pricing"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id"), unique=True, nullable=False, index=True
    )
    driver_hourly_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Driver hourly rate, RUB"
    )
    planned_work_hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Planned working hours"
    )
    fuel_price_per_liter: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Fuel price, RUB/L"
    )
    fuel_consumption_per_100km: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Fuel consumption, L/100km"
    )
    depreciation_coefficient: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False,
        comment="Vehicle depreciation coefficient"
    )
    warehouse_processing_per_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Warehouse processing cost per kg, RUB"
    )
    service_fee_per_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Service fee per kg (company revenue), RUB"
    )
    delivery_point_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Cost per delivery point, RUB"
    )
    standard_trip_weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Standard trip cargo weight, kg"
    )
    standard_box_length: Mapped[int] = mapped_column(
        nullable=False,
        comment="Standard box length, cm"
    )
    standard_box_width: Mapped[int] = mapped_column(
        nullable=False,
        comment="Standard box width, cm"
    )
    standard_box_height: Mapped[int] = mapped_column(
        nullable=False,
        comment="Standard box height, cm"
    )
    standard_box_max_weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Standard box maximum weight, kg"
    )
    min_points_for_discount: Mapped[int] = mapped_column(
        nullable=False,
        comment="Minimum points before discount applies"
    )
    discount_step_points: Mapped[int] = mapped_column(
        nullable=False,
        comment="Step increment for delivery points"
    )
    initial_discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False,
        comment="Initial discount, %"
    )
    discount_step_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False,
        comment="Discount step increment, %"
    )
    region: Mapped["Region"] = relationship(
        "Region", back_populates="pricing"
    )

    def __repr__(self) -> str:
        return f"<RegionPricing(id={self.id}, region_id={self.region_id})>"
