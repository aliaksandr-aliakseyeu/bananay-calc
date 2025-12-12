"""Settlements endpoints."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_AsGeoJSON, ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import Settlement
from app.schemas.settlement import SettlementResponse, SettlementSearchResponse

router = APIRouter(prefix="/settlements", tags=["Settlements"])


@router.get("", response_model=list[SettlementResponse])
async def get_settlements(
    db: Annotated[AsyncSession, Depends(get_db)],
    region_id: Annotated[int, Query(description="Region ID to filter settlements")],
) -> list[dict]:
    """
    Get all settlements for a region.

    Returns list of settlements for dropdown/selection.
    """
    query = select(
        Settlement.id,
        Settlement.name,
        Settlement.type,
        Settlement.postal_code,
        ST_AsGeoJSON(Settlement.location).label('location_geojson'),
    ).where(
        Settlement.region_id == region_id
    ).order_by(Settlement.name)

    result = await db.execute(query)
    rows = result.all()

    settlements = []
    for row in rows:
        location_data = None
        if row.location_geojson:
            location_data = json.loads(row.location_geojson)

        settlements.append({
            "id": row.id,
            "name": row.name,
            "type": row.type.value if row.type else None,
            "postal_code": row.postal_code,
            "location": location_data,
        })

    return settlements


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
    # Create point from coordinates
    point = ST_SetSRID(ST_MakePoint(lng, lat), 4326)

    # Find nearest settlement with distance
    # ST_Distance returns distance in degrees for geography, we convert to km
    # Using approximate conversion: 1 degree ≈ 111 km
    query = select(
        Settlement.id,
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

    location_data = None
    if row.location_geojson:
        location_data = json.loads(row.location_geojson)

    return {
        "settlement": {
            "id": row.id,
            "name": row.name,
            "type": row.type.value if row.type else None,
            "postal_code": row.postal_code,
            "location": location_data,
        },
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
    query = select(
        Settlement.id,
        Settlement.name,
        Settlement.type,
        Settlement.postal_code,
        ST_AsGeoJSON(Settlement.location).label('location_geojson'),
    ).where(
        Settlement.region_id == region_id,
        Settlement.name.ilike(f"%{q}%"),
    ).order_by(Settlement.name).limit(20)

    result = await db.execute(query)
    rows = result.all()

    settlements = []
    for row in rows:
        location_data = None
        if row.location_geojson:
            location_data = json.loads(row.location_geojson)

        settlements.append({
            "id": row.id,
            "name": row.name,
            "type": row.type.value if row.type else None,
            "postal_code": row.postal_code,
            "location": location_data,
        })

    return settlements
