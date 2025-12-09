from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.region import Region


class Country(Base):
    """Country."""

    __tablename__ = "geo_countries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, comment="ISO country code")
    regions: Mapped[list["Region"]] = relationship(
        "Region", back_populates="country", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Country(id={self.id}, name='{self.name}', code='{self.code}')>"
