"""Delivery lists endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.shape import to_shape
from shapely.geometry import Point
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.dependencies import get_current_user
from app.schemas.delivery_list import (CheckPointInListResponse,
                                       DeliveryListCreate,
                                       DeliveryListDetailResponse,
                                       DeliveryListItemCreate,
                                       DeliveryListItemResponse,
                                       DeliveryListItemUpdate,
                                       DeliveryListResponse,
                                       DeliveryListUpdate,
                                       DeliveryPointInRadiusResponse,
                                       TogglePointRequest, TogglePointResponse)
from app.schemas.delivery_point import DeliveryPointResponse, GeoJSONPoint
from app.services.delivery_list_service import DeliveryListService

router = APIRouter(prefix="/delivery-lists", tags=["Delivery Lists"])


def location_to_geojson(location) -> dict:
    """Convert WKBElement location to GeoJSON dict."""
    shape: Point = to_shape(location)
    return {
        "type": "Point",
        "coordinates": [shape.x, shape.y]  # longitude, latitude
    }


@router.get("", response_model=list[DeliveryListResponse])
async def get_user_delivery_lists(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DeliveryListResponse]:
    """
    Get all delivery lists for the current user.

    Returns a list of all delivery lists with item counts.
    Lists are sorted by default flag (default first) and creation date.
    """
    lists_with_counts = await DeliveryListService.get_user_lists(db, current_user.id)

    return [
        DeliveryListResponse(
            id=delivery_list.id,
            name=delivery_list.name,
            description=delivery_list.description,
            is_default=delivery_list.is_default,
            items_count=items_count,
            created_at=delivery_list.created_at,
            updated_at=delivery_list.updated_at,
        )
        for delivery_list, items_count in lists_with_counts
    ]


@router.post("", response_model=DeliveryListResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_list(
    data: DeliveryListCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryListResponse:
    """
    Create a new delivery list.

    - **name**: List name (3-100 characters, must be unique per user)
    - **description**: Optional description (max 500 characters)
    - **is_default**: Set as default list (only one can be default)

    **Limits:**
    - Maximum 20 lists per user
    - First list is automatically set as default
    """
    delivery_list = await DeliveryListService.create_list(
        db=db,
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        is_default=data.is_default,
    )

    return DeliveryListResponse(
        id=delivery_list.id,
        name=delivery_list.name,
        description=delivery_list.description,
        is_default=delivery_list.is_default,
        items_count=0,
        created_at=delivery_list.created_at,
        updated_at=delivery_list.updated_at,
    )


@router.get("/{list_id}", response_model=DeliveryListDetailResponse)
async def get_delivery_list(
    list_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryListDetailResponse:
    """
    Get delivery list details with all delivery points.

    Returns detailed information about the list including all items
    with their delivery point data sorted by creation date.
    """
    delivery_list = await DeliveryListService.get_list_by_id(
        db, list_id, current_user.id, with_items=True
    )

    if not delivery_list:
        raise HTTPException(status_code=404, detail="Delivery list not found")

    items_sorted = sorted(delivery_list.items, key=lambda x: x.created_at)

    items = []
    for item in items_sorted:
        location_geojson = location_to_geojson(item.delivery_point.location)

        items.append(
            DeliveryListItemResponse(
                id=item.id,
                custom_name=item.custom_name,
                notes=item.notes,
                created_at=item.created_at,
                delivery_point=DeliveryPointResponse(
                    id=item.delivery_point.id,
                    name=item.delivery_point.name,
                    type=item.delivery_point.type,
                    title=item.delivery_point.title,
                    address=item.delivery_point.address,
                    address_comment=item.delivery_point.address_comment,
                    landmark=item.delivery_point.landmark,
                    location=GeoJSONPoint(
                        type=location_geojson["type"],
                        coordinates=location_geojson["coordinates"]
                    ),
                    phone=item.delivery_point.phone,
                    mobile=item.delivery_point.mobile,
                    email=item.delivery_point.email,
                    schedule=item.delivery_point.schedule,
                    is_active=item.delivery_point.is_active,
                ),
            )
        )

    return DeliveryListDetailResponse(
        id=delivery_list.id,
        name=delivery_list.name,
        description=delivery_list.description,
        is_default=delivery_list.is_default,
        created_at=delivery_list.created_at,
        updated_at=delivery_list.updated_at,
        items=items,
    )


@router.patch("/{list_id}", response_model=DeliveryListResponse)
async def update_delivery_list(
    list_id: int,
    data: DeliveryListUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryListResponse:
    """
    Update delivery list.

    All fields are optional. Only provided fields will be updated.
    """
    delivery_list = await DeliveryListService.get_list_by_id(db, list_id, current_user.id)

    if not delivery_list:
        raise HTTPException(status_code=404, detail="Delivery list not found")

    updated_list = await DeliveryListService.update_list(
        db=db,
        delivery_list=delivery_list,
        name=data.name,
        description=data.description,
        is_default=data.is_default,
    )

    lists_with_counts = await DeliveryListService.get_user_lists(db, current_user.id)
    items_count = next(
        (count for dl, count in lists_with_counts if dl.id == updated_list.id),
        0
    )

    return DeliveryListResponse(
        id=updated_list.id,
        name=updated_list.name,
        description=updated_list.description,
        is_default=updated_list.is_default,
        items_count=items_count,
        created_at=updated_list.created_at,
        updated_at=updated_list.updated_at,
    )


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery_list(
    list_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete delivery list.

    All items in the list will be deleted as well (cascade delete).
    """
    delivery_list = await DeliveryListService.get_list_by_id(db, list_id, current_user.id)

    if not delivery_list:
        raise HTTPException(status_code=404, detail="Delivery list not found")

    await DeliveryListService.delete_list(db, delivery_list)


