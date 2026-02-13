"""Telegram binding for driver OTP delivery (simulated SMS)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DriverTelegramBinding(Base):
    """Phone ↔ Telegram chat_id for sending OTP via bot instead of SMS."""

    __tablename__ = "driver_telegram_bindings"

    phone_e164: Mapped[str] = mapped_column(String(20), primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
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

    def __repr__(self) -> str:
        return f"<DriverTelegramBinding(phone_e164='{self.phone_e164}', chat_id={self.telegram_chat_id})>"
