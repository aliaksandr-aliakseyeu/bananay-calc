from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base
from app.utils.slugify import slugify


class Category(Base):
    """Category (establishment category)."""

    __tablename__ = "geo_categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    subcategories: Mapped[list["Subcategory"]] = relationship(
        "Subcategory", back_populates="category", cascade="all, delete-orphan"
    )

    @validates('slug', 'name')
    def generate_slug(self, key: str, value: str) -> str:
        """Auto-generate slug from name if slug is not specified."""
        if key == 'name':
            if not self.slug:
                self.slug = slugify(value)
            return value
        return value or slugify(self.name) if hasattr(self, 'name') and self.name else value

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Subcategory(Base):
    """Subcategory."""

    __tablename__ = "geo_subcategories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("geo_categories.id"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped["Category"] = relationship("Category", back_populates="subcategories")

    @validates('slug', 'name')
    def generate_slug(self, key: str, value: str) -> str:
        """Auto-generate slug from name if slug is not specified."""
        if key == 'name':
            if not self.slug:
                self.slug = slugify(value)
            return value
        return value or slugify(self.name) if hasattr(self, 'name') and self.name else value

    def __repr__(self) -> str:
        return f"<Subcategory(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class Tag(Base):
    """Tag (category tag)."""

    __tablename__ = "geo_tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    @validates('slug', 'name')
    def generate_slug(self, key: str, value: str) -> str:
        """Auto-generate slug from name if slug is not specified."""
        if key == 'name':
            if not self.slug:
                self.slug = slugify(value)
            return value
        return value or slugify(self.name) if hasattr(self, 'name') and self.name else value

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}', slug='{self.slug}')>"
