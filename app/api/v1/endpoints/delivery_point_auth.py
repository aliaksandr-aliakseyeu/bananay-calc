"""Delivery point auth: request OTP, verify OTP."""
import random
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (create_delivery_point_access_token,
                               create_delivery_point_refresh_token,
                               decode_token)
from app.db.base import get_db
from app.db.models import (DeliveryPointAccount, DeliveryPointAccountStatus,
                           DeliveryPointOtpCode, DeliveryPointOtpStatus)
from app.schemas.auth import (DeliveryPointRequestOtp, DeliveryPointVerifyOtp,
                              DeliveryPointVerifyOtpResponse,
                              RefreshTokenRequest)
from app.services.phone_service import validate_phone_e164
from app.services.telegram_otp_service import send_otp_to_telegram

router = APIRouter(prefix="/auth/delivery-point", tags=["Delivery Point Auth"])

OTP_EXPIRE_MINUTES = 5
OTP_LENGTH = 4


def _generate_otp() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(OTP_LENGTH))


async def _get_or_create_point_account(
    db: AsyncSession,
    phone_e164: str,
) -> tuple[DeliveryPointAccount, bool]:
    result = await db.execute(
        select(DeliveryPointAccount).where(DeliveryPointAccount.phone_e164 == phone_e164)
    )
    account = result.scalar_one_or_none()
    if account:
        account.last_login_at = datetime.now(timezone.utc)
        return account, False

    account = DeliveryPointAccount(
        phone_e164=phone_e164,
        status=DeliveryPointAccountStatus.DRAFT,
    )
    db.add(account)
    await db.flush()
    return account, True


@router.post("/request-otp")
async def request_otp(
    body: DeliveryPointRequestOtp,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Request OTP for delivery point account login."""
    phone_e164 = validate_phone_e164(body.phone_e164)
    code = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    result = await db.execute(
        select(DeliveryPointOtpCode).where(DeliveryPointOtpCode.phone_e164 == phone_e164)
    )
    row = result.scalar_one_or_none()
    if row:
        row.code = code
        row.status = DeliveryPointOtpStatus.PENDING
        row.expires_at = expires_at
        row.used_at = None
    else:
        row = DeliveryPointOtpCode(
            phone_e164=phone_e164,
            code=code,
            status=DeliveryPointOtpStatus.PENDING,
            expires_at=expires_at,
        )
        db.add(row)
    await db.flush()

    sent = await send_otp_to_telegram(db, phone_e164, code)
    await db.commit()

    if sent:
        return {"message": "Код отправлен в Telegram. Проверьте чат."}
    return {"message": "Код сгенерирован (телеграм не привязан)", "debug_code": code}


@router.post("/verify-otp", response_model=DeliveryPointVerifyOtpResponse)
async def verify_otp(
    body: DeliveryPointVerifyOtp,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryPointVerifyOtpResponse:
    """Verify OTP and issue tokens for delivery point account."""
    phone_e164 = validate_phone_e164(body.phone_e164)
    result = await db.execute(
        select(DeliveryPointOtpCode).where(DeliveryPointOtpCode.phone_e164 == phone_e164)
    )
    otp_row = result.scalar_one_or_none()
    if not otp_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP not requested")
    if otp_row.status != DeliveryPointOtpStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP already used")
    if otp_row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OTP expired")
    if otp_row.code != body.code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP code")

    account, is_new_user = await _get_or_create_point_account(db, phone_e164)
    if account.status == DeliveryPointAccountStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked")

    otp_row.status = DeliveryPointOtpStatus.USED
    otp_row.used_at = datetime.now(timezone.utc)
    account.last_login_at = datetime.now(timezone.utc)

    access_token = create_delivery_point_access_token(str(account.id))
    refresh_token = create_delivery_point_refresh_token(str(account.id))

    await db.commit()

    return DeliveryPointVerifyOtpResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        is_new_user=is_new_user,
    )


@router.post("/refresh", response_model=DeliveryPointVerifyOtpResponse)
async def refresh_token(
    body: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryPointVerifyOtpResponse:
    """Refresh access token for delivery point account."""
    payload = decode_token(body.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    if payload.get("subject_type") != "delivery_point":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        point_uuid = UUID(sub)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(DeliveryPointAccount).where(DeliveryPointAccount.id == point_uuid))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found")
    if account.status == DeliveryPointAccountStatus.BLOCKED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked")

    access_token = create_delivery_point_access_token(str(account.id))
    refresh_token = create_delivery_point_refresh_token(str(account.id))
    return DeliveryPointVerifyOtpResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        is_new_user=False,
    )
