from __future__ import annotations

from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import SettlementType

if TYPE_CHECKING:
    from app.db.models.delivery_point import DeliveryPoint
    from app.db.models.district import District
    from app.db.models.region import Region


class Settlement(Base):
    """Населенный пункт."""

    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    type: Mapped[SettlementType | None] = mapped_column(
        SQLEnum(SettlementType, native_enum=False, length=50),
        nullable=True,
        comment="Тип населенного пункта"
    )
    postal_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    location: Mapped[str | None] = mapped_column(
        Geometry(geometry_type='POINT', srid=4326, spatial_index=True),
        nullable=True
    )
    region: Mapped["Region"] = relationship("Region", back_populates="settlements")
    delivery_points: Mapped[list["DeliveryPoint"]] = relationship(
        "DeliveryPoint", back_populates="settlement", cascade="all, delete-orphan"
    )
    districts: Mapped[list["District"]] = relationship(
        "District", back_populates="settlement", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Settlement(id={self.id}, name='{self.name}', type='{self.type.value if self.type else None}')>"
