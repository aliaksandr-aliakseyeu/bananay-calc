from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, String, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.enums import RegionType
from app.utils.i18n_fields import sync_legacy_text_from_i18n

if TYPE_CHECKING:
    from app.db.models.country import Country
    from app.db.models.distribution_center import DistributionCenter
    from app.db.models.region_pricing import RegionPricing
    from app.db.models.sector import Sector
    from app.db.models.settlement import Settlement


class Region(Base):
    """Geographic region within a country."""

    __tablename__ = "geo_regions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    country_id: Mapped[int] = mapped_column(ForeignKey("geo_countries.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True,
        comment="Legacy display name (synced from English translation)",
    )
    name_i18n: Mapped[dict[str, str]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Localized names (en, ka, ru)",
    )
    type: Mapped[RegionType | None] = mapped_column(
        SQLEnum(RegionType, native_enum=False, length=50),
        nullable=True,
        comment="Region type",
    )
    default_lat: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Default map center latitude",
    )
    default_lng: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Default map center longitude",
    )
    country: Mapped["Country"] = relationship("Country", back_populates="regions")
    settlements: Mapped[list["Settlement"]] = relationship(
        "Settlement", back_populates="region", cascade="all, delete-orphan",
    )
    sectors: Mapped[list["Sector"]] = relationship(
        "Sector", back_populates="region", cascade="all, delete-orphan",
    )
    distribution_centers: Mapped[list["DistributionCenter"]] = relationship(
        "DistributionCenter", back_populates="region", cascade="all, delete-orphan",
    )
    pricing: Mapped["RegionPricing | None"] = relationship(
        "RegionPricing", back_populates="region", uselist=False,
    )

    def sync_legacy_fields(self) -> None:
        """Keep legacy name column aligned with English translations."""
        self.name = sync_legacy_text_from_i18n(self.name_i18n, fallback=self.name) or self.name

    def __repr__(self) -> str:
        return f"<Region(id={self.id}, name='{self.name}', type='{self.type.value if self.type else None}')>"


@event.listens_for(Region, "before_insert")
@event.listens_for(Region, "before_update")
def _sync_region_legacy_fields(
    _mapper: object,
    _connection: object,
    target: Region,
) -> None:
    target.sync_legacy_fields()
