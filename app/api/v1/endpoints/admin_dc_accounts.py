"""Admin endpoints for DC account management."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import DcAccount, DistributionCenter, User
from app.db.models.enums import DcAccountStatus
from app.dependencies import get_current_admin

router = APIRouter(prefix="/admin/dc-accounts", tags=["Admin - DC Accounts"])


@router.get("")
async def list_dc_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    status_filter: DcAccountStatus | None = Query(None, alias="status"),
) -> dict:
    query = (
        select(
            DcAccount,
            DistributionCenter.name.label("distribution_center_name"),
        )
        .outerjoin(DistributionCenter, DistributionCenter.id == DcAccount.distribution_center_id)
    )
    if status_filter is not None:
        query = query.where(DcAccount.status == status_filter)
    query = query.order_by(DcAccount.created_at.desc())
    result = await db.execute(query)
    rows = result.all()
    return {
        "total": len(rows),
        "items": [
            {
                "id": str(account.id),
                "phone_e164": account.phone_e164,
                "status": account.status.value,
                "first_name": account.first_name,
                "last_name": account.last_name,
                "distribution_center_id": account.distribution_center_id,
                "distribution_center_name": distribution_center_name,
                "created_at": account.created_at,
                "last_login_at": account.last_login_at,
            }
            for account, distribution_center_name in rows
        ],
    }


@router.post("")
async def create_dc_account(
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    phone = (body.get("phone_e164") or "").strip()
    if not phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="phone_e164 is required")
    existing_result = await db.execute(select(DcAccount).where(DcAccount.phone_e164 == phone))
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DC account with this phone already exists")
    row = DcAccount(
        phone_e164=phone,
        status=DcAccountStatus.ACTIVE,
        first_name=(body.get("first_name") or None),
        last_name=(body.get("last_name") or None),
        distribution_center_id=body.get("distribution_center_id"),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": str(row.id), "phone_e164": row.phone_e164, "status": row.status.value}


@router.post("/{dc_id}/activate")
async def activate_dc_account(
    dc_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(select(DcAccount).where(DcAccount.id == dc_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DC account not found")
    row.status = DcAccountStatus.ACTIVE
    row.blocked_at = None
    row.blocked_reason = None
    await db.commit()
    return {"id": str(row.id), "status": row.status.value}


@router.post("/{dc_id}/block")
async def block_dc_account(
    dc_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    reason: str | None = None,
) -> dict:
    result = await db.execute(select(DcAccount).where(DcAccount.id == dc_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DC account not found")
    row.status = DcAccountStatus.BLOCKED
    row.blocked_at = datetime.now(timezone.utc)
    row.blocked_reason = reason
    await db.commit()
    return {"id": str(row.id), "status": row.status.value, "reason": reason}


@router.post("/{dc_id}/assign-distribution-center")
async def assign_distribution_center(
    dc_id: str,
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(select(DcAccount).where(DcAccount.id == dc_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DC account not found")

    distribution_center_id = body.get("distribution_center_id")
    if distribution_center_id is not None:
        dc_result = await db.execute(
            select(DistributionCenter).where(DistributionCenter.id == distribution_center_id)
        )
        distribution_center = dc_result.scalar_one_or_none()
        if not distribution_center:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Distribution center not found",
            )
        row.distribution_center_id = distribution_center.id
        distribution_center_name = distribution_center.name
    else:
        row.distribution_center_id = None
        distribution_center_name = None

    await db.commit()
    return {
        "id": str(row.id),
        "status": row.status.value,
        "distribution_center_id": row.distribution_center_id,
        "distribution_center_name": distribution_center_name,
    }
