"""Delivery points endpoints."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends
from geoalchemy2.functions import ST_AsGeoJSON, ST_MakeEnvelope, ST_Within
from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DeliveryPoint, Sector, Settlement
from app.db.models.delivery_point import delivery_point_tags
from app.schemas.delivery_point import (DeliveryPointSearchRequest,
                                        DeliveryPointSearchResponse)

router = APIRouter(prefix="/delivery-points", tags=["Delivery Points"])


@router.post("/search", response_model=DeliveryPointSearchResponse)
async def search_delivery_points(
    filters: DeliveryPointSearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Search delivery points with filters.

    Поиск точек доставки с различными фильтрами:
    - **region_id** (обязательно): ID региона
    - **only_in_sectors**: true = только точки внутри секторов, false = все точки
    - **bbox** (опционально): прямоугольник координат для фильтрации

    **Примеры использования:**

    1. Все точки региона:
    ```json
    {"region_id": 1, "only_in_sectors": false}
    ```

    2. Только точки в секторах:
    ```json
    {"region_id": 1, "only_in_sectors": true}
    ```

    3. Точки в bbox:
    ```json
    {
      "region_id": 1,
      "only_in_sectors": false,
      "bbox": {"min_lng": 39.7, "min_lat": 43.5, "max_lng": 39.8, "max_lat": 43.6}
    }
    ```

    4. Точки с определенными тэгами (OR логика):
    ```json
    {
      "region_id": 1,
      "only_in_sectors": false,
      "tag_ids": [1, 2, 3]
    }
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

    query = query.order_by(DeliveryPoint.name)

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
