from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (Boolean, DateTime, ForeignKey, Index, Integer, Numeric,
                        String, func)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.driver_account import DriverAccount
    from app.db.models.media_file import MediaFile


class DriverVehicle(Base):
    """Driver vehicle (1..N per driver)."""

    __tablename__ = "driver_vehicles"
    __table_args__ = (Index("ix_driver_vehicles_driver_id_is_active", "driver_id", "is_active"),)

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
    model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    capacity_kg: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_m3: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    body_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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

    def __repr__(self) -> str:
        return f"<DriverVehicle(id={self.id}, plate_number='{self.plate_number}', driver_id={self.driver_id})>"
