import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.telegram_operator import TelegramOperator

logger = logging.getLogger(__name__)


async def notify_business_operators(
    db: Session,
    bot,
    business_id: int,
    text: str,
    reply_markup=None,
) -> int:
    operators = list(
        db.scalars(
            select(TelegramOperator).where(
                TelegramOperator.business_id == business_id,
                TelegramOperator.is_active.is_(True),
            )
        ).all()
    )
    chat_ids = [operator.telegram_chat_id for operator in operators]
    if not chat_ids:
        logger.warning("No active Telegram operators configured for business_id=%s", business_id)
        return 0

    successful = 0
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, text, reply_markup=reply_markup)
            successful += 1
        except Exception:
            logger.exception("Failed to notify Telegram operator chat_id=%s business_id=%s", chat_id, business_id)
    return successful


async def notify_single_operator(
    bot,
    operator: TelegramOperator,
    text: str,
    reply_markup=None,
) -> bool:
    try:
        await bot.send_message(operator.telegram_chat_id, text, reply_markup=reply_markup)
        return True
    except Exception:
        logger.exception("Failed to notify Telegram operator chat_id=%s", operator.telegram_chat_id)
        return False
