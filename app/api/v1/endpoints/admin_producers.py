"""Admin endpoints for producer management."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.base import get_db
from app.db.models import OnboardingStatus, ProducerProfile, User, UserRole
from app.dependencies import get_current_admin
from app.schemas.auth import ProducerProfileResponse
from app.services.email_service import email_service

router = APIRouter(prefix="/admin/producers", tags=["Admin - Producers"])


@router.get("/pending")
async def get_pending_producers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """
    Get list of producers pending approval.

    Returns producers with:
    - Email verified
    - Profile completed
    - Status: pending_approval
    """
    result = await db.execute(
        select(User)
        .options(joinedload(User.producer_profile))
        .where(
            User.role == UserRole.PRODUCER,
            User.onboarding_status == OnboardingStatus.PENDING_APPROVAL,
            User.email_verified == True,  # noqa: E712
            User.is_approved == False,  # noqa: E712
            User.is_rejected == False,  # noqa: E712
        )
        .order_by(User.created_at.desc())
    )
    producers = result.unique().scalars().all()

    items = []
    for producer in producers:
        profile = producer.producer_profile if hasattr(producer, 'producer_profile') else None
        items.append({
            "user_id": producer.id,
            "email": producer.email,
            "company_name": profile.company_name if profile else None,
            "company_inn": profile.company_inn if profile else None,
            "contact_person": profile.contact_person if profile else None,
            "phone": profile.phone if profile else None,
            "registered_at": producer.created_at,
            "email_verified": producer.email_verified,
        })

    return {
        "total": len(items),
        "items": items,
    }


@router.get("")
async def get_all_producers(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    is_approved: bool | None = Query(None, description="Filter by approval status"),
    is_rejected: bool | None = Query(None, description="Filter by rejection status"),
    email_verified: bool | None = Query(None, description="Filter by email verification"),
) -> dict:
    """
    Get all producers with filters.

    Admin can filter by approval status, rejection status, and email verification.
    """
    query = (
        select(User)
        .options(joinedload(User.producer_profile))
        .where(User.role == UserRole.PRODUCER)
    )

    if is_approved is not None:
        query = query.where(User.is_approved == is_approved)

    if is_rejected is not None:
        query = query.where(User.is_rejected == is_rejected)

    if email_verified is not None:
        query = query.where(User.email_verified == email_verified)

    query = query.order_by(User.created_at.desc())

    result = await db.execute(query)
    producers = result.unique().scalars().all()

    items = []
    for producer in producers:
        profile = producer.producer_profile if hasattr(producer, 'producer_profile') else None
        items.append({
            "user_id": producer.id,
            "email": producer.email,
            "onboarding_status": producer.onboarding_status.value,
            "email_verified": producer.email_verified,
            "is_approved": producer.is_approved,
            "is_rejected": producer.is_rejected,
            "is_active": producer.is_active,
            "company_name": profile.company_name if profile else None,
            "registered_at": producer.created_at,
        })

    return {
        "total": len(items),
        "items": items,
    }


@router.post("/{user_id}/approve")
async def approve_producer(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """
    Approve producer account.

    Sets:
    - is_approved = True
    - onboarding_status = completed
    - approved_at = now
    - approved_by = admin_id

    Sends approval notification email.
    """
    result = await db.execute(
        select(User)
        .options(joinedload(User.producer_profile))
        .where(User.id == user_id, User.role == UserRole.PRODUCER)
    )
    producer = result.unique().scalar_one_or_none()

    if not producer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producer not found",
        )

    if producer.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Producer already approved",
        )

    if not producer.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Producer email not verified",
        )

    producer.is_approved = True
    producer.approved_at = datetime.now(timezone.utc)
    producer.approved_by = current_admin.id
    producer.onboarding_status = OnboardingStatus.COMPLETED
    producer.is_rejected = False

    await db.commit()

    profile = producer.producer_profile if hasattr(producer, 'producer_profile') else None
    company_name = profile.company_name if profile else "Unknown"
    email_service.send_approval_notification(producer.email, company_name)

    return {
        "message": "Producer approved successfully",
        "user_id": producer.id,
        "email": producer.email,
    }


@router.post("/{user_id}/reject")
async def reject_producer(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
    reason: str | None = None,
) -> dict:
    """
    Reject producer account.

    Sets:
    - is_rejected = True
    - onboarding_status = rejected
    - rejected_at = now
    - rejected_by = admin_id
    - is_active = False

    Sends rejection notification email with optional reason.
    """
    result = await db.execute(
        select(User)
        .options(joinedload(User.producer_profile))
        .where(User.id == user_id, User.role == UserRole.PRODUCER)
    )
    producer = result.unique().scalar_one_or_none()

    if not producer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producer not found",
        )

    if producer.is_rejected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Producer already rejected",
        )

    producer.is_rejected = True
    producer.rejected_at = datetime.now(timezone.utc)
    producer.rejected_by = current_admin.id
    producer.onboarding_status = OnboardingStatus.REJECTED
    producer.is_active = False
    producer.is_approved = False

    await db.commit()

    profile = producer.producer_profile if hasattr(producer, 'producer_profile') else None
    company_name = profile.company_name if profile else "Unknown"
    email_service.send_rejection_notification(
        producer.email,
        company_name,
        reason or ""
    )

    return {
        "message": "Producer rejected successfully",
        "user_id": producer.id,
        "email": producer.email,
        "reason": reason,
    }


@router.get("/{user_id}")
async def get_producer_detail(
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> dict:
    """
    Get detailed information about a producer.

    Returns full producer information including:
    - User details
    - Profile information
    - Approval/rejection history
    """
    result = await db.execute(
        select(User)
        .options(joinedload(User.producer_profile))
        .where(User.id == user_id, User.role == UserRole.PRODUCER)
    )
    producer = result.unique().scalar_one_or_none()

    if not producer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producer not found",
        )

    profile = producer.producer_profile if hasattr(producer, 'producer_profile') else None

    return {
        "user_id": producer.id,
        "email": producer.email,
        "role": producer.role.value,
        "onboarding_status": producer.onboarding_status.value,
        "email_verified": producer.email_verified,
        "is_approved": producer.is_approved,
        "is_rejected": producer.is_rejected,
        "is_active": producer.is_active,
        "created_at": producer.created_at,
        "updated_at": producer.updated_at,
        "approved_at": producer.approved_at,
        "approved_by": producer.approved_by,
        "rejected_at": producer.rejected_at,
        "rejected_by": producer.rejected_by,
        "profile": {
            "id": profile.id if profile else None,
            "company_name": profile.company_name if profile else None,
            "company_inn": profile.company_inn if profile else None,
            "contact_person": profile.contact_person if profile else None,
            "phone": profile.phone if profile else None,
            "company_address": profile.company_address if profile else None,
            "description": profile.description if profile else None,
            "website": profile.website if profile else None,
            "created_at": profile.created_at if profile else None,
            "updated_at": profile.updated_at if profile else None,
        } if profile else None,
    }


@router.patch("/{user_id}/profile", response_model=ProducerProfileResponse)
async def update_producer_profile_admin(
    user_id: int,
    profile_update: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_admin: Annotated[User, Depends(get_current_admin)],
) -> ProducerProfileResponse:
    """
    Update producer profile (admin).

    Admin can update any profile fields.
    """
    result = await db.execute(
        select(ProducerProfile)
        .where(ProducerProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producer profile not found",
        )

    for field, value in profile_update.items():
        if hasattr(profile, field):
            setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return ProducerProfileResponse.model_validate(profile)
