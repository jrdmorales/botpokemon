"""Envío de notificaciones Telegram con throttling y respeto de preferencias."""

import asyncio

import structlog
from sqlalchemy import select
from telegram import Bot
from telegram.error import Forbidden, RetryAfter, TelegramError

from app.config import get_settings
from app.db import SessionLocal
from app.models import TelegramUser
from app.services.alerts import PendingAlert

log = structlog.get_logger()

# Telegram limita ~30 mensajes/segundo global; nos quedamos muy por debajo
_SEND_DELAY_S = 0.1


def _get_bot() -> Bot | None:
    token = get_settings().telegram_bot_token
    return Bot(token) if token else None


async def _send(bot: Bot, chat_id: int | str, text: str) -> None:
    try:
        await bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=False)
    except RetryAfter as exc:
        await asyncio.sleep(exc.retry_after + 1)
        await bot.send_message(chat_id=chat_id, text=text)
    except Forbidden:
        log.info("user_blocked_bot", chat_id=chat_id)
    except TelegramError as exc:
        log.error("telegram_send_failed", chat_id=chat_id, error=str(exc))


async def notify_admin(message: str) -> None:
    """Alertas internas (salud de scrapers) al canal de administración."""
    settings = get_settings()
    bot = _get_bot()
    if bot is None or not settings.telegram_admin_chat_id:
        log.warning("admin_alert_no_telegram", message=message)
        return
    await _send(bot, settings.telegram_admin_chat_id, message)


def _user_wants(user: TelegramUser, alert: PendingAlert) -> bool:
    if not user.alerts_enabled:
        return False
    if alert.listing.language not in user.languages.split(","):
        # idioma "unknown" pasa siempre (mejor avisar de más que filtrar mal)
        if alert.listing.language != "unknown":
            return False
    if user.categories and alert.listing.category_slug:
        if alert.listing.category_slug not in user.categories.split(","):
            return False
    if alert.discount_pct is not None and alert.discount_pct < user.min_discount_pct:
        return False
    return True


async def broadcast_alert(alert: PendingAlert, text: str) -> None:
    bot = _get_bot()
    if bot is None:
        return
    async with SessionLocal() as session:
        users = (
            await session.scalars(
                select(TelegramUser).where(TelegramUser.alerts_enabled.is_(True))
            )
        ).all()
    for user in users:
        if not _user_wants(user, alert):
            continue
        await _send(bot, user.chat_id, text)
        await asyncio.sleep(_SEND_DELAY_S)
