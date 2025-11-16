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
    region_id: Annotated[int, Query(description="ID региона для фильтрации секторов")],
) -> list[dict]:
    """
    Get all sectors for a region.

    Возвращает список всех секторов доставки для указанного региона
    с границами в формате GeoJSON.

    **Параметры:**
    - **region_id** (обязательно): ID региона для получения его секторов

    **Формат boundary:**
    GeoJSON Polygon с координатами в формате [longitude, latitude]
    """
    # Query sectors with GeoJSON conversion
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

    # Convert to response format
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
