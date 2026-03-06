"""Courier auth: request OTP, verify OTP."""
import random
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (create_courier_access_token,
                               create_courier_refresh_token, decode_token)
from app.db.base import get_db
from app.db.models import CourierAccount, CourierAccountStatus, CourierOtpCode, CourierOtpStatus
from app.schemas.auth import (CourierRequestOtp, CourierVerifyOtp,
                              CourierVerifyOtpResponse, RefreshTokenRequest)
from app.services.phone_service import validate_phone_e164
from app.services.telegram_otp_service import send_otp_to_telegram

router = APIRouter(prefix="/auth/courier", tags=["Courier Auth"])

OTP_EXPIRE_MINUTES = 5
OTP_LENGTH = 4


def _generate_otp() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(OTP_LENGTH))


async def _get_or_create_courier(db: AsyncSession, phone_e164: str) -> tuple[CourierAccount, bool]:
    """Return (courier_account, is_new_user)."""
    result = await db.execute(select(CourierAccount).where(CourierAccount.phone_e164 == phone_e164))
    courier = result.scalar_one_or_none()
    if courier:
        courier.last_login_at = datetime.now(timezone.utc)
        return courier, False
    courier = CourierAccount(
        phone_e164=phone_e164,
        status=CourierAccountStatus.DRAFT,
    )
    db.add(courier)
    await db.flush()
    return courier, True


@router.post("/request-otp")
async def request_otp(
    body: CourierRequestOtp,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Request OTP for courier login."""
    phone_e164 = validate_phone_e164(body.phone_e164)
    code = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    result = await db.execute(select(CourierOtpCode).where(CourierOtpCode.phone_e164 == phone_e164))
    row = result.scalar_one_or_none()
    if row:
        row.code = code
        row.status = CourierOtpStatus.PENDING
        row.expires_at = expires_at
        row.used_at = None
    else:
        row = CourierOtpCode(
            phone_e164=phone_e164,
            code=code,
            status=CourierOtpStatus.PENDING,
            expires_at=expires_at,
        )
        db.add(row)
    await db.flush()

    sent = await send_otp_to_telegram(db, phone_e164, code)
    await db.commit()

    if sent:
        return {"message": "Код отправлен в Telegram. Проверьте чат."}
    return {
        "message": (
            "Подключитесь к нашему Telegram-боту и попробуйте снова, "
            "или используйте код который придёт когда вы это сделаете."
        ),
        "telegram_sent": False,
    }


@router.post("/verify-otp", response_model=CourierVerifyOtpResponse)
async def verify_otp(
    body: CourierVerifyOtp,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourierVerifyOtpResponse:
    """Verify OTP and return courier JWT tokens."""
    phone_e164 = validate_phone_e164(body.phone_e164)
    code = body.code.strip()

    universal = settings.DRIVER_OTP_UNIVERSAL_CODE
    if code == universal:
        courier, is_new_user = await _get_or_create_courier(db, phone_e164)
        await db.commit()
        courier_id_str = str(courier.id)
        return CourierVerifyOtpResponse(
            access_token=create_courier_access_token(courier_id_str),
            refresh_token=create_courier_refresh_token(courier_id_str),
            token_type="bearer",
            is_new_user=is_new_user,
        )

    result = await db.execute(
        select(CourierOtpCode).where(
            CourierOtpCode.phone_e164 == phone_e164,
            CourierOtpCode.status == CourierOtpStatus.PENDING,
        )
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код не найден или уже использован. Запросите новый код.",
        )
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код истёк. Запросите новый код.",
        )
    if row.code != code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный код.",
        )

    row.status = CourierOtpStatus.USED
    row.used_at = datetime.now(timezone.utc)

    courier, is_new_user = await _get_or_create_courier(db, phone_e164)
    await db.commit()
    courier_id_str = str(courier.id)
    return CourierVerifyOtpResponse(
        access_token=create_courier_access_token(courier_id_str),
        refresh_token=create_courier_refresh_token(courier_id_str),
        token_type="bearer",
        is_new_user=is_new_user,
    )


@router.post("/refresh", response_model=CourierVerifyOtpResponse)
async def refresh_courier_token(
    refresh_request: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CourierVerifyOtpResponse:
    """Refresh courier access token pair using a valid courier refresh token."""
    payload = decode_token(refresh_request.refresh_token)
    if payload.get("type") != "refresh" or payload.get("subject_type") != "courier":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid courier refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    courier_id_raw = payload.get("sub")
    if not courier_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid courier refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        courier_uuid = UUID(str(courier_id_raw))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid courier refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(CourierAccount).where(CourierAccount.id == courier_uuid))
    courier = result.scalar_one_or_none()
    if not courier:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Courier account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if courier.status == CourierAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Courier account is blocked",
        )

    courier_id_str = str(courier.id)
    return CourierVerifyOtpResponse(
        access_token=create_courier_access_token(courier_id_str),
        refresh_token=create_courier_refresh_token(courier_id_str),
        token_type="bearer",
        is_new_user=False,
    )
