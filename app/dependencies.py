"""FastAPI dependencies."""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_user_id_from_token
from app.db.base import get_db
from app.db.models import User
from app.db.models.enums import OnboardingStatus, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def check_user_role(user: User, allowed_roles: list[UserRole], error_msg: str = "Insufficient permissions") -> None:
    """
    Check if user has one of the allowed roles.

    Args:
        user: User object to check
        allowed_roles: List of allowed roles
        error_msg: Custom error message

    Raises:
        HTTPException: If user role is not in allowed_roles
    """
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_msg,
        )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Dependency to get current authenticated user.

    Validates JWT token and returns User object.
    """
    user_id = get_user_id_from_token(token)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to get current admin user.

    Requires user to have ADMIN role.
    """
    check_user_role(
        current_user,
        [UserRole.ADMIN],
        "Admin access required"
    )
    return current_user


async def get_current_verified_producer(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to get current producer with verified email.

    Can edit profile but not use main service features.

    Requires:
    - User has PRODUCER role
    - Email is verified
    """
    check_user_role(
        current_user,
        [UserRole.PRODUCER],
        "Producer access required"
    )

    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )

    return current_user


async def get_current_active_producer(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to get current active producer with full access.

    Requires:
    - User has PRODUCER role
    - Onboarding completed (email verified, profile filled, approved)
    - Account is active
    """
    check_user_role(
        current_user,
        [UserRole.PRODUCER],
        "Producer access required"
    )

    if current_user.onboarding_status != OnboardingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Onboarding not completed. Current status: {current_user.onboarding_status.value}",
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return current_user
