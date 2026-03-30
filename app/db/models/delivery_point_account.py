from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import DeliveryPointAccountStatus

if TYPE_CHECKING:
    from app.db.models.delivery_point_account_point import DeliveryPointAccountPoint


class DeliveryPointAccount(Base):
    """Delivery point account (OTP auth)."""

    __tablename__ = "delivery_point_accounts"
    __table_args__ = (Index("ix_delivery_point_accounts_status", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    phone_e164: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    status: Mapped[DeliveryPointAccountStatus] = mapped_column(
        Enum(
            DeliveryPointAccountStatus,
            native_enum=False,
            length=20,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=DeliveryPointAccountStatus.DRAFT,
        index=True,
    )
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tracking_list_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tracking_list_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    about_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_delivery_point_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    application_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    application_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    application_reviewed_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("geo_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    application_reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocked_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    blocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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

    point_links: Mapped[list["DeliveryPointAccountPoint"]] = relationship(
        "DeliveryPointAccountPoint",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<DeliveryPointAccount(id={self.id}, phone_e164='{self.phone_e164}', "
            f"status='{self.status}')>"
        )
