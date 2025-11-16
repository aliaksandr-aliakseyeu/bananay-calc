"""Distribution Center model."""
from __future__ import annotations

from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.region import Region


class DistributionCenter(Base):
    """Распределительный центр (РЦ)."""

    __tablename__ = "distribution_centers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True,
        comment="Название РЦ"
    )

    location: Mapped[str] = mapped_column(
        Geometry(geometry_type='POINT', srid=4326, spatial_index=True),
        nullable=False,
        comment="Координаты РЦ"
    )

    address: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Адрес РЦ"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
        comment="Активен ли РЦ"
    )

    # Relationships
    region: Mapped["Region"] = relationship(
        "Region", back_populates="distribution_centers"
    )

    def __repr__(self) -> str:
        return f"<DistributionCenter(id={self.id}, name='{self.name}', region_id={self.region_id})>"
