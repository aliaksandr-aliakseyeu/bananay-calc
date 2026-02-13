"""Driver auth: request OTP, verify OTP (Telegram as SMS simulation)."""
import random
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (create_driver_access_token,
                               create_driver_refresh_token)
from app.db.base import get_db
from app.db.models import (DriverAccount, DriverAccountStatus, DriverOtpCode,
                           DriverOtpStatus)
from app.schemas.auth import (DriverRequestOtp, DriverVerifyOtp,
                              DriverVerifyOtpResponse)
from app.services.phone_service import validate_phone_e164
from app.services.telegram_otp_service import send_otp_to_telegram

router = APIRouter(prefix="/auth/driver", tags=["Driver Auth"])

OTP_EXPIRE_MINUTES = 5
OTP_LENGTH = 4


def _generate_otp() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(OTP_LENGTH))


async def _get_or_create_driver(
    db: AsyncSession, phone_e164: str
) -> tuple[DriverAccount, bool]:
    """Return (driver, is_new_user)."""
    result = await db.execute(
        select(DriverAccount).where(DriverAccount.phone_e164 == phone_e164)
    )
    driver = result.scalar_one_or_none()
    if driver:
        driver.last_login_at = datetime.now(timezone.utc)
        return driver, False
    driver = DriverAccount(
        phone_e164=phone_e164,
        status=DriverAccountStatus.DRAFT,
    )
    db.add(driver)
    await db.flush()
    return driver, True


@router.post("/request-otp")
async def request_otp(
    body: DriverRequestOtp,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Request OTP for driver login.
    Generates 4-digit code, saves to DB, sends via Telegram if user subscribed to the bot.
    Accepts any country number (E.164 or local format).
    """
    phone_e164 = validate_phone_e164(body.phone_e164)
    code = _generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)

    result = await db.execute(
        select(DriverOtpCode).where(DriverOtpCode.phone_e164 == phone_e164)
    )
    row = result.scalar_one_or_none()
    if row:
        row.code = code
        row.status = DriverOtpStatus.PENDING
        row.expires_at = expires_at
        row.used_at = None
    else:
        row = DriverOtpCode(
            phone_e164=phone_e164,
            code=code,
            status=DriverOtpStatus.PENDING,
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


@router.post("/verify-otp", response_model=DriverVerifyOtpResponse)
async def verify_otp(
    body: DriverVerifyOtp,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DriverVerifyOtpResponse:
    """
    Verify OTP and return driver JWT (or use universal code 0320).
    Creates DriverAccount if first login. is_new_user=True for first-time drivers.
    Accepts any country number (E.164 or local format).
    """
    phone_e164 = validate_phone_e164(body.phone_e164)
    code = body.code.strip()

    universal = settings.DRIVER_OTP_UNIVERSAL_CODE
    if code == universal:
        driver, is_new_user = await _get_or_create_driver(db, phone_e164)
        await db.commit()
        driver_id_str = str(driver.id)
        return DriverVerifyOtpResponse(
            access_token=create_driver_access_token(driver_id_str),
            refresh_token=create_driver_refresh_token(driver_id_str),
            token_type="bearer",
            is_new_user=is_new_user,
        )
    result = await db.execute(
        select(DriverOtpCode).where(
            DriverOtpCode.phone_e164 == phone_e164,
            DriverOtpCode.status == DriverOtpStatus.PENDING,
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

    row.status = DriverOtpStatus.USED
    row.used_at = datetime.now(timezone.utc)

    driver, is_new_user = await _get_or_create_driver(db, phone_e164)
    await db.commit()

    driver_id_str = str(driver.id)
    return DriverVerifyOtpResponse(
        access_token=create_driver_access_token(driver_id_str),
        refresh_token=create_driver_refresh_token(driver_id_str),
        token_type="bearer",
        is_new_user=is_new_user,
    )
