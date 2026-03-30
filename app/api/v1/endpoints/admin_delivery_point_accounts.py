"""Admin endpoints for delivery point account management."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.db.models import (DeliveryPoint, DeliveryPointAccount,
                           DeliveryPointAccountPoint, User)
from app.db.models.enums import DeliveryPointAccountStatus
from app.dependencies import get_current_admin

router = APIRouter(
    prefix="/admin/delivery-point-accounts",
    tags=["Admin - Delivery Point Accounts"],
)


async def _resolve_requested_points(db: AsyncSession, point_ids: list[int]) -> list[dict]:
    if not point_ids:
        return []
    points_result = await db.execute(
        select(DeliveryPoint)
        .where(DeliveryPoint.id.in_(point_ids))
        .order_by(DeliveryPoint.id.asc())
    )
    points = points_result.scalars().all()
    return [
        {"id": point.id, "name": point.name, "address": point.address}
        for point in points
    ]


async def _serialize_account(db: AsyncSession, row: DeliveryPointAccount) -> dict:
    requested_points = await _resolve_requested_points(db, row.requested_delivery_point_ids or [])
    linked_ids = {
        link.delivery_point_id
        for link in (row.point_links or [])
        if link.delivery_point_id is not None
    }
    requested_ids = set(row.requested_delivery_point_ids or [])
    has_pending_point_update = bool(requested_ids) and requested_ids != linked_ids
    requested_points_visible = requested_points if has_pending_point_update else []
    requested_ids_visible = (row.requested_delivery_point_ids or []) if has_pending_point_update else []
    return {
        "id": str(row.id),
        "phone_e164": row.phone_e164,
        "status": row.status.value,
        "first_name": row.first_name,
        "last_name": row.last_name,
        "about_text": row.about_text,
        "application_submitted_at": row.application_submitted_at,
        "application_reviewed_at": row.application_reviewed_at,
        "application_reviewed_by": row.application_reviewed_by,
        "application_reject_reason": row.application_reject_reason,
        "requested_delivery_point_ids": requested_ids_visible,
        "requested_points": requested_points_visible,
        "has_pending_point_update": has_pending_point_update,
        "created_at": row.created_at,
        "last_login_at": row.last_login_at,
        "points": [
            {
                "id": link.delivery_point.id,
                "name": link.delivery_point.name,
                "address": link.delivery_point.address,
            }
            for link in (row.point_links or [])
            if link.delivery_point is not None
        ],
    }


@router.get("")
async def list_delivery_point_accounts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    status_filter: DeliveryPointAccountStatus | None = Query(None, alias="status"),
) -> dict:
    query = select(DeliveryPointAccount).options(
        selectinload(DeliveryPointAccount.point_links).selectinload(
            DeliveryPointAccountPoint.delivery_point
        )
    )
    if status_filter is not None:
        query = query.where(DeliveryPointAccount.status == status_filter)
    query = query.order_by(DeliveryPointAccount.created_at.desc())
    result = await db.execute(query)
    rows = result.scalars().all()
    items: list[dict] = []
    for row in rows:
        items.append(await _serialize_account(db, row))
    return {
        "total": len(rows),
        "items": items,
    }


@router.post("")
async def create_delivery_point_account(
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    phone = (body.get("phone_e164") or "").strip()
    if not phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="phone_e164 is required")
    existing = await db.execute(
        select(DeliveryPointAccount).where(DeliveryPointAccount.phone_e164 == phone)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery point account with this phone already exists",
        )
    row = DeliveryPointAccount(
        phone_e164=phone,
        status=DeliveryPointAccountStatus.ACTIVE,
        first_name=body.get("first_name"),
        last_name=body.get("last_name"),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": str(row.id), "phone_e164": row.phone_e164, "status": row.status.value}


@router.post("/{account_id}/activate")
async def activate_delivery_point_account(
    account_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(select(DeliveryPointAccount).where(DeliveryPointAccount.id == account_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    row.status = DeliveryPointAccountStatus.ACTIVE
    row.blocked_at = None
    row.blocked_reason = None
    row.application_reject_reason = None
    row.application_reviewed_at = datetime.now(timezone.utc)
    row.application_reviewed_by = current_admin.id
    await db.commit()
    return {"id": str(row.id), "status": row.status.value}


@router.post("/{account_id}/block")
async def block_delivery_point_account(
    account_id: str,
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(select(DeliveryPointAccount).where(DeliveryPointAccount.id == account_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    reason = body.get("reason")
    row.status = DeliveryPointAccountStatus.BLOCKED
    row.blocked_at = datetime.now(timezone.utc)
    row.blocked_reason = reason
    await db.commit()
    return {"id": str(row.id), "status": row.status.value, "reason": reason}


@router.post("/{account_id}/assign-points")
async def assign_points(
    account_id: str,
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(select(DeliveryPointAccount).where(DeliveryPointAccount.id == account_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    point_ids: list[int] = body.get("delivery_point_ids") or []
    if point_ids:
        point_result = await db.execute(select(DeliveryPoint.id).where(DeliveryPoint.id.in_(point_ids)))
        existing_ids = set(point_result.scalars().all())
        missing = [pid for pid in point_ids if pid not in existing_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Delivery points not found: {missing}",
            )

    await db.execute(
        delete(DeliveryPointAccountPoint).where(DeliveryPointAccountPoint.account_id == row.id)
    )
    for point_id in point_ids:
        db.add(
            DeliveryPointAccountPoint(
                account_id=row.id,
                delivery_point_id=point_id,
            )
        )

    await db.commit()
    return {"id": str(row.id), "delivery_point_ids": point_ids}


@router.post("/{account_id}/approve-application")
async def approve_application(
    account_id: str,
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(
        select(DeliveryPointAccount)
        .options(selectinload(DeliveryPointAccount.point_links).selectinload(DeliveryPointAccountPoint.delivery_point))
        .where(DeliveryPointAccount.id == account_id)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    linked_ids = {
        link.delivery_point_id
        for link in (row.point_links or [])
        if link.delivery_point_id is not None
    }
    requested_ids = set(row.requested_delivery_point_ids or [])
    has_pending_point_update = bool(requested_ids) and requested_ids != linked_ids
    is_initial_application = row.status == DeliveryPointAccountStatus.PENDING_REVIEW
    if not is_initial_application and not has_pending_point_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending application or tracking list update to approve",
        )

    point_ids: list[int] = body.get("delivery_point_ids") or row.requested_delivery_point_ids or []
    if not point_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No requested points to approve")

    point_result = await db.execute(select(DeliveryPoint.id).where(DeliveryPoint.id.in_(point_ids)))
    existing_ids = set(point_result.scalars().all())
    missing = [pid for pid in point_ids if pid not in existing_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery points not found: {missing}",
        )

    await db.execute(
        delete(DeliveryPointAccountPoint).where(DeliveryPointAccountPoint.account_id == row.id)
    )
    for point_id in point_ids:
        db.add(
            DeliveryPointAccountPoint(
                account_id=row.id,
                delivery_point_id=point_id,
            )
        )

    row.status = DeliveryPointAccountStatus.ACTIVE
    row.requested_delivery_point_ids = []
    row.application_reviewed_at = datetime.now(timezone.utc)
    row.application_reviewed_by = current_admin.id
    row.application_reject_reason = None
    await db.commit()
    await db.refresh(row)
    return {"id": str(row.id), "status": row.status.value, "delivery_point_ids": point_ids}


@router.post("/{account_id}/reject-application")
async def reject_application(
    account_id: str,
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    result = await db.execute(select(DeliveryPointAccount).where(DeliveryPointAccount.id == account_id))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    links_result = await db.execute(
        select(DeliveryPointAccountPoint).where(DeliveryPointAccountPoint.account_id == row.id)
    )
    links = links_result.scalars().all()
    linked_ids = {link.delivery_point_id for link in links if link.delivery_point_id is not None}
    requested_ids = set(row.requested_delivery_point_ids or [])
    has_pending_point_update = bool(requested_ids) and requested_ids != linked_ids
    is_initial_application = row.status == DeliveryPointAccountStatus.PENDING_REVIEW
    if not is_initial_application and not has_pending_point_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending application or tracking list update to reject",
        )

    reason = (body.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reason is required")

    if is_initial_application:
        row.status = DeliveryPointAccountStatus.REJECTED
    else:
        row.status = DeliveryPointAccountStatus.ACTIVE
        row.requested_delivery_point_ids = []
    row.application_reject_reason = reason
    row.application_reviewed_at = datetime.now(timezone.utc)
    row.application_reviewed_by = current_admin.id
    await db.commit()
    return {"id": str(row.id), "status": row.status.value, "reason": reason}
