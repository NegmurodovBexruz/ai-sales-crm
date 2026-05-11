from fastapi import APIRouter, Header, HTTPException, Request, status
from aiogram.types import Update
from sqlalchemy import select

from app.bot.bot import get_bot
from app.bot.context import reset_telegram_business_id, set_telegram_business_id
from app.bot.dispatcher import dp
from app.core.config import settings
from app.core.security import decrypt_secret
from app.db.session import SessionLocal
from app.models.business import Business

router = APIRouter(prefix="/telegram", tags=["telegram"])


def get_webhook_business_or_404(public_business_id: str) -> Business:
    db = SessionLocal()
    try:
        business = db.scalar(select(Business).where(Business.public_business_id == public_business_id))
        if business is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
        if not business.telegram_bot_token_encrypted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram bot token is not configured")
        db.expunge(business)
        return business
    finally:
        db.close()


async def feed_business_update(
    request: Request,
    business: Business,
    x_telegram_bot_api_secret_token: str | None,
) -> dict[str, bool]:
    if (
        business.telegram_webhook_secret
        and x_telegram_bot_api_secret_token != business.telegram_webhook_secret
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    bot = get_bot(decrypt_secret(business.telegram_bot_token_encrypted or ""))
    context_token = set_telegram_business_id(business.id)
    try:
        update_data = await request.json()
        update = Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    finally:
        reset_telegram_business_id(context_token)
        await bot.session.close()


@router.post("/webhook/{public_business_id}")
async def telegram_business_webhook(
    public_business_id: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    business = get_webhook_business_or_404(public_business_id)
    return await feed_business_update(request, business, x_telegram_bot_api_secret_token)


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if settings.APP_ENV == "production":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Business-specific webhook is required")
    if settings.DEFAULT_BUSINESS_ID is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DEFAULT_BUSINESS_ID is not configured")
    if (
        settings.TELEGRAM_WEBHOOK_SECRET
        and x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")

    bot = get_bot()
    context_token = set_telegram_business_id(settings.DEFAULT_BUSINESS_ID)
    try:
        update_data = await request.json()
        update = Update.model_validate(update_data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    finally:
        reset_telegram_business_id(context_token)
        await bot.session.close()
