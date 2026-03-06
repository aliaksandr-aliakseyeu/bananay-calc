"""Courier profile endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import CourierAccount
from app.db.models.enums import CourierAccountStatus
from app.dependencies import get_current_courier
from app.schemas.courier import CourierProfileResponse, CourierProfileUpdate

from .courier_common import REQUIRED_COURIER_DOCUMENT_KINDS, check_can_submit

router = APIRouter()


@router.get("/me", response_model=CourierProfileResponse)
async def get_me(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourierProfileResponse:
    """Get current courier profile and onboarding status."""
    await db.refresh(courier, ["vehicles"])
    can_submit, required = await check_can_submit(courier, db)
    return CourierProfileResponse(
        id=courier.id,
        phone_e164=courier.phone_e164,
        status=courier.status.value,
        full_name=courier.full_name,
        city=courier.city,
        street=courier.street,
        building=courier.building,
        apartment=courier.apartment,
        region_id=courier.region_id,
        payout_account=courier.payout_account,
        created_at=courier.created_at,
        updated_at=courier.updated_at,
        can_submit=can_submit,
        required_fields=required,
        required_document_kinds=sorted(REQUIRED_COURIER_DOCUMENT_KINDS),
    )


@router.patch("/me", response_model=CourierProfileResponse)
async def update_me(
    body: CourierProfileUpdate,
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourierProfileResponse:
    """Update courier profile (only in draft / before submit)."""
    if courier.status not in (CourierAccountStatus.DRAFT, CourierAccountStatus.PENDING_REVIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profile cannot be edited in current status",
        )
    if body.full_name is not None:
        courier.full_name = body.full_name.strip() or None
    if body.city is not None:
        courier.city = body.city.strip() or None
    if body.street is not None:
        courier.street = body.street.strip() or None
    if body.building is not None:
        courier.building = body.building.strip() or None
    if body.apartment is not None:
        courier.apartment = body.apartment.strip() or None
    if body.region_id is not None:
        courier.region_id = body.region_id
    if body.payout_account is not None:
        courier.payout_account = body.payout_account.strip() or None
    await db.commit()
    await db.refresh(courier, ["vehicles"])
    can_submit, required = await check_can_submit(courier, db)
    return CourierProfileResponse(
        id=courier.id,
        phone_e164=courier.phone_e164,
        status=courier.status.value,
        full_name=courier.full_name,
        city=courier.city,
        street=courier.street,
        building=courier.building,
        apartment=courier.apartment,
        region_id=courier.region_id,
        payout_account=courier.payout_account,
        created_at=courier.created_at,
        updated_at=courier.updated_at,
        can_submit=can_submit,
        required_fields=required,
        required_document_kinds=sorted(REQUIRED_COURIER_DOCUMENT_KINDS),
    )
