from aiogram import Bot

from app.core.config import settings


def get_bot(token: str | None = None) -> Bot:
    bot_token = token or settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    return Bot(token=bot_token)
