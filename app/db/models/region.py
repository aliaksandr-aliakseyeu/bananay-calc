from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import RegionType

if TYPE_CHECKING:
    from app.db.models.country import Country
    from app.db.models.distribution_center import DistributionCenter
    from app.db.models.region_pricing import RegionPricing
    from app.db.models.sector import Sector
    from app.db.models.settlement import Settlement


class Region(Base):
    """Region (subject of Russian Federation)."""

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    type: Mapped[RegionType | None] = mapped_column(
        SQLEnum(RegionType, native_enum=False, length=50),
        nullable=True,
        comment="Region type"
    )
    country: Mapped["Country"] = relationship("Country", back_populates="regions")
    settlements: Mapped[list["Settlement"]] = relationship(
        "Settlement", back_populates="region", cascade="all, delete-orphan"
    )
    sectors: Mapped[list["Sector"]] = relationship(
        "Sector", back_populates="region", cascade="all, delete-orphan"
    )
    distribution_centers: Mapped[list["DistributionCenter"]] = relationship(
        "DistributionCenter", back_populates="region", cascade="all, delete-orphan"
    )
    pricing: Mapped["RegionPricing | None"] = relationship(
        "RegionPricing", back_populates="region", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Region(id={self.id}, name='{self.name}', type='{self.type.value if self.type else None}')>"
