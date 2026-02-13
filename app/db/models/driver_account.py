from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import DriverAccountStatus

if TYPE_CHECKING:
    from app.db.models.driver_application import DriverApplication
    from app.db.models.driver_vehicle import DriverVehicle


class DriverAccount(Base):
    """Driver account (SMS auth, separate from User)."""

    __tablename__ = "driver_accounts"
    __table_args__ = (Index("ix_driver_accounts_status_region_id", "status", "region_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    phone_e164: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    status: Mapped[DriverAccountStatus] = mapped_column(
        Enum(
            DriverAccountStatus,
            native_enum=False,
            length=50,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DriverAccountStatus.DRAFT,
        index=True,
    )
    full_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    street: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    building: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    apartment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    region_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("geo_regions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payout_account: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    vehicles: Mapped[list["DriverVehicle"]] = relationship(
        "DriverVehicle",
        back_populates="driver",
        cascade="all, delete-orphan",
    )
    application: Mapped[Optional["DriverApplication"]] = relationship(
        "DriverApplication",
        back_populates="driver",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DriverAccount(id={self.id}, phone_e164='{self.phone_e164}', status='{self.status}')>"
