from __future__ import annotations

from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.settlement import Settlement


class District(Base):
    """Район населенного пункта (например, район города)."""

    __tablename__ = "geo_districts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    settlement_id: Mapped[int] = mapped_column(
        ForeignKey("geo_settlements.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    boundary: Mapped[str | None] = mapped_column(
        Geometry(geometry_type='POLYGON', srid=4326, spatial_index=True),
        nullable=True,
        comment="Граница района"
    )
    settlement: Mapped["Settlement"] = relationship(
        "Settlement", back_populates="districts"
    )

    def __repr__(self) -> str:
        return f"<District(id={self.id}, name='{self.name}')>"
