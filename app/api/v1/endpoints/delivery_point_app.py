"""Delivery point app endpoints."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.shape import to_shape
from shapely.geometry import Point
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import (CourierAccount, CourierDeliveryTask, DeliveryOrderItem,
                           DeliveryOrderItemPoint, DeliveryPoint, DeliveryPointAccount,
                           DeliveryPointAccountPoint, DeliveryPointStatus,
                           ProducerSKU)
from app.db.models.enums import DeliveryPointAccountStatus
from app.dependencies import (get_current_delivery_point_account,
                              get_current_delivery_point_account_basic)
from app.schemas.delivery_point_app import (DeliveryPointDeliveryItem,
                                            DeliveryPointHistoryResponse,
                                            DeliveryPointLinkedPoint,
                                            DeliveryPointMeResponse,
                                            DeliveryPointSubmitApplicationRequest,
                                            DeliveryPointTrackingListUpsertRequest,
                                            DeliveryPointMeUpdateRequest)
from app.schemas.delivery_list import DeliveryPointInRadiusResponse
from app.schemas.delivery_point import DeliveryPointResponse, GeoJSONPoint
from app.services.delivery_list_service import DeliveryListService

router = APIRouter(prefix="/point", tags=["Delivery Point App"])


def _location_to_geojson(location) -> dict:
    shape: Point = to_shape(location)
    return {
        "type": "Point",
        "coordinates": [shape.x, shape.y],
    }


async def _get_account_point_ids(db: AsyncSession, account_id) -> list[int]:
    result = await db.execute(
        select(DeliveryPointAccountPoint.delivery_point_id).where(
            DeliveryPointAccountPoint.account_id == account_id
        )
    )
    return list(result.scalars().all())


async def _resolve_points(db: AsyncSession, point_ids: list[int]) -> list[DeliveryPointLinkedPoint]:
    if not point_ids:
        return []
    result = await db.execute(
        select(DeliveryPoint)
        .where(DeliveryPoint.id.in_(point_ids))
        .order_by(DeliveryPoint.id.asc())
    )
    points = result.scalars().all()
    return [
        DeliveryPointLinkedPoint(
            id=point.id,
            name=point.name,
            address=point.address,
        )
        for point in points
    ]


async def _map_item_point(
    db: AsyncSession,
    item_point: DeliveryOrderItemPoint,
) -> DeliveryPointDeliveryItem:
    courier_task_result = await db.execute(
        select(CourierDeliveryTask)
        .where(CourierDeliveryTask.item_point_id == item_point.id)
        .order_by(CourierDeliveryTask.created_at.desc())
        .limit(1)
    )
    courier_task = courier_task_result.scalar_one_or_none()
    courier = None
    if courier_task:
        courier_result = await db.execute(
            select(CourierAccount).where(CourierAccount.id == courier_task.courier_id)
        )
        courier = courier_result.scalar_one_or_none()

    order = item_point.order_item.order
    sku: ProducerSKU | None = item_point.order_item.producer_sku
    point = item_point.delivery_point
    return DeliveryPointDeliveryItem(
        item_point_id=item_point.id,
        order_id=order.id,
        order_number=order.order_number,
        order_status=order.status.value if hasattr(order.status, "value") else str(order.status),
        point_status=item_point.status.value
        if hasattr(item_point.status, "value")
        else str(item_point.status),
        delivery_point_id=item_point.delivery_point_id,
        delivery_point_name=point.name if point else None,
        delivery_point_address=point.address if point else None,
        sku_name=sku.name if sku else None,
        quantity=item_point.quantity,
        courier_id=str(courier.id) if courier else None,
        courier_phone=courier.phone_e164 if courier else None,
        courier_name=courier.full_name if courier and hasattr(courier, "full_name") else None,
        delivery_photo_media_id=str(courier_task.delivery_photo_media_id)
        if courier_task and courier_task.delivery_photo_media_id
        else None,
        expected_pickup_date=order.expected_pickup_date,
        delivery_deadline=order.delivery_deadline,
        delivered_at=item_point.delivered_at,
        updated_at=item_point.updated_at,
    )


@router.get("/me", response_model=DeliveryPointMeResponse)
async def get_me(
    account: Annotated[DeliveryPointAccount, Depends(get_current_delivery_point_account_basic)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryPointMeResponse:
    links_result = await db.execute(
        select(DeliveryPointAccountPoint)
        .options(selectinload(DeliveryPointAccountPoint.delivery_point))
        .where(DeliveryPointAccountPoint.account_id == account.id)
        .order_by(DeliveryPointAccountPoint.id.asc())
    )
    links = links_result.scalars().all()
    points = [
        DeliveryPointLinkedPoint(
            id=link.delivery_point.id,
            name=link.delivery_point.name,
            address=link.delivery_point.address,
        )
        for link in links
        if link.delivery_point is not None
    ]
    requested_points = await _resolve_points(db, account.requested_delivery_point_ids or [])
    return DeliveryPointMeResponse(
        id=str(account.id),
        phone_e164=account.phone_e164,
        email=account.email,
        tracking_list_name=account.tracking_list_name,
        tracking_list_description=account.tracking_list_description,
        status=account.status.value,
        first_name=account.first_name,
        last_name=account.last_name,
        about_text=account.about_text,
        application_submitted_at=account.application_submitted_at,
        application_reject_reason=account.application_reject_reason,
        points=points,
        requested_points=requested_points,
    )


@router.patch("/me", response_model=DeliveryPointMeResponse)
async def patch_me(
    body: DeliveryPointMeUpdateRequest,
    account: Annotated[DeliveryPointAccount, Depends(get_current_delivery_point_account_basic)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryPointMeResponse:
    if body.first_name is not None:
        account.first_name = body.first_name.strip() or None
    if body.last_name is not None:
        account.last_name = body.last_name.strip() or None
    if body.email is not None:
        account.email = body.email.strip() or None
    await db.commit()
    return await get_me(account, db)


@router.post("/tracking-list", response_model=DeliveryPointMeResponse)
async def upsert_tracking_list(
    body: DeliveryPointTrackingListUpsertRequest,
    account: Annotated[DeliveryPointAccount, Depends(get_current_delivery_point_account_basic)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryPointMeResponse:
    point_ids = list(dict.fromkeys(body.delivery_point_ids or []))
    if not point_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="delivery_point_ids must contain at least one point",
        )

    point_result = await db.execute(select(DeliveryPoint.id).where(DeliveryPoint.id.in_(point_ids)))
    existing_ids = set(point_result.scalars().all())
    missing_ids = [point_id for point_id in point_ids if point_id not in existing_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery points not found: {missing_ids}",
        )

    account.tracking_list_name = body.name.strip()
    account.tracking_list_description = (body.description or "").strip() or None
    account.requested_delivery_point_ids = point_ids
    await db.commit()
    return await get_me(account, db)


@router.get("/tracking-list/search/in-radius", response_model=list[DeliveryPointInRadiusResponse])
async def find_points_in_radius_for_tracking(
    lat: Annotated[float, Query(description="Latitude", ge=-90, le=90)],
    lon: Annotated[float, Query(description="Longitude", ge=-180, le=180)],
    radius: Annotated[int | None, Query(description="Search radius in meters", ge=1)] = None,
    account: Annotated[DeliveryPointAccount, Depends(get_current_delivery_point_account_basic)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[DeliveryPointInRadiusResponse]:
    points_with_distance = await DeliveryListService.find_points_in_radius(db, lat, lon, radius)
    results: list[DeliveryPointInRadiusResponse] = []
    for delivery_point, distance in points_with_distance:
        location_geojson = _location_to_geojson(delivery_point.location)
        results.append(
            DeliveryPointInRadiusResponse(
                delivery_point=DeliveryPointResponse(
                    id=delivery_point.id,
                    name=delivery_point.name,
                    type=delivery_point.type,
                    title=delivery_point.title,
                    address=delivery_point.address,
                    address_comment=delivery_point.address_comment,
                    landmark=delivery_point.landmark,
                    location=GeoJSONPoint(
                        type=location_geojson["type"],
                        coordinates=location_geojson["coordinates"],
                    ),
                    phone=delivery_point.phone,
                    mobile=delivery_point.mobile,
                    email=delivery_point.email,
                    schedule=delivery_point.schedule,
                    is_active=delivery_point.is_active,
                ),
                distance_meters=round(distance, 2),
            )
        )
    return results


@router.post("/application/submit", response_model=DeliveryPointMeResponse)
async def submit_application(
    body: DeliveryPointSubmitApplicationRequest,
    account: Annotated[DeliveryPointAccount, Depends(get_current_delivery_point_account_basic)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryPointMeResponse:
    if account.status not in {DeliveryPointAccountStatus.DRAFT, DeliveryPointAccountStatus.REJECTED}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application can only be submitted from draft or rejected status",
        )

    point_ids = list(dict.fromkeys(body.delivery_point_ids or []))
    if not point_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="delivery_point_ids must contain at least one point",
        )

    point_result = await db.execute(select(DeliveryPoint.id).where(DeliveryPoint.id.in_(point_ids)))
    existing_ids = set(point_result.scalars().all())
    missing_ids = [point_id for point_id in point_ids if point_id not in existing_ids]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery points not found: {missing_ids}",
        )

    account.about_text = body.about_text.strip()
    account.requested_delivery_point_ids = point_ids
    account.application_submitted_at = datetime.now(timezone.utc)
    account.application_reviewed_at = None
    account.application_reviewed_by = None
    account.application_reject_reason = None
    account.status = DeliveryPointAccountStatus.PENDING_REVIEW
    await db.commit()
    return await get_me(account, db)


@router.get("/deliveries", response_model=list[DeliveryPointDeliveryItem])
async def get_deliveries(
    account: Annotated[DeliveryPointAccount, Depends(get_current_delivery_point_account)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DeliveryPointDeliveryItem]:
    point_ids = await _get_account_point_ids(db, account.id)
    if not point_ids:
        return []

    result = await db.execute(
        select(DeliveryOrderItemPoint)
        .options(
            selectinload(DeliveryOrderItemPoint.delivery_point),
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                DeliveryOrderItem.producer_sku
            ),
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                DeliveryOrderItem.order
            ),
        )
        .where(
            and_(
                DeliveryOrderItemPoint.delivery_point_id.in_(point_ids),
                DeliveryOrderItemPoint.status.notin_(
                    [DeliveryPointStatus.DELIVERED, DeliveryPointStatus.FAILED]
                ),
            )
        )
        .order_by(desc(DeliveryOrderItemPoint.updated_at))
    )
    rows = result.scalars().all()
    return [await _map_item_point(db, row) for row in rows]


@router.get("/deliveries/history", response_model=DeliveryPointHistoryResponse)
async def get_deliveries_history(
    account: Annotated[DeliveryPointAccount, Depends(get_current_delivery_point_account)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> DeliveryPointHistoryResponse:
    point_ids = await _get_account_point_ids(db, account.id)
    if not point_ids:
        return DeliveryPointHistoryResponse(total=0, items=[])

    total = await db.scalar(
        select(func.count())
        .select_from(DeliveryOrderItemPoint)
        .where(
            and_(
                DeliveryOrderItemPoint.delivery_point_id.in_(point_ids),
                DeliveryOrderItemPoint.status.in_(
                    [DeliveryPointStatus.DELIVERED, DeliveryPointStatus.FAILED]
                ),
            )
        )
        .with_only_columns(DeliveryOrderItemPoint.id)
    )

    result = await db.execute(
        select(DeliveryOrderItemPoint)
        .options(
            selectinload(DeliveryOrderItemPoint.delivery_point),
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                DeliveryOrderItem.producer_sku
            ),
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                DeliveryOrderItem.order
            ),
        )
        .where(
            and_(
                DeliveryOrderItemPoint.delivery_point_id.in_(point_ids),
                DeliveryOrderItemPoint.status.in_(
                    [DeliveryPointStatus.DELIVERED, DeliveryPointStatus.FAILED]
                ),
            )
        )
        .order_by(desc(DeliveryOrderItemPoint.delivered_at), desc(DeliveryOrderItemPoint.updated_at))
        .limit(limit)
        .offset(offset)
    )
    rows = result.scalars().all()
    items = [await _map_item_point(db, row) for row in rows]
    return DeliveryPointHistoryResponse(total=len(items) if total is None else total, items=items)


@router.get("/deliveries/{item_point_id}", response_model=DeliveryPointDeliveryItem)
async def get_delivery_by_id(
    item_point_id: int,
    account: Annotated[DeliveryPointAccount, Depends(get_current_delivery_point_account)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryPointDeliveryItem:
    point_ids = await _get_account_point_ids(db, account.id)
    result = await db.execute(
        select(DeliveryOrderItemPoint)
        .options(
            selectinload(DeliveryOrderItemPoint.delivery_point),
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                DeliveryOrderItem.producer_sku
            ),
            selectinload(DeliveryOrderItemPoint.order_item).selectinload(
                DeliveryOrderItem.order
            ),
        )
        .where(
            and_(
                DeliveryOrderItemPoint.id == item_point_id,
                DeliveryOrderItemPoint.delivery_point_id.in_(point_ids),
            )
        )
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery not found")
    return await _map_item_point(db, row)
