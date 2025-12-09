"""Product Category model."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.db.base import Base
from app.utils.slugify import slugify


class ProductCategory(Base):
    """Категория товара."""

    __tablename__ = "geo_product_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
        comment="Название категории"
    )
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
        comment="URL-friendly название"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Описание категории"
    )

    cost_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=1.0,
        comment="Множитель стоимости (пока не используется)"
    )

    @validates('slug', 'name')
    def generate_slug(self, key: str, value: str) -> str:
        """Автогенерация slug из name если slug не указан."""
        if key == 'name':
            if not self.slug:
                self.slug = slugify(value)
            return value
        return value or slugify(self.name) if hasattr(self, 'name') and self.name else value

    def __repr__(self) -> str:
        return f"<ProductCategory(id={self.id}, name='{self.name}', slug='{self.slug}')>"
