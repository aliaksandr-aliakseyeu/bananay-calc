"""DC auth: request OTP, verify OTP."""
import random
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_dc_access_token, create_dc_refresh_token, decode_token
from app.db.base import get_db
from app.db.models import DcAccount, DcAccountStatus, DcOtpCode, DcOtpStatus
from app.schemas.auth import DcRequestOtp, DcVerifyOtp, DcVerifyOtpResponse, RefreshTokenRequest
from app.services.phone_service import validate_phone_e164
from app.services.telegram_otp_service import send_otp_to_telegram

router = APIRouter(prefix="/auth/dc", tags=["DC Auth"])

OTP_EXPIRE_MINUTES = 5
OTP_LENGTH = 4


def _generate_otp() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(OTP_LENGTH))


async def _get_or_create_dc(db: AsyncSession, phone_e164: str) -> tuple[DcAccount, bool]:
    """Return (dc_account, is_new_user)."""
    result = await db.execute(select(DcAccount).where(DcAccount.phone_e164 == phone_e164))
    dc_account = result.scalar_one_or_none()
    if dc_account:
        dc_account.last_login_at = datetime.now(timezone.utc)
        return dc_account, False
    dc_account = DcAccount(
        phone_e164=phone_e164,
        status=DcAccountStatus.DRAFT,
    )
    db.add(dc_account)
    await db.flush()
    return dc_account, True


@router.post("/request-otp")
async def request_otp(
    body: DcRequestOtp,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Request OTP for DC employee login."""
    phone_e164 = validate_phone_e164(body.phone_e164)
    code = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    result = await db.execute(select(DcOtpCode).where(DcOtpCode.phone_e164 == phone_e164))
    row = result.scalar_one_or_none()
    if row:
        row.code = code
        row.status = DcOtpStatus.PENDING
        row.expires_at = expires_at
        row.used_at = None
    else:
        row = DcOtpCode(
            phone_e164=phone_e164,
            code=code,
            status=DcOtpStatus.PENDING,
            expires_at=expires_at,
        )
        db.add(row)
    await db.flush()

    sent = await send_otp_to_telegram(db, phone_e164, code)
    await db.commit()

    if sent:
        return {"message": "Код отправлен в Telegram. Проверьте бота."}
    return {
        "message": (
            "Подпишитесь на нашего Telegram-бота и "
            "отправьте ему свой номер телефона — тогда вы получите код для входа."
        ),
        "telegram_sent": False,
    }


@router.post("/verify-otp", response_model=DcVerifyOtpResponse)
async def verify_otp(
    body: DcVerifyOtp,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcVerifyOtpResponse:
    """Verify OTP and return DC JWT tokens."""
    phone_e164 = validate_phone_e164(body.phone_e164)
    code = body.code.strip()

    universal = settings.DRIVER_OTP_UNIVERSAL_CODE
    if code == universal:
        dc_account, is_new_user = await _get_or_create_dc(db, phone_e164)
        await db.commit()
        dc_id_str = str(dc_account.id)
        return DcVerifyOtpResponse(
            access_token=create_dc_access_token(dc_id_str),
            refresh_token=create_dc_refresh_token(dc_id_str),
            token_type="bearer",
            is_new_user=is_new_user,
        )

    result = await db.execute(
        select(DcOtpCode).where(
            DcOtpCode.phone_e164 == phone_e164,
            DcOtpCode.status == DcOtpStatus.PENDING,
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

    row.status = DcOtpStatus.USED
    row.used_at = datetime.now(timezone.utc)

    dc_account, is_new_user = await _get_or_create_dc(db, phone_e164)
    await db.commit()
    dc_id_str = str(dc_account.id)
    return DcVerifyOtpResponse(
        access_token=create_dc_access_token(dc_id_str),
        refresh_token=create_dc_refresh_token(dc_id_str),
        token_type="bearer",
        is_new_user=is_new_user,
    )


@router.post("/refresh", response_model=DcVerifyOtpResponse)
async def refresh_dc_token(
    refresh_request: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DcVerifyOtpResponse:
    """Refresh DC access token pair using a valid DC refresh token."""
    payload = decode_token(refresh_request.refresh_token)
    if payload.get("type") != "refresh" or payload.get("subject_type") != "dc":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid DC refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    dc_id_raw = payload.get("sub")
    if not dc_id_raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid DC refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        dc_id = UUID(str(dc_id_raw))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid DC refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(DcAccount).where(DcAccount.id == dc_id))
    dc_account = result.scalar_one_or_none()
    if not dc_account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="DC account not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if dc_account.status == DcAccountStatus.BLOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="DC account is blocked",
        )

    dc_id_str = str(dc_account.id)
    return DcVerifyOtpResponse(
        access_token=create_dc_access_token(dc_id_str),
        refresh_token=create_dc_refresh_token(dc_id_str),
        token_type="bearer",
        is_new_user=False,
    )
