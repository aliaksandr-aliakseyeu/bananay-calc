"""Settlements endpoints."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.functions import (
    ST_AsGeoJSON,
    ST_Distance,
    ST_GeomFromGeoJSON,
    ST_MakePoint,
    ST_SetSRID,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DeliveryPoint, Settlement, User
from app.dependencies import get_current_admin
from app.schemas.settlement import (
    SettlementCreate,
    SettlementResponse,
    SettlementSearchResponse,
    SettlementUpdate,
)

router = APIRouter(prefix="/settlements", tags=["Settlements"])


def _row_to_dict(row, region_id: int | None = None) -> dict:
    location_data = json.loads(row.location_geojson) if row.location_geojson else None
    return {
        "id": row.id,
        "region_id": region_id if region_id is not None else row.region_id,
        "name": row.name,
        "type": row.type.value if row.type else None,
        "postal_code": row.postal_code,
        "location": location_data,
    }


def _settlement_select():
    return select(
        Settlement.id,
        Settlement.region_id,
        Settlement.name,
        Settlement.type,
        Settlement.postal_code,
        ST_AsGeoJSON(Settlement.location).label('location_geojson'),
    )


async def _get_settlement_by_id(db: AsyncSession, settlement_id: int) -> dict:
    query = _settlement_select().where(Settlement.id == settlement_id)
    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settlement with id {settlement_id} not found",
        )

    return _row_to_dict(row)


@router.get("", response_model=list[SettlementResponse])
async def get_settlements(
    db: Annotated[AsyncSession, Depends(get_db)],
    region_id: Annotated[int, Query(description="Region ID to filter settlements")],
) -> list[dict]:
    """
    Get all settlements for a region.

    Returns list of settlements for dropdown/selection.
    """
    query = _settlement_select().where(
        Settlement.region_id == region_id
    ).order_by(Settlement.name)

    result = await db.execute(query)
    rows = result.all()

    return [_row_to_dict(row) for row in rows]


@router.get("/find-nearest", response_model=SettlementSearchResponse)
async def find_nearest_settlement(
    db: Annotated[AsyncSession, Depends(get_db)],
    region_id: Annotated[int, Query(description="Region ID")],
    lat: Annotated[float, Query(description="Latitude")],
    lng: Annotated[float, Query(description="Longitude")],
) -> dict:
    """
    Find the nearest settlement to given coordinates.

    Used for auto-detecting settlement when user picks a point on the map.
    Returns the nearest settlement and distance in kilometers.
    """
    point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)

    query = select(
        Settlement.id,
        Settlement.region_id,
        Settlement.name,
        Settlement.type,
        Settlement.postal_code,
        ST_AsGeoJSON(Settlement.location).label('location_geojson'),
        (ST_Distance(Settlement.location, point) * 111).label('distance_km'),
    ).where(
        Settlement.region_id == region_id,
        Settlement.location.isnot(None),
    ).order_by(
        ST_Distance(Settlement.location, point)
    ).limit(1)

    result = await db.execute(query)
    row = result.first()

    if not row:
        return {
            "settlement": None,
            "distance_km": None,
            "auto_detected": False,
        }

    return {
        "settlement": _row_to_dict(row),
        "distance_km": round(row.distance_km, 2) if row.distance_km else None,
        "auto_detected": True,
    }


@router.get("/search", response_model=list[SettlementResponse])
async def search_settlements(
    db: Annotated[AsyncSession, Depends(get_db)],
    region_id: Annotated[int, Query(description="Region ID")],
    q: Annotated[str, Query(min_length=2, description="Search query")],
) -> list[dict]:
    """
    Search settlements by name.

    Used for autocomplete when user types settlement name.
    """
    query = _settlement_select().where(
        Settlement.region_id == region_id,
        Settlement.name.ilike(f"%{q}%"),
    ).order_by(Settlement.name).limit(20)

    result = await db.execute(query)
    rows = result.all()

    return [_row_to_dict(row) for row in rows]


@router.get("/{settlement_id}", response_model=SettlementResponse)
async def get_settlement(
    settlement_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get a single settlement by ID."""
    return await _get_settlement_by_id(db, settlement_id)


@router.post("", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
async def create_settlement(
    data: SettlementCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """
    Create a new settlement.

    **Required fields:**
    - **region_id**: Region ID
    - **name**: Settlement name
    - **location**: GeoJSON Point with coordinates [longitude, latitude]
    """
    location_geojson = json.dumps(data.location.model_dump())

    settlement = Settlement(
        region_id=data.region_id,
        name=data.name,
        type=data.type,
        postal_code=data.postal_code,
        location=ST_GeomFromGeoJSON(location_geojson),
    )

    db.add(settlement)
    await db.flush()
    await db.commit()

    return await _get_settlement_by_id(db, settlement.id)


@router.put("/{settlement_id}", response_model=SettlementResponse)
async def update_settlement(
    settlement_id: int,
    data: SettlementUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """
    Update a settlement.

    All fields are optional - only provided fields will be updated.
    """
    query = select(Settlement).where(Settlement.id == settlement_id)
    result = await db.execute(query)
    settlement = result.scalar_one_or_none()

    if not settlement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settlement with id {settlement_id} not found",
        )

    update_data = data.model_dump(exclude_unset=True, exclude={'location'})
    for field, value in update_data.items():
        setattr(settlement, field, value)

    if data.location is not None:
        location_geojson = json.dumps(data.location.model_dump())
        settlement.location = ST_GeomFromGeoJSON(location_geojson)

    await db.commit()

    return await _get_settlement_by_id(db, settlement_id)


@router.delete("/{settlement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_settlement(
    settlement_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> None:
    """
    Delete a settlement.

    Cannot delete if delivery points are linked to it.
    """
    query = select(Settlement).where(Settlement.id == settlement_id)
    result = await db.execute(query)
    settlement = result.scalar_one_or_none()

    if not settlement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settlement with id {settlement_id} not found",
        )

    points_count_result = await db.execute(
        select(func.count(DeliveryPoint.id)).where(
            DeliveryPoint.settlement_id == settlement_id
        )
    )
    points_count = points_count_result.scalar() or 0

    if points_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete settlement: {points_count} delivery point(s) linked",
        )

    await db.delete(settlement)
    await db.commit()
