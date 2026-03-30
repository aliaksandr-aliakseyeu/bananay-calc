"""FastAPI dependencies."""
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (get_courier_id_from_token, get_dc_id_from_token,
                               get_delivery_point_id_from_token,
                               get_driver_id_from_token, get_user_id_from_token)
from app.db.base import get_db
from app.db.models import (CourierAccount, DcAccount, DeliveryPointAccount,
                           DeliveryPointAccountPoint, DriverAccount, User)
from app.db.models.enums import (CourierAccountStatus, DcAccountStatus,
                                 DeliveryPointAccountStatus,
                                 DriverAccountStatus, OnboardingStatus, UserRole)

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


async def get_current_driver(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverAccount:
    """
    Dependency for driver endpoints. Validates JWT with subject_type=driver and returns DriverAccount.
    """
    driver_id_str = get_driver_id_from_token(token)
    try:
        driver_uuid = uuid.UUID(driver_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(DriverAccount).where(DriverAccount.id == driver_uuid))
    driver = result.scalar_one_or_none()
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Driver not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if driver.status == DriverAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return driver


async def get_current_dc(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcAccount:
    """Dependency for DC endpoints. Validates JWT with subject_type=dc and returns DcAccount."""
    dc_id_str = get_dc_id_from_token(token)
    try:
        dc_uuid = uuid.UUID(dc_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(DcAccount).where(DcAccount.id == dc_uuid))
    dc = result.scalar_one_or_none()
    if dc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="DC account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if dc.status == DcAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return dc


async def get_current_courier(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourierAccount:
    """Dependency for courier endpoints. Validates JWT with subject_type=courier and returns CourierAccount."""
    courier_id_str = get_courier_id_from_token(token)
    try:
        courier_uuid = uuid.UUID(courier_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(CourierAccount).where(CourierAccount.id == courier_uuid))
    courier = result.scalar_one_or_none()
    if courier is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Courier not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if courier.status == CourierAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return courier


async def get_current_delivery_point_account_basic(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryPointAccount:
    """Basic dependency for delivery point app endpoints."""
    point_id_str = get_delivery_point_id_from_token(token)
    try:
        point_uuid = uuid.UUID(point_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(DeliveryPointAccount).where(DeliveryPointAccount.id == point_uuid))
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Delivery point account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if account.status == DeliveryPointAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return account


async def get_current_delivery_point_account(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryPointAccount:
    """Strict dependency for delivery point delivery endpoints."""
    account = await get_current_delivery_point_account_basic(token, db)
    if account.status != DeliveryPointAccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    linked_points_count = await db.scalar(
        select(func.count())
        .select_from(DeliveryPointAccountPoint)
        .where(DeliveryPointAccountPoint.account_id == account.id)
    )
    if (linked_points_count or 0) == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No delivery points assigned to this account",
        )

    return account


async def get_current_courier_from_query(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Query(alias="token", description="Bearer token for SSE (EventSource)")] = None,
) -> CourierAccount:
    """Same as get_current_courier but reads token from query string (for SSE)."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required (query param: token)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    courier_id_str = get_courier_id_from_token(token)
    try:
        courier_uuid = uuid.UUID(courier_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(CourierAccount).where(CourierAccount.id == courier_uuid))
    courier = result.scalar_one_or_none()
    if courier is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Courier not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if courier.status == CourierAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return courier


async def get_current_driver_from_query(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Query(alias="token", description="Bearer token for SSE (EventSource)")] = None,
) -> DriverAccount:
    """
    Same as get_current_driver but reads token from query string.
    Use for SSE endpoint where EventSource cannot send Authorization header.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required (query param: token)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    driver_id_str = get_driver_id_from_token(token)
    try:
        driver_uuid = uuid.UUID(driver_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(DriverAccount).where(DriverAccount.id == driver_uuid))
    driver = result.scalar_one_or_none()
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Driver not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if driver.status == DriverAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is blocked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return driver


async def get_current_user_from_query(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Query(alias="token", description="Bearer token for SSE (EventSource)")] = None,
) -> User:
    """
    Same as get_current_user but reads token from query string.
    Use for SSE endpoint where EventSource cannot send Authorization header.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token required (query param: token)",
            headers={"WWW-Authenticate": "Bearer"},
        )
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
