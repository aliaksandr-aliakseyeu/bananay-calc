"""Distribution Centers endpoints."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DistributionCenter

router = APIRouter(prefix="/distribution-centers", tags=["Distribution Centers"])


@router.get("")
async def get_distribution_centers(
    db: Annotated[AsyncSession, Depends(get_db)],
    region_id: Annotated[int, Query(description="Region ID to filter distribution centers")],
) -> list[dict]:
    """
    Get all distribution centers for a region.

    Returns list of all distribution centers for the specified region
    with location in GeoJSON format.

    **Parameters:**
    - **region_id** (required): Region ID to get its distribution centers

    **Location format:**
    GeoJSON Point with coordinates in [longitude, latitude] format
    """
    query = select(
        DistributionCenter.id,
        DistributionCenter.region_id,
        DistributionCenter.name,
        DistributionCenter.address,
        DistributionCenter.is_active,
        ST_AsGeoJSON(DistributionCenter.location).label('location_geojson')
    ).where(
        DistributionCenter.region_id == region_id,
        DistributionCenter.is_active == True  # noqa: E712
    ).order_by(DistributionCenter.name)

    result = await db.execute(query)
    rows = result.all()

    distribution_centers = []
    for row in rows:
        location_data = json.loads(row.location_geojson) if row.location_geojson else None
        distribution_centers.append({
            "id": row.id,
            "region_id": row.region_id,
            "name": row.name,
            "address": row.address,
            "is_active": row.is_active,
            "location": location_data
        })

    return distribution_centers
