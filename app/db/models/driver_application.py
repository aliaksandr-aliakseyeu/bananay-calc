from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import DriverApplicationStatus

if TYPE_CHECKING:
    from app.db.models.driver_account import DriverAccount


class DriverApplication(Base):
    """Driver application (KYC-lite) for moderation."""

    __tablename__ = "driver_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("driver_accounts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    status: Mapped[DriverApplicationStatus] = mapped_column(
        Enum(
            DriverApplicationStatus,
            native_enum=False,
            length=50,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DriverApplicationStatus.DRAFT,
        index=True,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("geo_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    driver: Mapped["DriverAccount"] = relationship("DriverAccount", back_populates="application")

    def __repr__(self) -> str:
        return f"<DriverApplication(id={self.id}, driver_id={self.driver_id}, status='{self.status}')>"
