"""Regions endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.base import get_db
from app.db.models import DistributionCenter, Region, Sector, Settlement
from app.schemas.region import (RegionDetailResponse, RegionListResponse,
                                RegionPricingResponse, RegionStatsResponse)

router = APIRouter(prefix="/regions", tags=["Regions"])


@router.get("", response_model=list[RegionListResponse])
async def get_regions(
    db: Annotated[AsyncSession, Depends(get_db)],
    country_id: Annotated[int | None, Query(description="Фильтр по ID страны")] = None,
) -> list[Region]:
    """
    Get all regions.

    Возвращает список всех регионов с информацией о стране.

    **Фильтры:**
    - **country_id** (опционально): ID страны для фильтрации регионов
    """
    query = select(Region).options(joinedload(Region.country)).order_by(Region.name)

    if country_id is not None:
        query = query.where(Region.country_id == country_id)

    result = await db.execute(query)
    regions = result.unique().scalars().all()

    return list(regions)


@router.get("/{region_id}", response_model=RegionDetailResponse)
async def get_region(
    region_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Get region by ID with full information.

    Возвращает полную информацию о регионе:
    - Основные данные
    - Страна
    - Распределительные центры
    - Тарифы и параметры расчета (если настроены)
    - Статистика

    **Параметры:**
    - **region_id**: ID региона
    """
    # Get region with relationships
    query = (
        select(Region)
        .options(
            joinedload(Region.country),
            selectinload(Region.distribution_centers),
            joinedload(Region.pricing),
        )
        .where(Region.id == region_id)
    )

    result = await db.execute(query)
    region = result.unique().scalar_one_or_none()

    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region with id {region_id} not found",
        )

    stats = await _get_region_stats(db, region_id)

    pricing_response = None
    if region.pricing:
        pricing_response = RegionPricingResponse.from_pricing_model(region.pricing)

    # Build respose
    return {
        "id": region.id,
        "name": region.name,
        "type": region.type.value if region.type else None,
        "country": region.country,
        "distribution_centers": region.distribution_centers,
        "pricing": pricing_response,
        "stats": stats,
    }


async def _get_region_stats(db: AsyncSession, region_id: int) -> RegionStatsResponse:
    """
    Get region statistics in a single query.

    Uses scalar subqueries to count all related entities in one database round-trip.
    Similar to Django's annotate(Count(...)).
    """
    # Scalar subqueries for each count
    dc_count_subq = (
        select(func.count(DistributionCenter.id))
        .where(DistributionCenter.region_id == region_id)
        .scalar_subquery()
    )

    sectors_count_subq = (
        select(func.count(Sector.id))
        .where(Sector.region_id == region_id)
        .scalar_subquery()
    )

    settlements_count_subq = (
        select(func.count(Settlement.id))
        .where(Settlement.region_id == region_id)
        .scalar_subquery()
    )

    # Single query with all counts as subqueries
    query = select(
        dc_count_subq.label('dc_count'),
        sectors_count_subq.label('sectors_count'),
        settlements_count_subq.label('settlements_count'),
    )

    result = await db.execute(query)
    row = result.one()

    return RegionStatsResponse(
        distribution_centers_count=row.dc_count or 0,
        sectors_count=row.sectors_count or 0,
        settlements_count=row.settlements_count or 0,
    )
