from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import DailyCheckInPhotoKind, DailyCheckInStatus

if TYPE_CHECKING:
    from app.db.models.courier_account import CourierAccount
    from app.db.models.courier_vehicle import CourierVehicle
    from app.db.models.media_file import MediaFile


class CourierDailyCheckIn(Base):
    """Daily check-in for couriers. Must complete before starting work each day."""

    __tablename__ = "courier_daily_checkins"
    __table_args__ = (
        UniqueConstraint("courier_id", "vehicle_id", "check_date", name="uq_courier_daily_checkin_courier_vehicle_date"),
        Index("ix_courier_daily_checkins_courier_date", "courier_id", "check_date"),
        Index("ix_courier_daily_checkins_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    courier_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courier_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courier_vehicles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    check_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    status: Mapped[DailyCheckInStatus] = mapped_column(
        Enum(
            DailyCheckInStatus,
            native_enum=False,
            length=50,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DailyCheckInStatus.PENDING,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    courier: Mapped["CourierAccount"] = relationship("CourierAccount", lazy="raise_on_sql")
    vehicle: Mapped["CourierVehicle"] = relationship("CourierVehicle", lazy="raise_on_sql")
    photos: Mapped[list["CourierDailyCheckInPhoto"]] = relationship(
        "CourierDailyCheckInPhoto",
        back_populates="checkin",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<CourierDailyCheckIn(id={self.id}, courier_id={self.courier_id}, "
            f"date={self.check_date}, status={self.status})"
        )


class CourierDailyCheckInPhoto(Base):
    """Individual photo within a courier daily check-in."""

    __tablename__ = "courier_daily_checkin_photos"
    __table_args__ = (
        UniqueConstraint("checkin_id", "kind", name="uq_courier_checkin_photo_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    checkin_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("courier_daily_checkins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[DailyCheckInPhotoKind] = mapped_column(
        Enum(
            DailyCheckInPhotoKind,
            native_enum=False,
            length=50,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_files.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    checkin: Mapped["CourierDailyCheckIn"] = relationship("CourierDailyCheckIn", back_populates="photos")
    media: Mapped["MediaFile"] = relationship("MediaFile", lazy="raise_on_sql")

    def __repr__(self) -> str:
        return f"<CourierDailyCheckInPhoto(id={self.id}, kind={self.kind}, checkin_id={self.checkin_id})>"
