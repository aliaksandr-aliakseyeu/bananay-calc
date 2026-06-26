"""Countries endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import Country
from app.schemas.country import CountryResponse
from app.services.reference_data_serializers import to_country_response

router = APIRouter(prefix="/countries", tags=["Countries"])

SupportedLang = Annotated[
    str,
    Query(
        description="Response language (en, ka, ru). Defaults to English.",
        pattern="^(en|ka|ru)$",
    ),
]


@router.get("", response_model=list[CountryResponse])
async def get_countries(
    db: Annotated[AsyncSession, Depends(get_db)],
    lang: SupportedLang = "en",
) -> list[CountryResponse]:
    """Get all countries."""
    result = await db.execute(select(Country).order_by(Country.name))
    countries = result.scalars().all()
    return [to_country_response(country, lang) for country in countries]


@router.get("/{country_id}", response_model=CountryResponse)
async def get_country(
    country_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    lang: SupportedLang = "en",
) -> CountryResponse:
    """Get country by ID."""
    result = await db.execute(
        select(Country).where(Country.id == country_id)
    )
    country = result.scalar_one_or_none()

    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Country with id {country_id} not found",
        )

    return to_country_response(country, lang)
