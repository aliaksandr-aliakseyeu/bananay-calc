"""Producer SKU endpoints."""
from typing import Annotated

from fastapi import (APIRouter, Depends, File, HTTPException, Query,
                     UploadFile, status)
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import ProducerSKU, ProductCategory, TemperatureMode, User
from app.dependencies import get_current_active_producer
from app.schemas.producer_sku import (ProducerSKUCreate,
                                      ProducerSKUDetailResponse,
                                      ProducerSKUPaginatedResponse,
                                      ProducerSKUUpdate)
from app.services.excel_import_service import (ExcelImportError,
                                               ExcelImportService)
from app.utils.text_utils import normalize_name

router = APIRouter(prefix="/producer/skus", tags=["Producer SKU"])


@router.get("", response_model=ProducerSKUPaginatedResponse)
async def get_producer_skus(
    current_user: Annotated[User, Depends(get_current_active_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: bool | None = Query(None, description="Filter by active status"),
    product_category_id: int | None = Query(None, description="Filter by product category"),
    temperature_mode_id: int | None = Query(None, description="Filter by temperature mode"),
    search: str | None = Query(None, description="Search by name or SKU code"),
    limit: int = Query(50, ge=1, le=100, description="Number of records"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> ProducerSKUPaginatedResponse:
    """
    Get all SKUs for the current producer with pagination.

    Returns paginated response with items, total count, limit and offset.
    """
    from sqlalchemy.orm import selectinload

    base_query = select(ProducerSKU).where(ProducerSKU.producer_id == current_user.id)

    if is_active is not None:
        base_query = base_query.where(ProducerSKU.is_active == is_active)

    if product_category_id is not None:
        base_query = base_query.where(ProducerSKU.product_category_id == product_category_id)

    if temperature_mode_id is not None:
        base_query = base_query.where(ProducerSKU.temperature_mode_id == temperature_mode_id)

    if search:
        search_pattern = f"%{search}%"
        base_query = base_query.where(
            or_(
                ProducerSKU.name.ilike(search_pattern),
                ProducerSKU.sku_code.ilike(search_pattern),
            )
        )

    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0
    items_query = base_query.options(
        selectinload(ProducerSKU.product_category),
        selectinload(ProducerSKU.temperature_mode)
    ).order_by(ProducerSKU.created_at.desc()).limit(limit).offset(offset)

    items_result = await db.execute(items_query)
    skus = items_result.scalars().all()

    return ProducerSKUPaginatedResponse(
        items=[ProducerSKUDetailResponse.model_validate(sku) for sku in skus],
        total=total,
        limit=limit,
        offset=offset,
    )


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


@router.post("/import", response_model=dict)
async def import_skus_from_excel(
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_active_producer)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
) -> dict:
    """
    Import SKUs from Excel file.

    Accepts Excel files in the official template format (Russian or English).
    Returns summary of imported SKUs and any errors.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel files (.xlsx, .xls) are supported",
        )

    try:
        file_content = await file.read()
        skus_data = ExcelImportService.parse_excel(file_content)

        def _candidates_for_lookup(value: str) -> list[str]:
            v = value.strip()
            if not v:
                return []
            before_paren = v.split("(", 1)[0].strip()
            candidates = [normalize_name(v)]
            if before_paren and before_paren != v:
                candidates.append(normalize_name(before_paren))
            seen: set[str] = set()
            out: list[str] = []
            for c in candidates:
                if c and c not in seen:
                    out.append(c)
                    seen.add(c)
            return out

        def _resolve_by_text(value: str, lookup: dict[str, int]) -> int | None:
            for cand in _candidates_for_lookup(value):
                if cand in lookup:
                    return lookup[cand]

            cand_keys = set(_candidates_for_lookup(value))
            matches: set[int] = set()
            for key, _id in lookup.items():
                for cand in cand_keys:
                    if cand and (cand in key or key in cand):
                        matches.add(_id)
            if len(matches) == 1:
                return next(iter(matches))
            return None

        categories = (
            await db.execute(select(ProductCategory).where(ProductCategory.is_active.is_(True)))
        ).scalars().all()
        temperature_modes = (
            await db.execute(select(TemperatureMode).where(TemperatureMode.is_active.is_(True)))
        ).scalars().all()

        category_lookup: dict[str, int] = {}
        category_ids: set[int] = set()
        for c in categories:
            category_ids.add(c.id)
            if c.name:
                for cand in _candidates_for_lookup(c.name):
                    category_lookup[cand] = c.id
            if getattr(c, "slug", None):
                for cand in _candidates_for_lookup(c.slug):
                    category_lookup[cand] = c.id

        temperature_lookup: dict[str, int] = {}
        temperature_ids: set[int] = set()
        for tm in temperature_modes:
            temperature_ids.add(tm.id)
            if tm.name:
                for cand in _candidates_for_lookup(tm.name):
                    temperature_lookup[cand] = tm.id
            if getattr(tm, "slug", None):
                for cand in _candidates_for_lookup(tm.slug):
                    temperature_lookup[cand] = tm.id

        reference_errors: list[dict] = []
        resolved_skus_data: list[dict] = []

        for sku_data in skus_data:
            row_number = sku_data.get("row_number", "unknown")
            sku_code = sku_data.get("sku_code")
            name = sku_data.get("name")

            row_errors: list[str] = []

            raw_category = sku_data.pop("product_category", None)
            if raw_category is not None and str(raw_category).strip() != "":
                raw_str = str(raw_category).strip()
                category_id: int | None = None
                if raw_str.isdigit():
                    category_id = int(raw_str)
                    if category_id not in category_ids:
                        category_id = None
                else:
                    category_id = _resolve_by_text(raw_str, category_lookup)
                if category_id is None:
                    row_errors.append(f"product_category: unknown category '{raw_str}'")
                else:
                    sku_data["product_category_id"] = category_id

            raw_temperature = sku_data.pop("temperature_mode", None)
            if raw_temperature is not None and str(raw_temperature).strip() != "":
                raw_str = str(raw_temperature).strip()
                temperature_id: int | None = None
                if raw_str.isdigit():
                    temperature_id = int(raw_str)
                    if temperature_id not in temperature_ids:
                        temperature_id = None
                else:
                    temperature_id = _resolve_by_text(raw_str, temperature_lookup)
                if temperature_id is None:
                    row_errors.append(f"temperature_mode: unknown mode '{raw_str}'")
                else:
                    sku_data["temperature_mode_id"] = temperature_id

            if row_errors:
                reference_errors.append(
                    {
                        "row": row_number,
                        "sku_code": sku_code,
                        "name": name,
                        "errors": row_errors,
                        "details": "Reference mapping failed",
                    }
                )
                continue

            resolved_skus_data.append(sku_data)

        valid_skus, validation_errors = ExcelImportService.validate_skus(resolved_skus_data)
        validation_errors = reference_errors + validation_errors
        imported_count = 0
        import_errors = []

        for sku_create in valid_skus:
            try:
                if sku_create.sku_code:
                    result = await db.execute(
                        select(ProducerSKU).where(
                            and_(
                                ProducerSKU.producer_id == current_user.id,
                                ProducerSKU.sku_code == sku_create.sku_code,
                            )
                        )
                    )
                    existing_sku = result.scalar_one_or_none()
                    if existing_sku:
                        import_errors.append({
                            "sku_code": sku_create.sku_code,
                            "name": sku_create.name,
                            "error": f"SKU with code '{sku_create.sku_code}' already exists",
                        })
                        continue

                sku = ProducerSKU(
                    producer_id=current_user.id,
                    **sku_create.model_dump(),
                )
                db.add(sku)
                imported_count += 1

            except Exception as e:
                import_errors.append({
                    "sku_code": sku_create.sku_code,
                    "name": sku_create.name,
                    "error": str(e),
                })

        if imported_count > 0:
            await db.commit()

        return {
            "success": True,
            "imported_count": imported_count,
            "total_processed": len(skus_data),
            "validation_errors": validation_errors,
            "import_errors": import_errors,
        }

    except ExcelImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error importing Excel file: {str(e)}",
        )
