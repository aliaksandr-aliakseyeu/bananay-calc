"""Producer SKU endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import ProducerSKU, User
from app.dependencies import get_current_active_producer
from app.schemas.producer_sku import (ProducerSKUCreate,
                                      ProducerSKUDetailResponse,
                                      ProducerSKUUpdate)

router = APIRouter(prefix="/producer/skus", tags=["Producer SKU"])


@router.get("", response_model=list[ProducerSKUDetailResponse])
async def get_producer_skus(
    current_user: Annotated[User, Depends(get_current_active_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: bool | None = Query(None, description="Filter by active status"),
    product_category_id: int | None = Query(None, description="Filter by product category"),
    temperature_mode_id: int | None = Query(None, description="Filter by temperature mode"),
    search: str | None = Query(None, description="Search by name or SKU code"),
    limit: int = Query(50, ge=1, le=100, description="Number of records"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> list[ProducerSKUDetailResponse]:
    """
    Get all SKUs for the current producer.

    Returns a list of SKUs with detailed information including dimensions and items_per_box.
    """
    from sqlalchemy.orm import selectinload

    query = select(ProducerSKU).where(ProducerSKU.producer_id == current_user.id)
    query = query.options(
        selectinload(ProducerSKU.product_category),
        selectinload(ProducerSKU.temperature_mode)
    )

    if is_active is not None:
        query = query.where(ProducerSKU.is_active == is_active)

    if product_category_id is not None:
        query = query.where(ProducerSKU.product_category_id == product_category_id)

    if temperature_mode_id is not None:
        query = query.where(ProducerSKU.temperature_mode_id == temperature_mode_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                ProducerSKU.name.ilike(search_pattern),
                ProducerSKU.sku_code.ilike(search_pattern),
            )
        )

    query = query.order_by(ProducerSKU.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    skus = result.scalars().all()

    return [ProducerSKUDetailResponse.model_validate(sku) for sku in skus]


@router.get("/{sku_id}", response_model=ProducerSKUDetailResponse)
async def get_producer_sku(
    sku_id: int,
    current_user: Annotated[User, Depends(get_current_active_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProducerSKUDetailResponse:
    """
    Get detailed information about a specific SKU.

    Returns full SKU details including relationships.
    """
    result = await db.execute(
        select(ProducerSKU)
        .where(
            and_(
                ProducerSKU.id == sku_id,
                ProducerSKU.producer_id == current_user.id,
            )
        )
    )
    sku = result.scalar_one_or_none()

    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found",
        )

    await db.refresh(sku, ["product_category", "temperature_mode"])

    return ProducerSKUDetailResponse.model_validate(sku)


@router.post("", response_model=ProducerSKUDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_producer_sku(
    data: ProducerSKUCreate,
    current_user: Annotated[User, Depends(get_current_active_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProducerSKUDetailResponse:
    """
    Create a new SKU.

    All calculator parameters are required.
    SKU code must be unique per producer (if provided).
    """
    if data.sku_code:
        result = await db.execute(
            select(ProducerSKU).where(
                and_(
                    ProducerSKU.producer_id == current_user.id,
                    ProducerSKU.sku_code == data.sku_code,
                )
            )
        )
        existing_sku = result.scalar_one_or_none()
        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU with code '{data.sku_code}' already exists",
            )

    sku = ProducerSKU(
        producer_id=current_user.id,
        **data.model_dump(),
    )

    db.add(sku)
    await db.commit()
    await db.refresh(sku, ["product_category", "temperature_mode"])

    return ProducerSKUDetailResponse.model_validate(sku)


@router.patch("/{sku_id}", response_model=ProducerSKUDetailResponse)
async def update_producer_sku(
    sku_id: int,
    data: ProducerSKUUpdate,
    current_user: Annotated[User, Depends(get_current_active_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProducerSKUDetailResponse:
    """
    Update an existing SKU.

    All fields are optional. Only provided fields will be updated.
    SKU code must remain unique per producer (if changed).
    """
    result = await db.execute(
        select(ProducerSKU).where(
            and_(
                ProducerSKU.id == sku_id,
                ProducerSKU.producer_id == current_user.id,
            )
        )
    )
    sku = result.scalar_one_or_none()

    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found",
        )

    update_data = data.model_dump(exclude_unset=True)
    if "sku_code" in update_data and update_data["sku_code"]:
        result = await db.execute(
            select(ProducerSKU).where(
                and_(
                    ProducerSKU.producer_id == current_user.id,
                    ProducerSKU.sku_code == update_data["sku_code"],
                    ProducerSKU.id != sku_id,  # Exclude current SKU
                )
            )
        )
        existing_sku = result.scalar_one_or_none()
        if existing_sku:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SKU with code '{update_data['sku_code']}' already exists",
            )

    for field, value in update_data.items():
        setattr(sku, field, value)

    await db.commit()
    await db.refresh(sku)
    await db.refresh(sku, ["product_category", "temperature_mode"])

    return ProducerSKUDetailResponse.model_validate(sku)


@router.delete("/{sku_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_producer_sku(
    sku_id: int,
    current_user: Annotated[User, Depends(get_current_active_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a SKU.

    Performs soft delete by setting is_active to False.
    """
    result = await db.execute(
        select(ProducerSKU).where(
            and_(
                ProducerSKU.id == sku_id,
                ProducerSKU.producer_id == current_user.id,
            )
        )
    )
    sku = result.scalar_one_or_none()

    if not sku:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU not found",
        )

    sku.is_active = False
    await db.commit()
