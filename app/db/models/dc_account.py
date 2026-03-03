from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import DcAccountStatus


class DcAccount(Base):
    """Distribution center employee account (OTP auth, separate from User/Driver)."""

    __tablename__ = "dc_accounts"
    __table_args__ = (
        Index("ix_dc_accounts_status_distribution_center_id", "status", "distribution_center_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    phone_e164: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    status: Mapped[DcAccountStatus] = mapped_column(
        Enum(
            DcAccountStatus,
            native_enum=False,
            length=20,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DcAccountStatus.DRAFT,
        index=True,
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    distribution_center_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("geo_distribution_centers.id", ondelete="SET NULL"),
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
    blocked_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    blocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
