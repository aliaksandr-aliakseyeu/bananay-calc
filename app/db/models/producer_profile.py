from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class ProducerProfile(Base):
    """Producer profile with company information."""

    __tablename__ = "producer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("geo_users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    company_inn: Mapped[Optional[str]] = mapped_column(
        String(12), unique=True, nullable=True, index=True
    )
    contact_person: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    company_address: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="producer_profile")

    def __repr__(self) -> str:
        return f"<ProducerProfile(id={self.id}, user_id={self.user_id}, company='{self.company_name}')>"
