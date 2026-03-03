"""Driver profile endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DriverAccount
from app.db.models.enums import DriverAccountStatus
from app.dependencies import get_current_driver
from app.schemas.driver import DriverProfileResponse, DriverProfileUpdate

from .driver_common import REQUIRED_DRIVER_DOCUMENT_KINDS, check_can_submit

router = APIRouter()


@router.get("/me", response_model=DriverProfileResponse)
async def get_me(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverProfileResponse:
    """Get current driver profile and onboarding status."""
    await db.refresh(driver, ["vehicles"])
    can_submit, required = await check_can_submit(driver, db)
    return DriverProfileResponse(
        id=driver.id,
        phone_e164=driver.phone_e164,
        status=driver.status.value,
        full_name=driver.full_name,
        city=driver.city,
        street=driver.street,
        building=driver.building,
        apartment=driver.apartment,
        region_id=driver.region_id,
        payout_account=driver.payout_account,
        created_at=driver.created_at,
        updated_at=driver.updated_at,
        can_submit=can_submit,
        required_fields=required,
        required_document_kinds=sorted(REQUIRED_DRIVER_DOCUMENT_KINDS),
    )


@router.patch("/me", response_model=DriverProfileResponse)
async def update_me(
    body: DriverProfileUpdate,
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverProfileResponse:
    """Update driver profile (only in draft / before submit)."""
    if driver.status not in (DriverAccountStatus.DRAFT, DriverAccountStatus.PENDING_REVIEW):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profile cannot be edited in current status",
        )
    if body.full_name is not None:
        driver.full_name = body.full_name.strip() or None
    if body.city is not None:
        driver.city = body.city.strip() or None
    if body.street is not None:
        driver.street = body.street.strip() or None
    if body.building is not None:
        driver.building = body.building.strip() or None
    if body.apartment is not None:
        driver.apartment = body.apartment.strip() or None
    if body.region_id is not None:
        driver.region_id = body.region_id
    if body.payout_account is not None:
        driver.payout_account = body.payout_account.strip() or None
    await db.commit()
    await db.refresh(driver)
    can_submit, required = await check_can_submit(driver, db)
    return DriverProfileResponse(
        id=driver.id,
        phone_e164=driver.phone_e164,
        status=driver.status.value,
        full_name=driver.full_name,
        city=driver.city,
        street=driver.street,
        building=driver.building,
        apartment=driver.apartment,
        region_id=driver.region_id,
        payout_account=driver.payout_account,
        created_at=driver.created_at,
        updated_at=driver.updated_at,
        can_submit=can_submit,
        required_fields=required,
        required_document_kinds=sorted(REQUIRED_DRIVER_DOCUMENT_KINDS),
    )
