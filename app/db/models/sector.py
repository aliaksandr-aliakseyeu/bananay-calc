"""Sector model."""
from __future__ import annotations

from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.region import Region


class Sector(Base):
    """Сектор - кастомная область с полигоном координат, привязанная к региону."""

    __tablename__ = "sectors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, index=True,
        comment="Название сектора (опционально, сектора используются в основном для расчетов)"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Описание сектора"
    )

    boundary: Mapped[str] = mapped_column(
        Geometry(geometry_type='POLYGON', srid=4326, spatial_index=True),
        nullable=False,
        comment="Граница сектора (полигон)"
    )

    # Relationships
    region: Mapped["Region"] = relationship(
        "Region", back_populates="sectors"
    )

    def __repr__(self) -> str:
        return f"<Sector(id={self.id}, name='{self.name}', region_id={self.region_id})>"
