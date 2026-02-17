"""
Telegram bot for driver OTP: users subscribe by sending their phone number.
Run: poetry run python -m scripts.telegram_otp_bot
Requires: TELEGRAM_BOT_TOKEN and DB env vars in .env
"""
import sys
import time
from pathlib import Path

# project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import psycopg2

from app.core.config import settings
from app.services.phone_service import normalize_phone_e164

TELEGRAM_API = "https://api.telegram.org/bot{token}"
BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN


def get_updates(token: str, offset: int | None) -> dict:
    url = TELEGRAM_API.format(token=token)
    params = {"timeout": 30}
    if offset is not None:
        params["offset"] = offset
    with httpx.Client(timeout=35) as client:
        r = client.get(f"{url}/getUpdates", params=params)
    r.raise_for_status()
    return r.json()


def send_message(token: str, chat_id: int, text: str) -> bool:
    url = TELEGRAM_API.format(token=token)
    with httpx.Client(timeout=10) as client:
        r = client.post(f"{url}/sendMessage", json={"chat_id": chat_id, "text": text})
    return r.is_success


def upsert_binding(conn, phone_e164: str, telegram_chat_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO driver_telegram_bindings (phone_e164, telegram_chat_id, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
            ON CONFLICT (phone_e164) DO UPDATE SET
                telegram_chat_id = EXCLUDED.telegram_chat_id,
                updated_at = NOW()
            """,
            (phone_e164, telegram_chat_id),
        )
    conn.commit()


def main() -> None:
    if not BOT_TOKEN:
        print("Set TELEGRAM_BOT_TOKEN in .env")
        sys.exit(1)

    dsn = settings.database_url_sync.replace("postgresql+psycopg2://", "postgresql://").split("?")[0]
    conn = psycopg2.connect(dsn)

    offset = None
    print("Bot running. Send /start and then your phone number (e.g. +79001234567 or 89001234567) to subscribe.")

    while True:
        try:
            data = get_updates(BOT_TOKEN, offset)
            if not data.get("ok"):
                print("getUpdates error:", data)
                time.sleep(5)
                continue
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue
                chat_id = msg["chat"]["id"]
                text = (msg.get("text") or "").strip()

                if text == "/start":
                    send_message(
                        BOT_TOKEN,
                        chat_id,
                        "Отправьте номер телефона в формате +79001234567 или 89001234567 — мы запомним его и будем присылать сюда коды для входа в приложение водителя.",
                    )
                    continue

                phone = normalize_phone_e164(text)
                if phone:
                    upsert_binding(conn, phone, chat_id)
                    send_message(
                        BOT_TOKEN,
                        chat_id,
                        f"Номер {phone} привязан. Теперь при запросе кода входа мы будем присылать его сюда.",
                    )
                else:
                    send_message(
                        BOT_TOKEN,
                        chat_id,
                        "Не похоже на номер телефона. Отправьте, например: +79001234567 или 89001234567",
                    )
        except (httpx.HTTPError, psycopg2.Error) as e:
            print("Error:", e)
            time.sleep(5)
        except KeyboardInterrupt:
            print("Bye")
            break
    conn.close()


if __name__ == "__main__":
    main()
