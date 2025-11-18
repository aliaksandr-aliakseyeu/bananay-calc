"""Delivery points endpoints."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends
from geoalchemy2.functions import ST_AsGeoJSON, ST_MakeEnvelope, ST_Within
from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_db
from app.db.models import DeliveryPoint, Sector, Settlement
from app.db.models.delivery_point import delivery_point_tags
from app.schemas.delivery_point import (DeliveryPointSearchRequest,
                                        DeliveryPointSearchResponse)

router = APIRouter(prefix="/delivery-points", tags=["Delivery Points"])


def normalize_search_query(query: str) -> str:
    """
    Normalize search query same way as database does for name_normalized column.

    Rules:
    - Convert to lowercase
    - Replace ё with е
    - Remove all special characters (keep only letters, numbers, spaces)
    - Collapse multiple spaces into one
    - Trim spaces
    """
    import re

    normalized = query.lower()
    normalized = normalized.replace('ё', 'е')
    normalized = re.sub(r'[^а-яa-z0-9\s]', ' ', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)

    return normalized.strip()


@router.post("/search", response_model=DeliveryPointSearchResponse)
async def search_delivery_points(
    filters: DeliveryPointSearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Search delivery points with filters.

    Search for delivery points with various filters:
    - **region_id** (required): Region ID
    - **only_in_sectors**: true = only points inside sectors, false = all points
    - **search** (optional): search by name (autocomplete, min 3 characters)
    - **bbox** (optional): bounding box of coordinates for filtering
    - **tag_ids** (optional): filter by tags
    - **limit** (optional): maximum number of results (default 10)

    **Usage examples:**

    1. All points in region:
    ```json
    {"region_id": 1, "only_in_sectors": false}
    ```

    2. Search by name:
    ```json
    {"region_id": 1, "search": "mag", "only_in_sectors": false}
    ```

    3. Search with typos (5+ characters):
    ```json
    {"region_id": 1, "search": "manit", "only_in_sectors": false}
    ```
    """
    query = select(
        DeliveryPoint.id,
        DeliveryPoint.name,
        DeliveryPoint.type,
        DeliveryPoint.title,
        DeliveryPoint.address,
        DeliveryPoint.address_comment,
        DeliveryPoint.landmark,
        ST_AsGeoJSON(DeliveryPoint.location).label('location_geojson'),
        DeliveryPoint.phone,
        DeliveryPoint.mobile,
        DeliveryPoint.email,
        DeliveryPoint.schedule,
        DeliveryPoint.is_active,
    ).join(
        Settlement, DeliveryPoint.settlement_id == Settlement.id
    )

    query = query.where(Settlement.region_id == filters.region_id)

    if filters.search:
        normalized_search = normalize_search_query(filters.search)
        search_length = len(normalized_search)

        if search_length < settings.SEARCH_FUZZY_MIN_LENGTH:
            query = query.where(
                or_(
                    DeliveryPoint.name_normalized.like(f'{normalized_search}%'),
                    DeliveryPoint.name_normalized.like(f'% {normalized_search}%')
                )
            )

            query = query.order_by(
                case(
                    (DeliveryPoint.name_normalized.like(f'{normalized_search}%'), 1),
                    else_=2
                ),
                DeliveryPoint.name
            )

        else:
            similarity_score = func.similarity(
                DeliveryPoint.name_normalized,
                normalized_search
            )
            query = query.add_columns(similarity_score.label('similarity'))
            query = query.where(
                or_(
                    DeliveryPoint.name_normalized.like(f'{normalized_search}%'),
                    DeliveryPoint.name_normalized.like(f'% {normalized_search}%'),
                    similarity_score > settings.SEARCH_SIMILARITY_THRESHOLD
                )
            )
            query = query.order_by(
                case(
                    (DeliveryPoint.name_normalized.like(f'{normalized_search}%'), 1),
                    (DeliveryPoint.name_normalized.like(f'% {normalized_search}%'), 2),
                    else_=3
                ),
                similarity_score.desc(),
                func.length(DeliveryPoint.name),
                DeliveryPoint.name
            )

    if filters.only_in_sectors:
        sector_exists = exists(
            select(1)
            .select_from(Sector)
            .where(
                and_(
                    Sector.region_id == filters.region_id,
                    ST_Within(DeliveryPoint.location, Sector.boundary)
                )
            )
        )
        query = query.where(sector_exists)

    if filters.bbox:
        bbox_polygon = ST_MakeEnvelope(
            filters.bbox.min_lng,
            filters.bbox.min_lat,
            filters.bbox.max_lng,
            filters.bbox.max_lat,
            4326  # SRID
        )
        query = query.where(ST_Within(DeliveryPoint.location, bbox_polygon))

    if filters.tag_ids:
        tag_exists = exists(
            select(1)
            .select_from(delivery_point_tags)
            .where(
                and_(
                    delivery_point_tags.c.delivery_point_id == DeliveryPoint.id,
                    delivery_point_tags.c.tag_id.in_(filters.tag_ids)
                )
            )
        )
        query = query.where(tag_exists)

    if not filters.search:
        query = query.order_by(DeliveryPoint.name)
    else:
        result_limit = filters.limit if filters.limit else settings.SEARCH_DEFAULT_LIMIT
        query = query.limit(result_limit)

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        location_data = json.loads(row.location_geojson)
        items.append({
            "id": row.id,
            "name": row.name,
            "type": row.type,
            "title": row.title,
            "address": row.address,
            "address_comment": row.address_comment,
            "landmark": row.landmark,
            "location": location_data,
            "phone": row.phone,
            "mobile": row.mobile,
            "email": row.email,
            "schedule": row.schedule,
            "is_active": row.is_active,
        })

    return {
        "total": len(items),
        "items": items,
    }
