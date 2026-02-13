from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import TutorialStatus, TutorialType

if TYPE_CHECKING:
    from app.db.models.user import User


class ProducerTutorial(Base):
    """Producer tutorial tracking model."""

    __tablename__ = "producer_tutorials"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    producer_id: Mapped[int] = mapped_column(
        ForeignKey("geo_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tutorial_type: Mapped[TutorialType] = mapped_column(
        Enum(TutorialType, native_enum=False, length=50),
        nullable=False,
        index=True
    )
    status: Mapped[TutorialStatus] = mapped_column(
        Enum(TutorialStatus, native_enum=False, length=50),
        nullable=False,
        default=TutorialStatus.NOT_STARTED
    )
    current_step: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    last_shown_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    producer: Mapped["User"] = relationship(
        "User",
        back_populates="tutorials"
    )

    def __repr__(self) -> str:
        return (
            f"<ProducerTutorial(id={self.id}, producer_id={self.producer_id}, "
            f"type='{self.tutorial_type}', status='{self.status}')>"
        )
