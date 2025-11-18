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
    country_id: Annotated[int | None, Query(description="Filter by country ID")] = None,
) -> list[Region]:
    """
    Get all regions.

    Returns list of all regions with country information.

    **Filters:**
    - **country_id** (optional): Country ID for filtering regions
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

    Returns complete information about the region:
    - Basic data
    - Country
    - Distribution centers
    - Pricing and calculation parameters (if configured)
    - Statistics

    **Parameters:**
    - **region_id**: Region ID
    """
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

    Returns all parameters and rates used in the delivery cost calculator
    for this region:
    - Driver rates
    - Transport parameters (fuel consumption, depreciation)
    - DC rates (warehouse handling, service fee)
    - Address delivery cost
    - Standard box parameters
    - Discount parameters

    **Parameters:**
    - **region_id**: Region ID

    **Used for:**
    - Displaying rates to the user
    - Validation before calculation
    - Understanding how delivery cost is formed
    """
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

    Updates calculation parameters for the region. Individual fields can be updated
    without passing all parameters (PATCH semantics).

    **Parameters:**
    - **region_id**: Region ID
    - **pricing_update**: Parameters to update (all fields are optional)

    **Usage examples:**

    1. Update only fuel price:
    ```json
    {
      "fuel_price_per_liter": "75.00"
    }
    ```

    2. Update standard box parameters:
    ```json
    {
      "standard_box": {
        "length": 70,
        "max_weight": "25.00"
      }
    }
    ```

    3. Update discounts:
    ```json
    {
      "discount": {
        "min_points": 250,
        "initial_percent": "7.00"
      }
    }
    ```

    Returns updated calculation parameters.
    """
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

    update_data = pricing_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "standard_box" and value is not None:
            for box_field, box_value in value.items():
                if box_value is not None:
                    setattr(pricing, f"standard_box_{box_field}", box_value)
        elif field == "discount" and value is not None:
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
            setattr(pricing, field, value)

    await db.commit()
    await db.refresh(pricing)

    return RegionPricingResponse.from_pricing_model(pricing)


async def _get_region_stats(db: AsyncSession, region_id: int) -> RegionStatsResponse:
    """
    Get region statistics in a single query.

    Uses scalar subqueries to count all related entities in one database round-trip.
    Similar to Django's annotate(Count(...)).
    """
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
