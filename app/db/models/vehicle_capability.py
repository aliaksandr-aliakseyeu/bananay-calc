from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.driver_vehicle import DriverVehicle


class VehicleCapability(Base):
    """Operational characteristics used for matching vehicles to tasks."""

    __tablename__ = "vehicle_capabilities"
    __table_args__ = (
        CheckConstraint("payload_kg > 0", name="ck_vehicle_capabilities_payload_positive"),
        CheckConstraint(
            "cargo_volume_m3 IS NULL OR cargo_volume_m3 > 0",
            name="ck_vehicle_capabilities_volume_positive",
        ),
        CheckConstraint(
            "cargo_length_mm IS NULL OR cargo_length_mm > 0",
            name="ck_vehicle_capabilities_length_positive",
        ),
        CheckConstraint(
            "cargo_width_mm IS NULL OR cargo_width_mm > 0",
            name="ck_vehicle_capabilities_width_positive",
        ),
        CheckConstraint(
            "cargo_height_mm IS NULL OR cargo_height_mm > 0",
            name="ck_vehicle_capabilities_height_positive",
        ),
        CheckConstraint(
            "max_cargo_length_mm IS NULL OR max_cargo_length_mm > 0",
            name="ck_vehicle_capabilities_max_length_positive",
        ),
        CheckConstraint(
            "max_cargo_weight_kg IS NULL OR max_cargo_weight_kg > 0",
            name="ck_vehicle_capabilities_max_weight_positive",
        ),
        CheckConstraint(
            "banana_box_capacity IS NULL OR banana_box_capacity >= 0",
            name="ck_vehicle_capabilities_box_capacity_non_negative",
        ),
        CheckConstraint(
            "banana_box_capacity_bucket IS NULL OR banana_box_capacity_bucket >= 0",
            name="ck_vehicle_capabilities_box_bucket_non_negative",
        ),
        CheckConstraint(
            "("
            "has_refrigerator = FALSE AND min_temp_c IS NULL AND max_temp_c IS NULL"
            ") OR ("
            "has_refrigerator = TRUE AND min_temp_c IS NOT NULL AND max_temp_c IS NOT NULL AND min_temp_c <= max_temp_c"
            ")",
            name="ck_vehicle_capabilities_temperature_consistency",
        ),
        Index("ix_vehicle_capabilities_payload_kg", "payload_kg"),
        Index("ix_vehicle_capabilities_has_refrigerator", "has_refrigerator"),
        Index("ix_vehicle_capabilities_banana_box_capacity", "banana_box_capacity"),
    )

    vehicle_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("driver_vehicles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    payload_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    cargo_volume_m3: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3), nullable=True)
    cargo_length_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cargo_width_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cargo_height_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_cargo_length_mm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_cargo_weight_kg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    banana_box_capacity: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    banana_box_capacity_bucket: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    has_refrigerator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_temp_c: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    max_temp_c: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    supports_constant_temp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_liftgate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_ramp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_straps: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_antislip_floor: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allows_chilled_food: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allows_frozen_food: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allows_perishable_goods: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allows_fmcg: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allows_hazardous_goods: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hazard_class: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    vehicle: Mapped["DriverVehicle"] = relationship("DriverVehicle", back_populates="capabilities")
