"""Delivery templates endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import User
from app.dependencies import get_current_user
from app.schemas.common import PaginatedResponse
from app.schemas.delivery_template import (
    DeliveryTemplateCalculateResponse,
    DeliveryTemplateCreate,
    DeliveryTemplateDetailResponse,
    DeliveryTemplatePointCreate,
    DeliveryTemplatePointResponse,
    DeliveryTemplatePointUpdate,
    DeliveryTemplateResponse,
    DeliveryTemplateSyncPointsRequest,
    DeliveryTemplateUpdate,
    DeliveryTemplateUsageHistoryResponse,
)
from app.services.delivery_template_service import DeliveryTemplateService

router = APIRouter(prefix="/delivery-templates", tags=["Delivery Templates"])


@router.get("", response_model=PaginatedResponse[DeliveryTemplateDetailResponse])
async def get_user_templates(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_points: bool = True,
    only_active: bool = True,
    search: str | None = Query(None, description="Search by template name or description"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Items to skip"),
) -> PaginatedResponse[DeliveryTemplateDetailResponse]:
    """
    Get delivery templates for the current user with pagination and search.

    Templates are sorted by last_used_at (most recent first), then by created_at.

    - **include_points**: Include delivery points in response
    - **only_active**: Only return active (non-archived) templates
    - **search**: Filter by name or description (case-insensitive)
    - **limit**: Items per page (1-100)
    - **offset**: Number of items to skip
    """
    total = await DeliveryTemplateService.count_user_templates(
        db, current_user.id, only_active=only_active, search=search
    )
    templates = await DeliveryTemplateService.get_user_templates(
        db,
        current_user.id,
        with_points=include_points,
        only_active=only_active,
        search=search,
        limit=limit,
        offset=offset,
    )

    result = []
    for template in templates:
        template_dict = DeliveryTemplateDetailResponse.model_validate(template).model_dump()

        if include_points and template.points:
            enriched_points = []
            for point in template.points:
                point_dict = DeliveryTemplatePointResponse.model_validate(point).model_dump()
                if point.delivery_point:
                    point_dict['delivery_point_name'] = point.delivery_point.name
                    point_dict['delivery_point_address'] = point.delivery_point.address
                enriched_points.append(point_dict)
            template_dict['points'] = enriched_points

        result.append(DeliveryTemplateDetailResponse.model_validate(template_dict))

    return PaginatedResponse(items=result, total=total)


@router.post("", response_model=DeliveryTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: DeliveryTemplateCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryTemplateResponse:
    """
    Create a new delivery template.

    - **name**: Template name (3-200 characters)
    - **producer_sku_id**: SKU to use in this template
    - **region_id**: Region for delivery
    - **warehouse_lat/lon**: Warehouse coordinates
    - **points**: Initial delivery points (optional, can be added later)
    """
    try:
        template = await DeliveryTemplateService.create_template(
            db=db,
            user_id=current_user.id,
            name=data.name,
            producer_sku_id=data.producer_sku_id,
            region_id=data.region_id,
            warehouse_lat=data.warehouse_lat,
            warehouse_lon=data.warehouse_lon,
            description=data.description,
        )

        if data.points:
            for point_data in data.points:
                await DeliveryTemplateService.add_point_to_template(
                    db=db,
                    template_id=template.id,
                    delivery_point_id=point_data.delivery_point_id,
                    quantity=point_data.quantity,
                    notes=point_data.notes,
                )

            await db.refresh(template)

        return DeliveryTemplateResponse.model_validate(template)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{template_id}", response_model=DeliveryTemplateDetailResponse)
async def get_template(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryTemplateDetailResponse:
    """
    Get template details with all delivery points.

    Returns detailed information about the template including all points.
    """
    template = await DeliveryTemplateService.get_template_by_id(
        db, template_id, current_user.id, with_points=True
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template_dict = DeliveryTemplateDetailResponse.model_validate(template).model_dump()

    if template.points:
        enriched_points = []
        for point in template.points:
            point_dict = DeliveryTemplatePointResponse.model_validate(point).model_dump()
            if point.delivery_point:
                point_dict['delivery_point_name'] = point.delivery_point.name
                point_dict['delivery_point_address'] = point.delivery_point.address
            enriched_points.append(point_dict)
        template_dict['points'] = enriched_points

    return DeliveryTemplateDetailResponse.model_validate(template_dict)


@router.patch("/{template_id}", response_model=DeliveryTemplateResponse)
async def update_template(
    template_id: int,
    data: DeliveryTemplateUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryTemplateResponse:
    """
    Update template.

    All fields are optional. Only provided fields will be updated.
    """
    template = await DeliveryTemplateService.get_template_by_id(
        db, template_id, current_user.id
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    updated_template = await DeliveryTemplateService.update_template(
        db=db,
        template=template,
        name=data.name,
        description=data.description,
        warehouse_lat=data.warehouse_lat,
        warehouse_lon=data.warehouse_lon,
        is_active=data.is_active,
    )

    return DeliveryTemplateResponse.model_validate(updated_template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete (archive) template.

    Template will be marked as inactive but not removed from database.
    This preserves usage history in existing orders.
    """
    template = await DeliveryTemplateService.get_template_by_id(
        db, template_id, current_user.id
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await DeliveryTemplateService.delete_template(db, template)


@router.post("/{template_id}/calculate", response_model=DeliveryTemplateCalculateResponse)
async def calculate_template_cost(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryTemplateCalculateResponse:
    """
    Calculate delivery cost for this template.

    Uses the template's SKU, warehouse location, and delivery points
    to calculate the delivery cost. Result is cached in the template.
    """
    template = await DeliveryTemplateService.get_template_by_id(
        db, template_id, current_user.id, with_points=True
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        result = await DeliveryTemplateService.calculate_template_cost(db, template)
        return DeliveryTemplateCalculateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{template_id}/sync-points", response_model=dict)
async def sync_template_points(
    template_id: int,
    data: DeliveryTemplateSyncPointsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Sync template points in batch (create new or update existing).

    For each point:
    - If the point already exists in template: update quantity
    - If the point doesn't exist: create new

    This is more efficient than multiple individual requests.
    """
    template = await DeliveryTemplateService.get_template_by_id(
        db, template_id, current_user.id
    )

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        points_list = [p.model_dump() for p in data.points]
        processed_count = await DeliveryTemplateService.sync_template_points(
            db, template_id, points_list
        )
        return {
            "success": True,
            "processed_count": processed_count,
            "message": f"Successfully synced {processed_count} points"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{template_id}/usage-history", response_model=DeliveryTemplateUsageHistoryResponse)
async def get_template_usage_history(
    template_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryTemplateUsageHistoryResponse:
    """
    Get usage history for this template.

    Shows which orders used this template and when.
    """
    try:
        result = await DeliveryTemplateService.get_template_usage_history(
            db, template_id, current_user.id
        )
        return DeliveryTemplateUsageHistoryResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{template_id}/points", response_model=DeliveryTemplatePointResponse, status_code=status.HTTP_201_CREATED)
async def add_point_to_template(
    template_id: int,
    data: DeliveryTemplatePointCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryTemplatePointResponse:
    """
    Add a delivery point to template.

    - **delivery_point_id**: ID of the delivery point to add
    - **quantity**: Quantity for this point
    - **notes**: Optional notes
    """
    template = await DeliveryTemplateService.get_template_by_id(
        db, template_id, current_user.id
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    try:
        point = await DeliveryTemplateService.add_point_to_template(
            db=db,
            template_id=template_id,
            delivery_point_id=data.delivery_point_id,
            quantity=data.quantity,
            notes=data.notes,
        )

        return DeliveryTemplatePointResponse.model_validate(point)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{template_id}/points/{point_id}", response_model=DeliveryTemplatePointResponse)
async def update_template_point(
    template_id: int,
    point_id: int,
    data: DeliveryTemplatePointUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryTemplatePointResponse:
    """
    Update a point in template.

    All fields are optional. Only provided fields will be updated.
    """
    template = await DeliveryTemplateService.get_template_by_id(
        db, template_id, current_user.id
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    point = await DeliveryTemplateService.get_template_point_by_id(
        db, point_id, template_id
    )
    if not point:
        raise HTTPException(status_code=404, detail="Point not found")

    updated_point = await DeliveryTemplateService.update_template_point(
        db=db,
        point=point,
        quantity=data.quantity,
        notes=data.notes,
    )

    return DeliveryTemplatePointResponse.model_validate(updated_point)


@router.delete("/{template_id}/points/{point_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template_point(
    template_id: int,
    point_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Remove a delivery point from template.
    """
    template = await DeliveryTemplateService.get_template_by_id(
        db, template_id, current_user.id
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    point = await DeliveryTemplateService.get_template_point_by_id(
        db, point_id, template_id
    )
    if not point:
        raise HTTPException(status_code=404, detail="Point not found")

    await DeliveryTemplateService.delete_template_point(db, point)
