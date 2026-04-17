from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (CheckConstraint, DateTime, ForeignKey, Index,
                        SmallInteger, String, func)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import DriverVehicleStatus
from app.utils.vehicle import (body_type_label_from_code,
                               normalize_plate_number,
                               vehicle_is_active_for_operations)

if TYPE_CHECKING:
    from app.db.models.driver_account import DriverAccount
    from app.db.models.media_file import MediaFile
    from app.db.models.vehicle_capability import VehicleCapability
    from app.db.models.vehicle_compliance import VehicleCompliance


class DriverVehicle(Base):
    """Driver vehicle (1..N per driver)."""

    __tablename__ = "driver_vehicles"
    __table_args__ = (
        Index("ix_driver_vehicles_driver_id_status", "driver_id", "status"),
        CheckConstraint(
            "year IS NULL OR year BETWEEN 1950 AND EXTRACT(YEAR FROM NOW())::int + 1",
            name="ck_driver_vehicles_year_reasonable",
        ),
        CheckConstraint(
            "plate_number_normalized IS NULL OR plate_number_normalized <> ''",
            name="ck_driver_vehicles_plate_number_normalized_not_blank",
        ),
        CheckConstraint(
            "vin IS NULL OR length(vin) BETWEEN 11 AND 17",
            name="ck_driver_vehicles_vin_length",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("driver_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False)
    plate_number_normalized: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    vin: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    body_type_code: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    status: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=int(DriverVehicleStatus.ACTIVE),
        server_default=str(int(DriverVehicleStatus.ACTIVE)),
        index=True,
    )
    photo_media_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sts_media_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    driver: Mapped["DriverAccount"] = relationship("DriverAccount", back_populates="vehicles")
    photo_media: Mapped[Optional["MediaFile"]] = relationship(
        "MediaFile",
        foreign_keys=[photo_media_id],
        lazy="raise_on_sql",
    )
    sts_media: Mapped[Optional["MediaFile"]] = relationship(
        "MediaFile",
        foreign_keys=[sts_media_id],
        lazy="raise_on_sql",
    )
    capabilities: Mapped[Optional["VehicleCapability"]] = relationship(
        "VehicleCapability",
        back_populates="vehicle",
        uselist=False,
        cascade="all, delete-orphan",
    )
    compliance: Mapped[Optional["VehicleCompliance"]] = relationship(
        "VehicleCompliance",
        back_populates="vehicle",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def payload_kg(self) -> int:
        if self.capabilities is None or self.capabilities.payload_kg is None:
            return 0
        return self.capabilities.payload_kg

    def cargo_volume_m3(self) -> Decimal | None:
        if self.capabilities is None:
            return None
        return self.capabilities.cargo_volume_m3

    def legacy_body_type(self) -> Optional[str]:
        return body_type_label_from_code(self.body_type_code)

    @property
    def capacity_kg(self) -> int:
        return self.payload_kg()

    @property
    def capacity_m3(self) -> Decimal | None:
        return self.cargo_volume_m3()

    @property
    def body_type(self) -> Optional[str]:
        return self.legacy_body_type()

    @property
    def is_active(self) -> bool:
        return vehicle_is_active_for_operations(self.status)

    def normalize_plate(self) -> None:
        self.plate_number = (self.plate_number or "").strip()
        self.plate_number_normalized = normalize_plate_number(self.plate_number)

    def __repr__(self) -> str:
        return f"<DriverVehicle(id={self.id}, plate_number='{self.plate_number}', driver_id={self.driver_id})>"
