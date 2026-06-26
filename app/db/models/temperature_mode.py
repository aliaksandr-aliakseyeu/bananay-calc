"""Temperature Mode model."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String, Text, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, validates
from sqlalchemy.types import Integer

from app.db.base import Base
from app.utils.i18n_fields import sync_legacy_text_from_i18n
from app.utils.slugify import slugify


class TemperatureMode(Base):
    """Temperature mode."""

    __tablename__ = "geo_temperature_modes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    name_i18n: Mapped[dict[str, str]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Localized names (en, ka, ru)",
    )
    description_i18n: Mapped[dict[str, str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Localized descriptions (en, ka, ru)",
    )
    cost_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=1.0,
        comment="Множитель стоимости",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    min_temperature: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Минимальная температура",
    )
    max_temperature: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Максимальная температура",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Порядок сортировки",
    )

    @validates("slug", "name")
    def generate_slug(self, key: str, value: str) -> str:
        """Auto-generate slug from name if slug is not specified."""
        if key == "name":
            if not self.slug:
                source = sync_legacy_text_from_i18n(self.name_i18n) if self.name_i18n else value
                self.slug = slugify(source or value)
            return value
        return value or slugify(self.name) if hasattr(self, "name") and self.name else value

    def sync_legacy_fields(self) -> None:
        """Keep legacy columns aligned with English translations."""
        self.name = sync_legacy_text_from_i18n(self.name_i18n, fallback=self.name) or self.name
        if self.description_i18n:
            self.description = sync_legacy_text_from_i18n(
                self.description_i18n,
                fallback=self.description,
            )
        elif self.description_i18n is None:
            self.description = None

    def __repr__(self) -> str:
        return f"<TemperatureMode(id={self.id}, name='{self.name}')>"


@event.listens_for(TemperatureMode, "before_insert")
@event.listens_for(TemperatureMode, "before_update")
def _sync_temperature_mode_legacy_fields(
    _mapper: object,
    _connection: object,
    target: TemperatureMode,
) -> None:
    target.sync_legacy_fields()
