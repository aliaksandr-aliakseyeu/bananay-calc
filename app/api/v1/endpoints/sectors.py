"""Sectors endpoints."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import Sector
from app.schemas.sector import SectorResponse

router = APIRouter(prefix="/sectors", tags=["Sectors"])


@router.get("", response_model=list[SectorResponse])
async def get_sectors(
    db: Annotated[AsyncSession, Depends(get_db)],
    region_id: Annotated[int, Query(description="Region ID to filter sectors")],
) -> list[dict]:
    """
    Get all sectors for a region.

    Returns list of all delivery sectors for the specified region
    with boundaries in GeoJSON format.

    **Parameters:**
    - **region_id** (required): Region ID to get its sectors

    **Boundary format:**
    GeoJSON Polygon with coordinates in [longitude, latitude] format
    """
    query = select(
        Sector.id,
        Sector.region_id,
        Sector.name,
        Sector.description,
        ST_AsGeoJSON(Sector.boundary).label('boundary_geojson')
    ).where(
        Sector.region_id == region_id
    ).order_by(Sector.id)

    result = await db.execute(query)
    rows = result.all()

    sectors = []
    for row in rows:
        boundary_data = json.loads(row.boundary_geojson)
        sectors.append({
            "id": row.id,
            "region_id": row.region_id,
            "name": row.name,
            "description": row.description,
            "boundary": boundary_data
        })

    return sectors
