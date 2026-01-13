"""Product category endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import ProductCategory, User
from app.dependencies import get_current_user
from app.schemas.product_category import (
    ProductCategoryCreate,
    ProductCategoryResponse,
    ProductCategoryUpdate,
)
from app.utils.validation import check_unique_fields

router = APIRouter(prefix="/product-categories", tags=["Product Categories"])


@router.get("", response_model=list[ProductCategoryResponse])
async def get_product_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: bool | None = None,
) -> list[ProductCategoryResponse]:
    """Get all product categories."""
    query = select(ProductCategory).order_by(ProductCategory.sort_order, ProductCategory.name)
    if is_active is not None:
        query = query.where(ProductCategory.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{product_category_id}", response_model=ProductCategoryResponse)
async def get_product_category(
    product_category_id: int,
    db: Annotated[AsyncSession, Depends(get_db)]
) -> ProductCategoryResponse:
    """Get a product category by ID."""
    result = await db.execute(
        select(ProductCategory).where(ProductCategory.id == product_category_id)
    )
    db_product_category = result.scalar_one_or_none()
    if not db_product_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")
    return db_product_category


@router.post("", response_model=ProductCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_product_category(
    product_category: ProductCategoryCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProductCategoryResponse:
    """Create a new product category."""
    await check_unique_fields(
        db=db,
        model=ProductCategory,
        fields={
            "name": product_category.name,
            "slug": product_category.slug
        }
    )

    db_product_category = ProductCategory(**product_category.model_dump())
    db.add(db_product_category)
    await db.commit()
    await db.refresh(db_product_category)
    return db_product_category


@router.patch("/{product_category_id}", response_model=ProductCategoryResponse, status_code=status.HTTP_200_OK)
async def update_product_category(
    product_category_id: int,
    product_category: ProductCategoryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ProductCategoryResponse:
    """Update a product category."""
    result = await db.execute(
        select(ProductCategory).where(ProductCategory.id == product_category_id)
    )
    db_product_category = result.scalar_one_or_none()
    if not db_product_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")

    await check_unique_fields(
        db=db,
        model=ProductCategory,
        fields={
            "name": product_category.name,
            "slug": product_category.slug
        },
        exclude_id=product_category_id
    )

    update_data = product_category.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product_category, field, value)
    await db.commit()
    await db.refresh(db_product_category)
    return db_product_category


@router.delete("/{product_category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_category(
    product_category_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Delete a product category."""
    result = await db.execute(
        select(ProductCategory).where(ProductCategory.id == product_category_id)
    )
    db_product_category = result.scalar_one_or_none()
    if not db_product_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product category not found")
    await db.delete(db_product_category)
    await db.commit()
