from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import DriverOtpStatus


class DriverOtpCode(Base):
    """OTP codes for driver SMS auth (stored in DB, one-time use)."""

    __tablename__ = "driver_otp_codes"

    phone_e164: Mapped[str] = mapped_column(String(20), primary_key=True)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[DriverOtpStatus] = mapped_column(
        Enum(
            DriverOtpStatus,
            native_enum=False,
            length=20,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DriverOtpStatus.PENDING,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DriverOtpCode(phone_e164='{self.phone_e164}', status='{self.status}', expires_at={self.expires_at})>"
