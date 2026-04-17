from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.driver_vehicle import DriverVehicle


class VehicleCompliance(Base):
    """Documents and verification state for a vehicle."""

    __tablename__ = "vehicle_compliance"

    vehicle_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("driver_vehicles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    insurance_valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_inspection_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sts_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verification_status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    vehicle: Mapped["DriverVehicle"] = relationship("DriverVehicle", back_populates="compliance")
