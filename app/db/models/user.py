from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import UserRole


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "geo_users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=50),
        nullable=False,
        default=UserRole.PRODUCER,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("geo_users.id"), nullable=True
    )
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rejected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_by: Mapped[Optional[int]] = mapped_column(
        ForeignKey("geo_users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    approver: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by],
        remote_side=[id],
        back_populates="approved_users"
    )
    approved_users: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys=[approved_by],
        back_populates="approver"
    )

    rejecter: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[rejected_by],
        remote_side=[id],
        back_populates="rejected_users"
    )
    rejected_users: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys=[rejected_by],
        back_populates="rejecter"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}', is_active={self.is_active})>"
