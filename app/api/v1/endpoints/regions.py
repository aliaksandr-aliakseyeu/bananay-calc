"""Regions endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.base import get_db
from app.db.models import DistributionCenter, Region, Sector, Settlement
from app.schemas.region import (RegionDetailResponse, RegionListResponse,
                                RegionPricingResponse, RegionPricingUpdate,
                                RegionStatsResponse)

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


@router.get("/{region_id}/pricing", response_model=RegionPricingResponse)
async def get_region_pricing(
    region_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegionPricingResponse:
    """
    Get region pricing parameters for calculator.

    Возвращает все параметры и тарифы, которые используются в калькуляторе
    стоимости доставки для данного региона:
    - Тарифы водителя
    - Параметры транспорта (расход топлива, амортизация)
    - Тарифы РЦ (складская обработка, сервисный сбор)
    - Стоимость адресной доставки
    - Параметры эталонной коробки
    - Параметры скидок

    **Параметры:**
    - **region_id**: ID региона

    **Используется для:**
    - Отображения тарифов пользователю
    - Проверки перед расчетом
    - Понимания как формируется стоимость доставки
    """
    # Get region with pricing
    query = (
        select(Region)
        .options(joinedload(Region.pricing))
        .where(Region.id == region_id)
    )

    result = await db.execute(query)
    region = result.unique().scalar_one_or_none()

    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region with id {region_id} not found",
        )

    if not region.pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing not configured for region {region_id}",
        )

    return RegionPricingResponse.from_pricing_model(region.pricing)


@router.patch("/{region_id}/pricing", response_model=RegionPricingResponse)
async def update_region_pricing(
    region_id: int,
    pricing_update: RegionPricingUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RegionPricingResponse:
    """
    Update region pricing parameters (partial update).

    Обновляет параметры расчета для региона. Можно обновлять отдельные поля,
    не передавая все параметры (PATCH семантика).

    **Параметры:**
    - **region_id**: ID региона
    - **pricing_update**: Параметры для обновления (все поля опциональные)

    **Примеры использования:**

    1. Обновить только цену бензина:
    ```json
    {
      "fuel_price_per_liter": "75.00"
    }
    ```

    2. Обновить параметры эталонной коробки:
    ```json
    {
      "standard_box": {
        "length": 70,
        "max_weight": "25.00"
      }
    }
    ```

    3. Обновить скидки:
    ```json
    {
      "discount": {
        "min_points": 250,
        "initial_percent": "7.00"
      }
    }
    ```

    Возвращает обновленные параметры расчета.
    """
    # Get region with pricing
    query = (
        select(Region)
        .options(joinedload(Region.pricing))
        .where(Region.id == region_id)
    )

    result = await db.execute(query)
    region = result.unique().scalar_one_or_none()

    if not region:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Region with id {region_id} not found",
        )

    if not region.pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing not configured for region {region_id}",
        )

    pricing = region.pricing

    # Update fields (only if provided)
    update_data = pricing_update.model_dump(exclude_unset=True)

    # Update basic fields
    for field, value in update_data.items():
        if field == "standard_box" and value is not None:
            # Update standard box fields
            for box_field, box_value in value.items():
                if box_value is not None:
                    setattr(pricing, f"standard_box_{box_field}", box_value)
        elif field == "discount" and value is not None:
            # Update discount fields
            discount_mapping = {
                "min_points": "min_points_for_discount",
                "step_points": "discount_step_points",
                "initial_percent": "initial_discount_percent",
                "step_percent": "discount_step_percent",
            }
            for disc_field, disc_value in value.items():
                if disc_value is not None:
                    db_field = discount_mapping[disc_field]
                    setattr(pricing, db_field, disc_value)
        elif field not in ["standard_box", "discount"] and value is not None:
            # Update direct fields
            setattr(pricing, field, value)

    # Save changes
    await db.commit()
    await db.refresh(pricing)

    return RegionPricingResponse.from_pricing_model(pricing)


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
