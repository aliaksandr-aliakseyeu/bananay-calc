"""Distribution Centers endpoints."""
import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.functions import ST_AsGeoJSON, ST_GeomFromGeoJSON
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DistributionCenter

router = APIRouter(prefix="/distribution-centers", tags=["Distribution Centers"])


# === Pydantic Schemas ===

class GeoJSONPoint(BaseModel):
    """GeoJSON Point geometry."""
    type: str = "Point"
    coordinates: list[float]  # [longitude, latitude]


class DistributionCenterCreate(BaseModel):
    """Schema for creating a distribution center."""
    region_id: int
    name: str
    address: Optional[str] = None
    is_active: bool = True
    location: GeoJSONPoint


class DistributionCenterUpdate(BaseModel):
    """Schema for updating a distribution center."""
    name: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None
    location: Optional[GeoJSONPoint] = None


class DistributionCenterResponse(BaseModel):
    """Schema for distribution center response."""
    id: int
    region_id: int
    name: str
    address: Optional[str] = None
    is_active: bool
    location: Optional[GeoJSONPoint] = None

    class Config:
        from_attributes = True


# === Helper Functions ===

def _row_to_dict(row) -> dict:
    """Convert a database row to a dictionary."""
    location_data = json.loads(row.location_geojson) if row.location_geojson else None
    return {
        "id": row.id,
        "region_id": row.region_id,
        "name": row.name,
        "address": row.address,
        "is_active": row.is_active,
        "location": location_data
    }


async def _get_distribution_center_by_id(
    db: AsyncSession, 
    dc_id: int
) -> DistributionCenterResponse:
    """Get a distribution center by ID with location as GeoJSON."""
    query = select(
        DistributionCenter.id,
        DistributionCenter.region_id,
        DistributionCenter.name,
        DistributionCenter.address,
        DistributionCenter.is_active,
        ST_AsGeoJSON(DistributionCenter.location).label('location_geojson')
    ).where(DistributionCenter.id == dc_id)
    
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution center with id {dc_id} not found"
        )
    
    return _row_to_dict(row)


# === Endpoints ===

@router.get("", response_model=list[DistributionCenterResponse])
async def get_distribution_centers(
    db: Annotated[AsyncSession, Depends(get_db)],
    region_id: Annotated[int, Query(description="Region ID to filter distribution centers")],
    include_inactive: Annotated[bool, Query(description="Include inactive centers")] = False,
) -> list[dict]:
    """
    Get all distribution centers for a region.

    Returns list of all distribution centers for the specified region
    with location in GeoJSON format.

    **Parameters:**
    - **region_id** (required): Region ID to get its distribution centers
    - **include_inactive** (optional): Include inactive distribution centers

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
    ).where(DistributionCenter.region_id == region_id)
    
    if not include_inactive:
        query = query.where(DistributionCenter.is_active == True)  # noqa: E712
    
    query = query.order_by(DistributionCenter.name)

    result = await db.execute(query)
    rows = result.all()

    return [_row_to_dict(row) for row in rows]


@router.get("/{dc_id}", response_model=DistributionCenterResponse)
async def get_distribution_center(
    dc_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Get a single distribution center by ID.
    """
    return await _get_distribution_center_by_id(db, dc_id)


@router.post("", response_model=DistributionCenterResponse, status_code=status.HTTP_201_CREATED)
async def create_distribution_center(
    data: DistributionCenterCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Create a new distribution center.

    **Required fields:**
    - **region_id**: Region ID
    - **name**: Name of the distribution center
    - **location**: GeoJSON Point with coordinates [longitude, latitude]

    **Optional fields:**
    - **address**: Address string
    - **is_active**: Whether the center is active (default: true)
    """
    location_geojson = json.dumps(data.location.model_dump())
    
    distribution_center = DistributionCenter(
        region_id=data.region_id,
        name=data.name,
        address=data.address,
        is_active=data.is_active,
        location=ST_GeomFromGeoJSON(location_geojson),
    )
    
    db.add(distribution_center)
    await db.flush()
    await db.commit()
    
    return await _get_distribution_center_by_id(db, distribution_center.id)


@router.put("/{dc_id}", response_model=DistributionCenterResponse)
async def update_distribution_center(
    dc_id: int,
    data: DistributionCenterUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Update a distribution center.

    All fields are optional - only provided fields will be updated.
    """
    # Get existing distribution center
    query = select(DistributionCenter).where(DistributionCenter.id == dc_id)
    result = await db.execute(query)
    distribution_center = result.scalar_one_or_none()
    
    if not distribution_center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution center with id {dc_id} not found"
        )
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True, exclude={'location'})
    for field, value in update_data.items():
        setattr(distribution_center, field, value)
    
    # Update location if provided
    if data.location is not None:
        location_geojson = json.dumps(data.location.model_dump())
        distribution_center.location = ST_GeomFromGeoJSON(location_geojson)
    
    await db.commit()
    
    return await _get_distribution_center_by_id(db, dc_id)


@router.delete("/{dc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_distribution_center(
    dc_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a distribution center.
    """
    query = select(DistributionCenter).where(DistributionCenter.id == dc_id)
    result = await db.execute(query)
    distribution_center = result.scalar_one_or_none()
    
    if not distribution_center:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Distribution center with id {dc_id} not found"
        )
    
    await db.delete(distribution_center)
    await db.commit()