@router.post("/{list_id}/items", response_model=DeliveryListItemResponse, status_code=status.HTTP_201_CREATED)
async def add_item_to_list(
    list_id: int,
    data: DeliveryListItemCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryListItemResponse:
    """
    Add a delivery point to the list.

    - **delivery_point_id**: ID of the delivery point to add
    - **custom_name**: Optional custom name for this point
    - **notes**: Optional notes (max 1000 characters)

    **Limits:**
    - Maximum 500 points per list
    - Point cannot be added twice to the same list
    """
    delivery_list = await DeliveryListService.get_list_by_id(db, list_id, current_user.id)
    if not delivery_list:
        raise HTTPException(status_code=404, detail="Delivery list not found")

    item = await DeliveryListService.add_point_to_list(
        db=db,
        list_id=list_id,
        delivery_point_id=data.delivery_point_id,
        custom_name=data.custom_name,
        notes=data.notes,
    )

    location_geojson = location_to_geojson(item.delivery_point.location)

    return DeliveryListItemResponse(
        id=item.id,
        custom_name=item.custom_name,
        notes=item.notes,
        created_at=item.created_at,
        delivery_point=DeliveryPointResponse(
            id=item.delivery_point.id,
            name=item.delivery_point.name,
            type=item.delivery_point.type,
            title=item.delivery_point.title,
            address=item.delivery_point.address,
            address_comment=item.delivery_point.address_comment,
            landmark=item.delivery_point.landmark,
            location=GeoJSONPoint(
                type=location_geojson["type"],
                coordinates=location_geojson["coordinates"]
            ),
            phone=item.delivery_point.phone,
            mobile=item.delivery_point.mobile,
            email=item.delivery_point.email,
            schedule=item.delivery_point.schedule,
            is_active=item.delivery_point.is_active,
        ),
    )


@router.patch("/{list_id}/items/{item_id}", response_model=DeliveryListItemResponse)
async def update_list_item(
    list_id: int,
    item_id: int,
    data: DeliveryListItemUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryListItemResponse:
    """
    Update list item (custom name and notes).

    All fields are optional. Only provided fields will be updated.
    """
    delivery_list = await DeliveryListService.get_list_by_id(db, list_id, current_user.id)
    if not delivery_list:
        raise HTTPException(status_code=404, detail="Delivery list not found")

    item = await DeliveryListService.get_item_by_id(db, item_id, list_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    updated_item = await DeliveryListService.update_item(
        db=db,
        item=item,
        custom_name=data.custom_name,
        notes=data.notes,
    )

    location_geojson = location_to_geojson(updated_item.delivery_point.location)

    return DeliveryListItemResponse(
        id=updated_item.id,
        custom_name=updated_item.custom_name,
        notes=updated_item.notes,
        created_at=updated_item.created_at,
        delivery_point=DeliveryPointResponse(
            id=updated_item.delivery_point.id,
            name=updated_item.delivery_point.name,
            type=updated_item.delivery_point.type,
            title=updated_item.delivery_point.title,
            address=updated_item.delivery_point.address,
            address_comment=updated_item.delivery_point.address_comment,
            landmark=updated_item.delivery_point.landmark,
            location=GeoJSONPoint(
                type=location_geojson["type"],
                coordinates=location_geojson["coordinates"]
            ),
            phone=updated_item.delivery_point.phone,
            mobile=updated_item.delivery_point.mobile,
            email=updated_item.delivery_point.email,
            schedule=updated_item.delivery_point.schedule,
            is_active=updated_item.delivery_point.is_active,
        ),
    )


@router.delete("/{list_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_list_item(
    list_id: int,
    item_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Remove a delivery point from the list.
    """
    delivery_list = await DeliveryListService.get_list_by_id(db, list_id, current_user.id)
    if not delivery_list:
        raise HTTPException(status_code=404, detail="Delivery list not found")

    item = await DeliveryListService.get_item_by_id(db, item_id, list_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    await DeliveryListService.delete_item(db, item)


@router.get("/{list_id}/check-point/{delivery_point_id}", response_model=CheckPointInListResponse)
async def check_point_in_list(
    list_id: int,
    delivery_point_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CheckPointInListResponse:
    """
    Check if a delivery point is in the list.

    Useful for UI to show "Add" or "Remove" button.
    """
    delivery_list = await DeliveryListService.get_list_by_id(db, list_id, current_user.id)
    if not delivery_list:
        raise HTTPException(status_code=404, detail="Delivery list not found")

    in_list, item_id = await DeliveryListService.check_point_in_list(
        db, list_id, delivery_point_id
    )

    return CheckPointInListResponse(in_list=in_list, item_id=item_id)


@router.post("/{list_id}/toggle-point", response_model=TogglePointResponse)
async def toggle_point_in_list(
    list_id: int,
    data: TogglePointRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TogglePointResponse:
    """
    Toggle point in list (add if not exists, remove if exists).

    Convenient endpoint for UI - single action that handles both add and remove.
    """
    delivery_list = await DeliveryListService.get_list_by_id(db, list_id, current_user.id)
    if not delivery_list:
        raise HTTPException(status_code=404, detail="Delivery list not found")

    action, item_id = await DeliveryListService.toggle_point(
        db, list_id, data.delivery_point_id
    )

    return TogglePointResponse(action=action, item_id=item_id)


@router.get("/search/in-radius", response_model=list[DeliveryPointInRadiusResponse])
async def find_points_in_radius(
    lat: Annotated[float, Query(description="Latitude", ge=-90, le=90)],
    lon: Annotated[float, Query(description="Longitude", ge=-180, le=180)],
    radius: Annotated[int | None, Query(description="Search radius in meters", ge=1)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> list[DeliveryPointInRadiusResponse]:
    """
    Find delivery points within a radius from coordinates.

    - **lat**: Latitude (required)
    - **lon**: Longitude (required)
    - **radius**: Search radius in meters (optional, default from config: 300m, max: 5000m)

    Returns delivery points sorted by distance (closest first).

    **Usage:**
    1. User enters address in search
    2. Geocoding API returns coordinates
    3. Call this endpoint to find nearby delivery points
    4. Show results to user for selection
    """
    points_with_distance = await DeliveryListService.find_points_in_radius(
        db, lat, lon, radius
    )

    results = []
    for delivery_point, distance in points_with_distance:
        location_geojson = location_to_geojson(delivery_point.location)

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
                        coordinates=location_geojson["coordinates"]
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
