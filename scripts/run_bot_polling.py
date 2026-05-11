import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / ".env")

from app.bot.bot import get_bot
from app.bot.context import reset_telegram_business_id, set_telegram_business_id
from app.bot.dispatcher import dp
from app.core.config import settings


async def main() -> None:
    bot = get_bot()
    context_token = None
    if settings.DEFAULT_BUSINESS_ID is not None:
        context_token = set_telegram_business_id(settings.DEFAULT_BUSINESS_ID)
    try:
        await dp.start_polling(bot)
    finally:
        if context_token is not None:
            reset_telegram_business_id(context_token)
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
