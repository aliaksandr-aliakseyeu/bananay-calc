"""Countries endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import Country
from app.schemas.country import CountryResponse

router = APIRouter(prefix="/countries", tags=["Countries"])


@router.get("", response_model=list[CountryResponse])
async def get_countries(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[Country]:
    """
    Get all countries.

    Returns list of all countries in the database.
    """
    result = await db.execute(select(Country).order_by(Country.name))
    countries = result.scalars().all()
    return list(countries)


@router.get("/{country_id}", response_model=CountryResponse)
async def get_country(
    country_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> Country:
    """
    Get country by ID.

    - **country_id**: Country ID

    Returns country details or 404 if not found.
    """
    result = await db.execute(
        select(Country).where(Country.id == country_id)
    )
    country = result.scalar_one_or_none()

    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Country with id {country_id} not found"
        )

    return country
