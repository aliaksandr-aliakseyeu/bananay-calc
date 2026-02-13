"""Send OTP to driver via Telegram (simulated SMS)."""
from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import DriverTelegramBinding

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


async def send_otp_to_telegram(
    db: AsyncSession,
    phone_e164: str,
    code: str,
) -> bool:
    """
    Look up Telegram binding by phone and send OTP message.
    Returns True if sent, False if no binding or send failed.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set, skipping Telegram OTP send")
        return False

    result = await db.execute(
        select(DriverTelegramBinding).where(
            DriverTelegramBinding.phone_e164 == phone_e164
        )
    )
    binding = result.scalar_one_or_none()
    if not binding:
        logger.info("No Telegram binding for phone %s", phone_e164)
        return False

    url = TELEGRAM_API_BASE.format(token=settings.TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": binding.telegram_chat_id,
        "text": f"Код для входа: {code}\n\nНикому не сообщайте этот код.",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{url}/sendMessage", json=payload)
            if resp.is_success:
                logger.info("OTP sent via Telegram to chat_id %s", binding.telegram_chat_id)
                return True
            logger.warning("Telegram sendMessage failed: %s %s", resp.status_code, resp.text)
            return False
    except Exception as e:
        logger.exception("Telegram OTP send error: %s", e)
        return False
