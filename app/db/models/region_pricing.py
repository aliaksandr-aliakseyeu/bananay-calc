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
    """Тарифы и параметры расчета для региона."""

    __tablename__ = "region_pricing"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id"), unique=True, nullable=False, index=True
    )

    # === ВОДИТЕЛЬ ===
    driver_hourly_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Стоимость 1 часа работы водителя, руб."
    )
    planned_work_hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Часов на выполнение работы по плану"
    )

    # === ТРАНСПОРТ ===
    fuel_price_per_liter: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Стоимость бензина, руб/л"
    )
    fuel_consumption_per_100km: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Расход бензина, л/100км"
    )
    depreciation_coefficient: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False,
        comment="Коэффициент амортизации авто"
    )

    # === РАСПРЕДЕЛИТЕЛЬНЫЙ ЦЕНТР ===
    warehouse_processing_per_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Стоимость обработки 1 кг на РЦ, руб."
    )
    service_fee_per_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Сервисный сбор 1 кг (выручка компании), руб."
    )

    # === АДРЕСНАЯ ДОСТАВКА ===
    delivery_point_cost: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Стоимость одной точки доставки, руб."
    )

    # === ПАРАМЕТРЫ РЕЙСА ===
    standard_trip_weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Стандартный вес груза в рейсе, кг"
    )

    # === ЭТАЛОННАЯ КОРОБКА ===
    standard_box_length: Mapped[int] = mapped_column(
        nullable=False,
        comment="Длина эталонной коробки, см"
    )
    standard_box_width: Mapped[int] = mapped_column(
        nullable=False,
        comment="Ширина эталонной коробки, см"
    )
    standard_box_height: Mapped[int] = mapped_column(
        nullable=False,
        comment="Высота эталонной коробки, см"
    )
    standard_box_max_weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False,
        comment="Максимальный вес эталонной коробки, кг"
    )

    # === СКИДКИ ===
    min_points_for_discount: Mapped[int] = mapped_column(
        nullable=False,
        comment="Минимальное количество точек до применения скидки"
    )
    discount_step_points: Mapped[int] = mapped_column(
        nullable=False,
        comment="Шаг прироста количества точек доставки"
    )
    initial_discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False,
        comment="Стартовая скидка, %"
    )
    discount_step_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False,
        comment="Шаг прироста скидки, %"
    )

    # Relationships
    region: Mapped["Region"] = relationship(
        "Region", back_populates="pricing"
    )

    def __repr__(self) -> str:
        return f"<RegionPricing(id={self.id}, region_id={self.region_id})>"
