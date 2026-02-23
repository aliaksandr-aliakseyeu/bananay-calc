"""Driver application (onboarding submit) endpoints."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DriverAccount, DriverApplication, DriverApplicationStatus
from app.db.models.enums import DriverAccountStatus
from app.dependencies import get_current_driver
from app.schemas.driver import DriverApplicationResponse

from .driver_common import check_can_submit

router = APIRouter()


@router.get("/application", response_model=DriverApplicationResponse | None)
async def get_application(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverApplicationResponse | None:
    """Get current driver application (if any)."""
    result = await db.execute(
        select(DriverApplication).where(DriverApplication.driver_id == driver.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        return None
    return DriverApplicationResponse.model_validate(app)


@router.post("/application/submit", response_model=DriverApplicationResponse)
async def submit_application(
    driver: Annotated[DriverAccount, Depends(get_current_driver)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverApplicationResponse:
    """Submit for moderation. Creates/updates DriverApplication, sets status pending_review."""
    await db.refresh(driver, ["vehicles"])
    if driver.status == DriverAccountStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked")
    can_submit, required = await check_can_submit(driver, db)
    if not can_submit:
        missing = [k for k, v in required.items() if not v]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fill required fields before submit: {', '.join(missing)}",
        )

    result = await db.execute(
        select(DriverApplication).where(DriverApplication.driver_id == driver.id)
    )
    app = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if app:
        if app.status == DriverApplicationStatus.PENDING_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already submitted for review",
            )
        if app.status == DriverApplicationStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already approved",
            )
        app.status = DriverApplicationStatus.PENDING_REVIEW
        app.submitted_at = now
        app.reject_reason = None
    else:
        app = DriverApplication(
            driver_id=driver.id,
            status=DriverApplicationStatus.PENDING_REVIEW,
            submitted_at=now,
        )
        db.add(app)
        await db.flush()

    driver.status = DriverAccountStatus.PENDING_REVIEW
    await db.commit()
    await db.refresh(app)
    return DriverApplicationResponse.model_validate(app)
