from aiogram import Bot

from app.core.config import settings


def get_bot() -> Bot:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)

