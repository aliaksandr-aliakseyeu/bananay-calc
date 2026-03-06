"""Courier application (onboarding submit) endpoints."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import CourierAccount, CourierApplication, CourierApplicationStatus
from app.db.models.enums import CourierAccountStatus
from app.dependencies import get_current_courier
from app.schemas.courier import CourierApplicationResponse

from .courier_common import check_can_submit

router = APIRouter()


@router.get("/application", response_model=CourierApplicationResponse | None)
async def get_application(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourierApplicationResponse | None:
    """Get current courier application (if any)."""
    result = await db.execute(
        select(CourierApplication).where(CourierApplication.courier_id == courier.id)
    )
    app = result.scalar_one_or_none()
    if not app:
        return None
    return CourierApplicationResponse.model_validate(app)


@router.post("/application/submit", response_model=CourierApplicationResponse)
async def submit_application(
    courier: Annotated[CourierAccount, Depends(get_current_courier)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourierApplicationResponse:
    """Submit for moderation. Creates/updates CourierApplication, sets status pending_review."""
    await db.refresh(courier, ["vehicles"])
    if courier.status == CourierAccountStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked")
    can_submit, required = await check_can_submit(courier, db)
    if not can_submit:
        missing = [k for k, v in required.items() if not v]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Fill required fields before submit: {', '.join(missing)}",
        )

    result = await db.execute(
        select(CourierApplication).where(CourierApplication.courier_id == courier.id)
    )
    app = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if app:
        if app.status == CourierApplicationStatus.PENDING_REVIEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already submitted for review",
            )
        if app.status == CourierApplicationStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already approved",
            )
        app.status = CourierApplicationStatus.PENDING_REVIEW
        app.submitted_at = now
        app.reject_reason = None
    else:
        app = CourierApplication(
            courier_id=courier.id,
            status=CourierApplicationStatus.PENDING_REVIEW,
            submitted_at=now,
        )
        db.add(app)
        await db.flush()

    courier.status = CourierAccountStatus.PENDING_REVIEW
    await db.commit()
    await db.refresh(app)
    return CourierApplicationResponse.model_validate(app)
