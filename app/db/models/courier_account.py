from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import CourierAccountStatus

if TYPE_CHECKING:
    from app.db.models.courier_application import CourierApplication
    from app.db.models.courier_vehicle import CourierVehicle


class CourierAccount(Base):
    """Courier account (OTP auth, separate from User/DriverAccount)."""

    __tablename__ = "courier_accounts"
    __table_args__ = (Index("ix_courier_accounts_status_region_id", "status", "region_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    phone_e164: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    status: Mapped[CourierAccountStatus] = mapped_column(
        Enum(
            CourierAccountStatus,
            native_enum=False,
            length=50,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=CourierAccountStatus.DRAFT,
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

    vehicles: Mapped[list["CourierVehicle"]] = relationship(
        "CourierVehicle",
        back_populates="courier",
        cascade="all, delete-orphan",
    )
    application: Mapped[Optional["CourierApplication"]] = relationship(
        "CourierApplication",
        back_populates="courier",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CourierAccount(id={self.id}, phone_e164='{self.phone_e164}', status='{self.status}')>"
