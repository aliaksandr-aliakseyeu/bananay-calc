"""Delivery points endpoints."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.functions import (ST_AsGeoJSON, ST_GeomFromGeoJSON,
                                   ST_MakeEnvelope, ST_Within)
from sqlalchemy import and_, case, delete, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_db
from app.db.models import DeliveryPoint, Sector, Settlement, Tag
from app.db.models.delivery_point import delivery_point_tags
from app.schemas.delivery_point import (DeliveryPointCreate,
                                        DeliveryPointDetailResponse,
                                        DeliveryPointSearchRequest,
                                        DeliveryPointSearchResponse,
                                        DeliveryPointUpdate)
from app.utils import normalize_name

router = APIRouter(prefix="/delivery-points", tags=["Delivery Points"])


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
        normalized_search = normalize_name(filters.search)
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


@router.get("/{delivery_point_id}", response_model=DeliveryPointDetailResponse)
async def get_delivery_point(
    delivery_point_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get a single delivery point by ID."""
    query = select(
        DeliveryPoint.id,
        DeliveryPoint.name,
        DeliveryPoint.type,
        DeliveryPoint.title,
        DeliveryPoint.settlement_id,
        DeliveryPoint.district_id,
        DeliveryPoint.address,
        DeliveryPoint.address_comment,
        DeliveryPoint.landmark,
        ST_AsGeoJSON(DeliveryPoint.location).label('location_geojson'),
        DeliveryPoint.category_id,
        DeliveryPoint.subcategory_id,
        DeliveryPoint.phone,
        DeliveryPoint.mobile,
        DeliveryPoint.email,
        DeliveryPoint.schedule,
        DeliveryPoint.is_active,
    ).where(DeliveryPoint.id == delivery_point_id)

    result = await db.execute(query)
    row = result.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery point with id {delivery_point_id} not found"
        )

    tag_query = select(delivery_point_tags.c.tag_id).where(
        delivery_point_tags.c.delivery_point_id == delivery_point_id
    )
    tag_result = await db.execute(tag_query)
    tag_ids = [t[0] for t in tag_result.all()]

    location_data = json.loads(row.location_geojson)

    return {
        "id": row.id,
        "name": row.name,
        "type": row.type,
        "title": row.title,
        "settlement_id": row.settlement_id,
        "district_id": row.district_id,
        "address": row.address,
        "address_comment": row.address_comment,
        "landmark": row.landmark,
        "location": location_data,
        "category_id": row.category_id,
        "subcategory_id": row.subcategory_id,
        "phone": row.phone,
        "mobile": row.mobile,
        "email": row.email,
        "schedule": row.schedule,
        "is_active": row.is_active,
        "tag_ids": tag_ids,
    }


@router.post("", response_model=DeliveryPointDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_point(
    data: DeliveryPointCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Create a new delivery point."""
    settlement_query = select(Settlement.id).where(Settlement.id == data.settlement_id)
    settlement_result = await db.execute(settlement_query)
    if not settlement_result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Settlement with id {data.settlement_id} not found"
        )

    if data.tag_ids:
        tag_query = select(func.count(Tag.id)).where(Tag.id.in_(data.tag_ids))
        tag_result = await db.execute(tag_query)
        tag_count = tag_result.scalar()
        if tag_count != len(data.tag_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more tag IDs are invalid"
            )

    location_geojson = json.dumps(data.location.model_dump())

    delivery_point = DeliveryPoint(
        settlement_id=data.settlement_id,
        name=data.name,
        type=data.type,
        title=data.title,
        district_id=data.district_id,
        address=data.address,
        address_comment=data.address_comment,
        landmark=data.landmark,
        location=ST_GeomFromGeoJSON(location_geojson),
        category_id=data.category_id,
        subcategory_id=data.subcategory_id,
        phone=data.phone,
        mobile=data.mobile,
        email=data.email,
        schedule=data.schedule,
        is_active=data.is_active,
    )

    db.add(delivery_point)
    await db.flush()

    if data.tag_ids:
        for tag_id in data.tag_ids:
            await db.execute(
                delivery_point_tags.insert().values(
                    delivery_point_id=delivery_point.id,
                    tag_id=tag_id
                )
            )

    await db.commit()

    return await get_delivery_point(delivery_point.id, db)


@router.put("/{delivery_point_id}", response_model=DeliveryPointDetailResponse)
async def update_delivery_point(
    delivery_point_id: int,
    data: DeliveryPointUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Update an existing delivery point."""
    query = select(DeliveryPoint).where(DeliveryPoint.id == delivery_point_id)
    result = await db.execute(query)
    delivery_point = result.scalar_one_or_none()

    if not delivery_point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery point with id {delivery_point_id} not found"
        )

    if data.settlement_id is not None:
        settlement_query = select(Settlement.id).where(Settlement.id == data.settlement_id)
        settlement_result = await db.execute(settlement_query)
        if not settlement_result.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Settlement with id {data.settlement_id} not found"
            )

    if data.tag_ids is not None and data.tag_ids:
        tag_query = select(func.count(Tag.id)).where(Tag.id.in_(data.tag_ids))
        tag_result = await db.execute(tag_query)
        tag_count = tag_result.scalar()
        if tag_count != len(data.tag_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more tag IDs are invalid"
            )

    update_data = data.model_dump(exclude_unset=True, exclude={'tag_ids', 'location'})

    if data.location is not None:
        location_geojson = json.dumps(data.location.model_dump())
        delivery_point.location = ST_GeomFromGeoJSON(location_geojson)

    for field, value in update_data.items():
        setattr(delivery_point, field, value)

    if data.tag_ids is not None:
        await db.execute(
            delete(delivery_point_tags).where(
                delivery_point_tags.c.delivery_point_id == delivery_point_id
            )
        )
        for tag_id in data.tag_ids:
            await db.execute(
                delivery_point_tags.insert().values(
                    delivery_point_id=delivery_point_id,
                    tag_id=tag_id
                )
            )

    await db.commit()

    return await get_delivery_point(delivery_point_id, db)


@router.delete("/{delivery_point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_point(
    delivery_point_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a delivery point."""
    query = select(DeliveryPoint).where(DeliveryPoint.id == delivery_point_id)
    result = await db.execute(query)
    delivery_point = result.scalar_one_or_none()

    if not delivery_point:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery point with id {delivery_point_id} not found"
        )

    await db.execute(
        delete(delivery_point_tags).where(
            delivery_point_tags.c.delivery_point_id == delivery_point_id
        )
    )

    await db.delete(delivery_point)
    await db.commit()
