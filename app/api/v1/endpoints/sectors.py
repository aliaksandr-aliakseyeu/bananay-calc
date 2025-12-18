"""Sectors endpoints."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.functions import ST_AsGeoJSON, ST_GeomFromGeoJSON
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import Sector
from app.schemas.sector import SectorCreate, SectorResponse, SectorUpdate

router = APIRouter(prefix="/sectors", tags=["Sectors"])


def _row_to_dict(row) -> dict:
    """Convert a database row to a dictionary."""
    boundary_data = json.loads(row.boundary_geojson) if row.boundary_geojson else None
    return {
        "id": row.id,
        "region_id": row.region_id,
        "name": row.name,
        "description": row.description,
        "boundary": boundary_data
    }


async def _get_sector_by_id(
    db: AsyncSession,
    sector_id: int
) -> dict:
    """Get a sector by ID with boundary as GeoJSON."""
    query = select(
        Sector.id,
        Sector.region_id,
        Sector.name,
        Sector.description,
        ST_AsGeoJSON(Sector.boundary).label('boundary_geojson')
    ).where(Sector.id == sector_id)

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sector with id {sector_id} not found"
        )

    return _row_to_dict(row)


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

    return [_row_to_dict(row) for row in rows]


@router.get("/{sector_id}", response_model=SectorResponse)
async def get_sector(
    sector_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Get a single sector by ID.
    """
    return await _get_sector_by_id(db, sector_id)


@router.post("", response_model=SectorResponse, status_code=status.HTTP_201_CREATED)
async def create_sector(
    data: SectorCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Create a new sector.

    **Required fields:**
    - **region_id**: Region ID
    - **boundary**: GeoJSON Polygon with coordinates [[[lng, lat], [lng, lat], ...]]

    **Optional fields:**
    - **name**: Sector name
    - **description**: Sector description
    """
    boundary_geojson = json.dumps(data.boundary.model_dump())

    sector = Sector(
        region_id=data.region_id,
        name=data.name,
        description=data.description,
        boundary=ST_GeomFromGeoJSON(boundary_geojson),
    )

    db.add(sector)
    await db.flush()
    await db.commit()

    return await _get_sector_by_id(db, sector.id)


@router.put("/{sector_id}", response_model=SectorResponse)
async def update_sector(
    sector_id: int,
    data: SectorUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Update a sector.

    All fields are optional - only provided fields will be updated.
    """
    query = select(Sector).where(Sector.id == sector_id)
    result = await db.execute(query)
    sector = result.scalar_one_or_none()

    if not sector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sector with id {sector_id} not found"
        )

    update_data = data.model_dump(exclude_unset=True, exclude={'boundary'})
    for field, value in update_data.items():
        setattr(sector, field, value)

    if data.boundary is not None:
        boundary_geojson = json.dumps(data.boundary.model_dump())
        sector.boundary = ST_GeomFromGeoJSON(boundary_geojson)

    await db.commit()

    return await _get_sector_by_id(db, sector_id)


@router.delete("/{sector_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sector(
    sector_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a sector.
    """
    query = select(Sector).where(Sector.id == sector_id)
    result = await db.execute(query)
    sector = result.scalar_one_or_none()

    if not sector:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sector with id {sector_id} not found"
        )

    await db.delete(sector)
    await db.commit()
