from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.context import get_telegram_business_id
from app.bot.keyboards import contact_request_keyboard, language_selection_keyboard
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.business import Business
from app.models.customer import Customer
from app.services.conversation_service import save_conversation_message
from app.services.customer_service import get_or_create_telegram_customer

router = Router()

LANGUAGE_SELECTED_MESSAGES = {
    "uz_latin": "Til tanlandi. Endi savolingizni yozishingiz mumkin.",
    "uz_cyrillic": "Тил танланди. Энди саволингизни ёзишингиз мумкин.",
    "ru": "Язык выбран. Теперь можете написать свой вопрос.",
}


def get_default_business(db) -> Business | None:
    business_id = get_telegram_business_id()
    if business_id is not None:
        return db.scalar(select(Business).where(Business.id == business_id))
    if settings.APP_ENV != "production" and settings.DEFAULT_BUSINESS_ID is not None:
        return db.scalar(select(Business).where(Business.id == settings.DEFAULT_BUSINESS_ID))
    if settings.APP_ENV == "production":
        return None
    return db.scalar(select(Business).order_by(Business.id.asc()).limit(1))


def get_telegram_identity(message_or_callback: Message | CallbackQuery) -> tuple[str, str | None, str | None]:
    user = message_or_callback.from_user
    name_parts = [user.first_name, user.last_name]
    full_name = " ".join(part for part in name_parts if part) or None
    return str(user.id), full_name, user.username


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    db = SessionLocal()
    try:
        business = get_default_business(db)
        if business is None:
            await message.answer("Bot setup is not ready yet. Please create a business first.")
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        get_or_create_telegram_customer(
            db=db,
            business_id=business.id,
            telegram_user_id=telegram_user_id,
            full_name=full_name,
            username=username,
        )
        await message.answer("Tilni tanlang / Тилни танланг / Выберите язык", reply_markup=language_selection_keyboard())
    finally:
        db.close()


@router.callback_query(F.data.in_({"lang:uz_latin", "lang:uz_cyrillic", "lang:ru"}))
async def select_language(callback: CallbackQuery) -> None:
    selected_language = callback.data.split(":", 1)[1] if callback.data else "uz_latin"
    db = SessionLocal()
    try:
        business = get_default_business(db)
        if business is None:
            await callback.answer("Business is not configured", show_alert=True)
            return

        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(
            db=db,
            business_id=business.id,
            telegram_user_id=telegram_user_id,
            full_name=full_name,
            username=username,
        )
        customer.language = selected_language
        db.commit()
        db.refresh(customer)

        save_conversation_message(
            db=db,
            business_id=business.id,
            customer_id=customer.id,
            message_text=f"language selected: {selected_language}",
            sender_type="system",
        )

        await callback.message.answer(
            LANGUAGE_SELECTED_MESSAGES[selected_language],
            reply_markup=contact_request_keyboard(selected_language),
        )
        await callback.answer()
    finally:
        db.close()
