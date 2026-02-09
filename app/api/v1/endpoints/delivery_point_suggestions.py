"""Delivery point suggestions endpoints (producer-submitted, pending moderation)."""
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from geoalchemy2.functions import ST_AsGeoJSON, ST_GeomFromGeoJSON
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DeliveryPointSuggestion, Settlement, Tag, User
from app.db.models.delivery_point_suggestion import delivery_point_suggestion_tags
from app.dependencies import get_current_active_producer
from app.schemas.delivery_point_suggestion import (
    DeliveryPointSuggestionCreate,
    DeliveryPointSuggestionListResponse,
    DeliveryPointSuggestionResponse,
)

router = APIRouter(prefix="/delivery-point-suggestions", tags=["Delivery Point Suggestions"])


def _suggestion_row_to_response(row, tag_ids: list[int]) -> dict:
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
        "tag_ids": tag_ids,
        "created_by_id": row.created_by_id,
        "created_at": row.created_at,
    }


@router.post("", response_model=DeliveryPointSuggestionResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_point_suggestion(
    data: DeliveryPointSuggestionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_producer)],
) -> dict:
    """Create a new delivery point suggestion (producer). Pending moderation."""
    settlement_result = await db.execute(
        select(Settlement.id).where(Settlement.id == data.settlement_id)
    )
    if not settlement_result.first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Settlement with id {data.settlement_id} not found",
        )

    if data.tag_ids:
        tag_result = await db.execute(
            select(Tag.id).where(Tag.id.in_(data.tag_ids))
        )
        found_ids = {r[0] for r in tag_result.all()}
        if found_ids != set(data.tag_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more tag IDs are invalid",
            )

    location_geojson = json.dumps(data.location.model_dump())
    suggestion = DeliveryPointSuggestion(
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
        created_by_id=current_user.id,
    )
    db.add(suggestion)
    await db.flush()

    if data.tag_ids:
        for tag_id in data.tag_ids:
            await db.execute(
                delivery_point_suggestion_tags.insert().values(
                    suggestion_id=suggestion.id,
                    tag_id=tag_id,
                )
            )

    await db.commit()
    return await _fetch_suggestion_response(suggestion.id, current_user.id, db)


@router.get("", response_model=DeliveryPointSuggestionListResponse)
async def list_my_delivery_point_suggestions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_producer)],
) -> dict:
    """List delivery point suggestions created by the current producer."""
    query = (
        select(
            DeliveryPointSuggestion.id,
            DeliveryPointSuggestion.name,
            DeliveryPointSuggestion.type,
            DeliveryPointSuggestion.title,
            DeliveryPointSuggestion.settlement_id,
            DeliveryPointSuggestion.district_id,
            DeliveryPointSuggestion.address,
            DeliveryPointSuggestion.address_comment,
            DeliveryPointSuggestion.landmark,
            ST_AsGeoJSON(DeliveryPointSuggestion.location).label("location_geojson"),
            DeliveryPointSuggestion.category_id,
            DeliveryPointSuggestion.subcategory_id,
            DeliveryPointSuggestion.phone,
            DeliveryPointSuggestion.mobile,
            DeliveryPointSuggestion.email,
            DeliveryPointSuggestion.schedule,
            DeliveryPointSuggestion.created_by_id,
            DeliveryPointSuggestion.created_at,
        )
        .where(DeliveryPointSuggestion.created_by_id == current_user.id)
        .order_by(DeliveryPointSuggestion.created_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        tag_result = await db.execute(
            select(delivery_point_suggestion_tags.c.tag_id).where(
                delivery_point_suggestion_tags.c.suggestion_id == row.id
            )
        )
        tag_ids = [t[0] for t in tag_result.all()]
        items.append(_suggestion_row_to_response(row, tag_ids))

    return {"total": len(items), "items": items}


async def _fetch_suggestion_response(
    suggestion_id: int,
    created_by_id: int,
    db: AsyncSession,
) -> dict:
    """Fetch suggestion by id; 404 if not found or not owned by created_by_id."""
    query = (
        select(
            DeliveryPointSuggestion.id,
            DeliveryPointSuggestion.name,
            DeliveryPointSuggestion.type,
            DeliveryPointSuggestion.title,
            DeliveryPointSuggestion.settlement_id,
            DeliveryPointSuggestion.district_id,
            DeliveryPointSuggestion.address,
            DeliveryPointSuggestion.address_comment,
            DeliveryPointSuggestion.landmark,
            ST_AsGeoJSON(DeliveryPointSuggestion.location).label("location_geojson"),
            DeliveryPointSuggestion.category_id,
            DeliveryPointSuggestion.subcategory_id,
            DeliveryPointSuggestion.phone,
            DeliveryPointSuggestion.mobile,
            DeliveryPointSuggestion.email,
            DeliveryPointSuggestion.schedule,
            DeliveryPointSuggestion.created_by_id,
            DeliveryPointSuggestion.created_at,
        )
        .where(DeliveryPointSuggestion.id == suggestion_id)
    )
    result = await db.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery point suggestion with id {suggestion_id} not found",
        )
    if row.created_by_id != created_by_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery point suggestion with id {suggestion_id} not found",
        )
    tag_result = await db.execute(
        select(delivery_point_suggestion_tags.c.tag_id).where(
            delivery_point_suggestion_tags.c.suggestion_id == suggestion_id
        )
    )
    tag_ids = [t[0] for t in tag_result.all()]
    return _suggestion_row_to_response(row, tag_ids)


@router.get("/{suggestion_id}", response_model=DeliveryPointSuggestionResponse)
async def get_my_delivery_point_suggestion(
    suggestion_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_producer)],
) -> dict:
    """Get a single delivery point suggestion by ID (only own suggestions)."""
    return await _fetch_suggestion_response(suggestion_id, current_user.id, db)
