from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.utils.i18n_fields import sync_legacy_text_from_i18n

if TYPE_CHECKING:
    from app.db.models.region import Region


class Country(Base):
    """Country."""

    __tablename__ = "geo_countries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="Legacy display name (synced from English translation)",
    )
    name_i18n: Mapped[dict[str, str]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Localized names (en, ka, ru)",
    )
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, comment="ISO country code")
    regions: Mapped[list["Region"]] = relationship(
        "Region", back_populates="country", cascade="all, delete-orphan"
    )

    def sync_legacy_fields(self) -> None:
        """Keep legacy name column aligned with English translations."""
        self.name = sync_legacy_text_from_i18n(self.name_i18n, fallback=self.name) or self.name

    def __repr__(self) -> str:
        return f"<Country(id={self.id}, name='{self.name}', code='{self.code}')>"


@event.listens_for(Country, "before_insert")
@event.listens_for(Country, "before_update")
def _sync_country_legacy_fields(
    _mapper: object,
    _connection: object,
    target: Country,
) -> None:
    target.sync_legacy_fields()
