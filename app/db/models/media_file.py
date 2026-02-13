from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.enums import MediaFileOwnerType


class MediaFile(Base):
    """Universal file storage (photos, documents) for drivers/applications/shifts."""

    __tablename__ = "media_files"
    __table_args__ = (
        Index("ix_media_files_owner_type_owner_id", "owner_type", "owner_id"),
        Index("ix_media_files_owner_type_owner_id_kind", "owner_type", "owner_id", "kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_type: Mapped[MediaFileOwnerType] = mapped_column(
        Enum(
            MediaFileOwnerType,
            native_enum=False,
            length=50,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    blob_path: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<MediaFile(id={self.id}, owner_type='{self.owner_type}', kind='{self.kind}')>"
