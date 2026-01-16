"""Authentication endpoints."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.base import get_db
from app.db.models import OnboardingStatus, ProducerProfile, User, UserRole
from app.dependencies import get_current_user
from app.schemas.auth import (
    EmailVerificationRequest,
    ProducerRegistration,
    RefreshTokenRequest,
    Token,
    UserResponse,
)
from app.services.email_service import email_service
from app.services.verification_service import verification_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def _authenticate_user(
    username: str,
    password: str,
    db: AsyncSession,
    required_role: UserRole | None = None,
) -> User:
    """Helper function to authenticate user."""
    result = await db.execute(select(User).where(User.email == username))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if required_role and user.role != required_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/login/producer", response_model=Token)
async def login_producer(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Producer login endpoint.

    Authenticate producer with email and password.
    Returns access token and refresh token.

    **Note:** Use email as username in the form.
    **Only for producer accounts.**
    """
    user = await _authenticate_user(
        form_data.username,
        form_data.password,
        db,
        required_role=UserRole.PRODUCER,
    )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login/admin", response_model=Token)
async def login_admin(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Admin login endpoint.

    Authenticate admin with email and password.
    Returns access token and refresh token.

    **Note:** Use email as username in the form.
    **Only for admin accounts.**
    """
    user = await _authenticate_user(
        form_data.username,
        form_data.password,
        db,
        required_role=UserRole.ADMIN,
    )

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """
    Refresh access token.

    Use refresh token to get a new access token.
    """
    try:
        payload = decode_token(refresh_request.refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled",
            )

        access_token = create_access_token(data={"sub": str(user.id)})
        new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate refresh token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """
    Get current user information.

    Returns information about the authenticated user.
    """
    return UserResponse.model_validate(current_user)


@router.post("/register/producer", status_code=status.HTTP_201_CREATED)
async def register_producer(
    registration_data: ProducerRegistration,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Register a new producer (Step 1).

    Creates user account and producer profile with company name.
    Sends email verification link.

    Next steps:
    1. User must verify email
    2. User must complete profile (contact_person, phone)
    3. Wait for admin approval
    """
    result = await db.execute(select(User).where(User.email == registration_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=registration_data.email,
        hashed_password=get_password_hash(registration_data.password),
        role=UserRole.PRODUCER,
        onboarding_status=OnboardingStatus.PENDING_EMAIL_VERIFICATION,
        email_verified=False,
        is_approved=False,
    )

    db.add(user)
    await db.flush()

    producer_profile = ProducerProfile(
        user_id=user.id,
        company_name=registration_data.company_name,
    )

    db.add(producer_profile)
    await db.commit()

    verification_token = verification_service.create_email_verification_token(user.id)

    email_service.send_verification_email(user.email, verification_token)

    return {
        "message": "Registration successful. Please check your email to verify your account.",
        "email": user.email,
    }


@router.post("/verify-email")
async def verify_email(
    verification_request: EmailVerificationRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Verify email address.

    Validates verification token and marks email as verified.
    Updates onboarding status to pending_profile_completion.
    """
    user_id = verification_service.verify_email_verification_token(verification_request.token)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.email_verified:
        return {"message": "Email already verified"}

    user.email_verified = True
    user.email_verified_at = datetime.now(timezone.utc)
    user.onboarding_status = OnboardingStatus.PENDING_PROFILE_COMPLETION

    await db.commit()

    return {
        "message": "Email verified successfully. Please complete your profile.",
    }
