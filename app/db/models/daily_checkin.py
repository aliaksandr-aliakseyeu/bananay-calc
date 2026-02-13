from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (Date, DateTime, Enum, ForeignKey, Index, Text,
                        UniqueConstraint, func)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import DailyCheckInPhotoKind, DailyCheckInStatus

if TYPE_CHECKING:
    from app.db.models.driver_account import DriverAccount
    from app.db.models.driver_vehicle import DriverVehicle
    from app.db.models.media_file import MediaFile


class DailyCheckIn(Base):
    """
    Daily check-in (ЕКФ - Ежедневный Контроль Функционирования).

    Driver must complete this before starting work each day.
    Includes selfie + vehicle photos to verify identity and vehicle condition.
    """

    __tablename__ = "daily_checkins"
    __table_args__ = (
        UniqueConstraint("driver_id", "vehicle_id", "check_date", name="uq_daily_checkin_driver_vehicle_date"),
        Index("ix_daily_checkins_driver_date", "driver_id", "check_date"),
        Index("ix_daily_checkins_status", "status"),
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
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("driver_vehicles.id", ondelete="CASCADE"),
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
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    driver: Mapped["DriverAccount"] = relationship("DriverAccount", lazy="raise_on_sql")
    vehicle: Mapped["DriverVehicle"] = relationship("DriverVehicle", lazy="raise_on_sql")
    photos: Mapped[list["DailyCheckInPhoto"]] = relationship(
        "DailyCheckInPhoto",
        back_populates="checkin",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<DailyCheckIn(id={self.id}, driver_id={self.driver_id}, date={self.check_date}, status={self.status})>"


class DailyCheckInPhoto(Base):
    """
    Individual photo within a daily check-in.

    Required photos:
    - selfie: Driver's face
    - vehicle_front: Front of vehicle
    - vehicle_left: Left side
    - vehicle_right: Right side
    - vehicle_rear: Rear of vehicle
    - vehicle_cargo: Open cargo area
    """

    __tablename__ = "daily_checkin_photos"
    __table_args__ = (
        UniqueConstraint("checkin_id", "kind", name="uq_checkin_photo_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    checkin_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("daily_checkins.id", ondelete="CASCADE"),
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

    checkin: Mapped["DailyCheckIn"] = relationship("DailyCheckIn", back_populates="photos")
    media: Mapped["MediaFile"] = relationship("MediaFile", lazy="raise_on_sql")

    def __repr__(self) -> str:
        return f"<DailyCheckInPhoto(id={self.id}, kind={self.kind}, checkin_id={self.checkin_id})>"
