"""Producer endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import get_db
from app.db.models import OnboardingStatus, ProducerProfile, User
from app.dependencies import get_current_user, get_current_verified_producer
from app.schemas.auth import (
    OnboardingStatusResponse,
    ProducerProfileComplete,
    ProducerProfileResponse,
    ProducerProfileUpdate,
)

router = APIRouter(prefix="/producer", tags=["Producer"])


@router.get("/profile/me", response_model=ProducerProfileResponse)
async def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProducerProfileResponse:
    """
    Get current producer's profile.

    Returns producer profile with company information.
    """
    result = await db.execute(
        select(ProducerProfile)
        .where(ProducerProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producer profile not found",
        )

    return ProducerProfileResponse.model_validate(profile)


@router.patch("/profile/me", response_model=ProducerProfileResponse)
async def update_my_profile(
    profile_update: ProducerProfileUpdate,
    current_user: Annotated[User, Depends(get_current_verified_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProducerProfileResponse:
    """
    Update current producer's profile (general edit).

    Can update any profile fields.
    Producer must have verified email.
    """
    result = await db.execute(
        select(ProducerProfile)
        .where(ProducerProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producer profile not found",
        )

    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return ProducerProfileResponse.model_validate(profile)


@router.post("/profile/complete")
async def complete_profile(
    profile_data: ProducerProfileComplete,
    current_user: Annotated[User, Depends(get_current_verified_producer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Complete producer profile (Step 2 of onboarding).

    Required fields:
    - contact_person
    - phone

    After completion, producer is submitted for admin approval.
    Updates onboarding status to pending_approval.
    """
    if current_user.onboarding_status == OnboardingStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already completed and pending approval",
        )

    if current_user.onboarding_status == OnboardingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding already completed",
        )

    result = await db.execute(
        select(ProducerProfile)
        .where(ProducerProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producer profile not found",
        )

    profile.contact_person = profile_data.contact_person
    profile.phone = profile_data.phone

    if profile_data.company_inn:
        profile.company_inn = profile_data.company_inn
    if profile_data.company_address:
        profile.company_address = profile_data.company_address
    if profile_data.description:
        profile.description = profile_data.description
    if profile_data.website:
        profile.website = profile_data.website

    current_user.onboarding_status = OnboardingStatus.PENDING_APPROVAL

    await db.commit()

    return {
        "message": "Profile completed successfully. Your application is now pending admin approval.",
        "onboarding_status": OnboardingStatus.PENDING_APPROVAL.value,
    }


@router.get("/onboarding-status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OnboardingStatusResponse:
    """
    Get current onboarding status.

    Returns detailed information about onboarding progress
    and which fields are required.
    """
    result = await db.execute(
        select(ProducerProfile)
        .where(ProducerProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    profile_completed = False
    required_fields = {
        "contact_person": False,
        "phone": False,
    }

    if profile:
        required_fields["contact_person"] = profile.contact_person is not None
        required_fields["phone"] = profile.phone is not None
        profile_completed = all(required_fields.values())

    return OnboardingStatusResponse(
        onboarding_status=current_user.onboarding_status,
        email_verified=current_user.email_verified,
        profile_completed=profile_completed,
        is_approved=current_user.is_approved,
        required_fields=required_fields,
    )
