from decimal import Decimal
from urllib.parse import quote, unquote

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from app.bot.keyboards import (
    admin_order_actions_keyboard,
    cancel_confirmation_keyboard,
    cart_edit_keyboard,
    cart_item_actions_keyboard,
    cart_review_keyboard,
    category_keyboard,
    contact_request_keyboard,
    operator_claim_customer_keyboard,
    operator_claim_order_keyboard,
    order_confirmation_keyboard,
    order_name_confirm_keyboard,
    order_phone_confirm_keyboard,
    product_keyboard,
    start_order_keyboard,
)
from app.bot.handlers.start import get_telegram_identity
from app.bot.context import get_telegram_business_id
from app.bot.i18n import t
from app.bot.states.order import OrderStates
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.ai_log import AILog
from app.models.business import Business
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.product import Product
from app.models.telegram_operator import TelegramOperator
from app.services.ai_service import ai_service
from app.services.conversation_service import save_conversation_message
from app.services.customer_service import get_or_create_telegram_customer
from app.services.notification_service import notify_business_operators, notify_single_operator
from app.services.operator_assignment_service import get_active_assignment
from app.services.order_service import create_order_with_items
from app.utils.phone import normalize_uz_phone

router = Router()


def has_active_operators(db, business_id: int) -> bool:
    return db.scalar(
        select(TelegramOperator.id).where(
            TelegramOperator.business_id == business_id,
            TelegramOperator.is_active.is_(True),
        )
    ) is not None

CONFIRM_WORDS = {
    "ha",
    "ҳа",
    "да",
    "yes",
    "ok",
    "okay",
    "tasdiqlayman",
    "тасдиқлайман",
    "подтверждаю",
}

NO_COMMENT_WORDS = {"yo‘q", "yo'q", "йўқ", "нет", "no", "-"}


def get_configured_business(db) -> Business | None:
    business_id = get_telegram_business_id()
    if business_id is not None:
        return db.scalar(select(Business).where(Business.id == business_id))
    if settings.APP_ENV == "production" or settings.DEFAULT_BUSINESS_ID is None:
        return None
    return db.scalar(select(Business).where(Business.id == settings.DEFAULT_BUSINESS_ID))


def is_valid_order_name(name: str) -> bool:
    normalized = name.strip()
    return len(normalized) >= 2 and not normalized.isdigit()


def format_sum(value: Decimal | int | str) -> str:
    return f"{int(Decimal(str(value))):,}".replace(",", " ")


async def show_cart_review(message_or_callback, state: FSMContext, language: str) -> None:
    data = await state.get_data()
    cart = data.get("cart") or []
    if not cart:
        await state.clear()
        target = getattr(message_or_callback, "message", message_or_callback)
        await target.answer(order_text("cancelled", language))
        return

    await state.set_state(OrderStates.cart_review)
    target = getattr(message_or_callback, "message", message_or_callback)
    await target.answer(cart_review_text(cart, language), reply_markup=cart_review_keyboard(language))


def product_final_price(product: Product) -> Decimal:
    return product.discount_price if product.discount_price is not None else product.price


def get_available_categories(db, business_id: int) -> list[tuple[str, str]]:
    categories = list(
        db.scalars(
            select(Product.category)
            .where(Product.business_id == business_id, Product.stock_count > 0)
            .distinct()
            .order_by(Product.category.asc())
        ).all()
    )
    labels = [(category or "Boshqa", quote(category or "__none__", safe="")) for category in categories]
    return labels


def category_filter_value(encoded_category: str) -> str | None:
    decoded = unquote(encoded_category)
    return None if decoded == "__none__" else decoded


def get_available_products_for_category(db, business_id: int, category: str | None) -> list[Product]:
    query = select(Product).where(Product.business_id == business_id, Product.stock_count > 0)
    query = query.where(Product.category.is_(None)) if category is None else query.where(Product.category == category)
    return list(db.scalars(query.order_by(Product.name.asc())).all())


async def show_categories(message, state: FSMContext, db, business: Business, customer: Customer) -> None:
    categories = get_available_categories(db, business.id)
    await state.update_data(business_id=business.id, customer_id=customer.id)
    await state.set_state(OrderStates.choosing_category)
    if not categories:
        await message.answer(text_for("out_of_stock", customer.language))
        return
    await message.answer(order_text("choose_category", customer.language), reply_markup=category_keyboard(categories, customer.language))


async def show_products_for_category(message, state: FSMContext, db, business: Business, customer: Customer, category: str | None) -> None:
    products = get_available_products_for_category(db, business.id, category)
    await state.update_data(selected_category=category)
    await state.set_state(OrderStates.choosing_product)
    if not products:
        await message.answer(order_text("choose_category", customer.language), reply_markup=category_keyboard(get_available_categories(db, business.id), customer.language))
        return
    await message.answer(
        order_text("choose_product", customer.language),
        reply_markup=product_keyboard(product_button_rows(products, customer.language), customer.language),
    )


def cart_item_currency(language: str) -> str:
    return t(language, "currency")


def cart_review_text(cart: list[dict], language: str) -> str:
    total_price = sum(Decimal(str(item["total_price"])) for item in cart)
    currency = cart_item_currency(language)
    product_lines = "\n".join(
        f"{index}. {item['product_name']} x {item['quantity']} = {format_sum(item['total_price'])} {currency}"
        for index, item in enumerate(cart, start=1)
    )
    return t(language, "cart_review", product_lines=product_lines, total_price=format_sum(total_price))


def product_button_rows(products: list[Product], language: str = "uz_latin") -> list[tuple[str, int]]:
    low_stock_text = t(language, "low_stock_suffix")
    currency = cart_item_currency(language)
    rows = []
    for product in products:
        suffix = f" · {low_stock_text}" if 1 <= product.stock_count <= 10 else ""
        rows.append((f"{product.name} - {format_sum(product_final_price(product))} {currency}{suffix}", product.id))
    return rows


def order_text(key: str, language: str, **kwargs) -> str:
    return t(language, key, **kwargs)


def cart_item_detail_text(item: dict, language: str) -> str:
    return t(language, "cart_item_detail", **item)


def invalid_phone_text(language: str) -> str:
    return t(language, "invalid_phone")


def name_confirm_text(language: str, full_name: str) -> str:
    return t(language, "name_confirm", full_name=full_name)


def phone_confirm_text(language: str, phone: str) -> str:
    return t(language, "phone_confirm", phone=phone)


def text_for(key: str, language: str, **kwargs) -> str:
    return t(language, key, **kwargs)


def order_text(key: str, language: str, **kwargs) -> str:
    return t(language, key, **kwargs)


def cart_item_currency(language: str) -> str:
    return t(language, "currency")


def cart_review_text(cart: list[dict], language: str) -> str:
    total_price = sum(Decimal(str(item["total_price"])) for item in cart)
    currency = cart_item_currency(language)
    product_lines = "\n".join(
        f"{index}. {item['product_name']} x {item['quantity']} = {format_sum(item['total_price'])} {currency}"
        for index, item in enumerate(cart, start=1)
    )
    return t(language, "cart_review", product_lines=product_lines, total_price=format_sum(total_price))


def product_button_rows(products: list[Product], language: str = "uz_latin") -> list[tuple[str, int]]:
    low_stock_text = t(language, "low_stock_suffix")
    currency = cart_item_currency(language)
    rows = []
    for product in products:
        suffix = f" · {low_stock_text}" if 1 <= product.stock_count <= 10 else ""
        rows.append((f"{product.name} - {format_sum(product_final_price(product))} {currency}{suffix}", product.id))
    return rows


def cart_item_detail_text(item: dict, language: str) -> str:
    return t(language, "cart_item_detail", **item)


async def show_edit_cart(callback: CallbackQuery, state: FSMContext, language: str) -> None:
    data = await state.get_data()
    cart = data.get("cart") or []
    if not cart:
        await show_cart_review(callback, state, language)
        return
    await state.set_state(OrderStates.editing_cart)
    await callback.message.answer(
        text_for("edit_cart_prompt", language),
        reply_markup=cart_edit_keyboard(cart, language),
    )


async def ask_cancel_confirmation(callback: CallbackQuery, state: FSMContext, language: str) -> None:
    data = await state.get_data()
    cart = data.get("cart") or []
    if not cart:
        await state.clear()
        await callback.message.answer(order_text("cancelled", language))
        return
    await callback.message.answer(
        text_for("cancel_full_confirm", language),
        reply_markup=cancel_confirmation_keyboard(language),
    )


def find_product_by_text(db, business_id: int, text: str) -> Product | None:
    query_text = text.lower()
    products = db.scalars(select(Product).where(Product.business_id == business_id)).all()
    for product in products:
        product_name = product.name.lower()
        if product_name in query_text or query_text in product_name:
            return product
        if product.tags:
            tags = [tag.strip().lower() for tag in product.tags.replace(";", ",").split(",")]
            if any(tag and (tag in query_text or query_text in tag) for tag in tags):
                return product
    return None


def get_first_available_recommended_product(db, business_id: int, ai_result: dict) -> Product | None:
    recommended_product_ids = ai_result.get("recommended_product_ids")
    if not isinstance(recommended_product_ids, list):
        return None

    for product_id in recommended_product_ids:
        try:
            normalized_product_id = int(product_id)
        except (TypeError, ValueError):
            continue
        product = db.scalar(
            select(Product).where(Product.id == normalized_product_id, Product.business_id == business_id)
        )
        if product is not None and product.stock_count > 0:
            return product
    return None


def get_order_button_product(db, business_id: int, customer_message: str, ai_result: dict) -> Product | None:
    recommended_product = get_first_available_recommended_product(db, business_id, ai_result)
    if recommended_product is not None:
        return recommended_product

    text_product = find_product_by_text(db, business_id, customer_message)
    if text_product is not None and text_product.stock_count > 0:
        return text_product

    return None


def should_show_generic_order_button(ai_result: dict) -> bool:
    return ai_result.get("order_intent") is True or ai_result.get("intent") in {
        "order_intent",
        "price_question",
        "availability_question",
        "product_question",
    }


def get_product(db, product_id: int) -> Product | None:
    return db.scalar(select(Product).where(Product.id == product_id))


def get_unit_price(product: Product) -> Decimal:
    return product.discount_price if product.discount_price is not None else product.price


def normalize_confirmation_text(text: str) -> str:
    return text.strip().lower()


def is_confirmation_text(text: str) -> bool:
    return normalize_confirmation_text(text) in CONFIRM_WORDS


def is_empty_comment(text: str) -> bool:
    return normalize_confirmation_text(text) in NO_COMMENT_WORDS


async def ask_quantity(message: Message, state: FSMContext, customer: Customer, product: Product) -> None:
    await state.update_data(selected_product_id=product.id)
    await state.set_state(OrderStates.waiting_for_quantity)
    await message.answer(order_text("ask_quantity_with_stock", customer.language, stock_count=product.stock_count))


async def ask_name(message: Message, state: FSMContext, customer: Customer) -> None:
    await state.set_state(OrderStates.waiting_for_name)
    if customer.full_name:
        await state.update_data(default_customer_name=customer.full_name)
        await message.answer(
            name_confirm_text(customer.language, customer.full_name),
            reply_markup=order_name_confirm_keyboard(customer.language),
        )
    else:
        await message.answer(text_for("ask_name", customer.language))


async def ask_phone(message: Message, state: FSMContext, customer: Customer) -> None:
    await state.set_state(OrderStates.waiting_for_phone)
    if customer.phone:
        await state.update_data(default_phone=customer.phone)
        await message.answer(
            phone_confirm_text(customer.language, customer.phone),
            reply_markup=order_phone_confirm_keyboard(customer.language),
        )
    else:
        await message.answer(text_for("ask_phone", customer.language), reply_markup=contact_request_keyboard(customer.language))


async def ask_address(message: Message, state: FSMContext, customer: Customer) -> None:
    await state.set_state(OrderStates.waiting_for_address)
    await message.answer(text_for("ask_address", customer.language))


async def ask_comment(message: Message, state: FSMContext, customer: Customer) -> None:
    await state.set_state(OrderStates.waiting_for_comment)
    await message.answer(text_for("ask_comment", customer.language))


async def show_order_confirmation(message: Message, state: FSMContext, db, customer: Customer) -> None:
    data = await state.get_data()
    cart = data.get("cart") or []
    if not cart:
        await state.clear()
        await message.answer(order_text("cancelled", customer.language))
        return

    total_price = sum(Decimal(str(item["total_price"])) for item in cart)
    currency = cart_item_currency(customer.language)
    product_lines = "\n".join(
        f"{index}. {item['product_name']} x {item['quantity']} = {format_sum(item['total_price'])} {currency}"
        for index, item in enumerate(cart, start=1)
    )
    comment = data.get("comment") or "-"
    summary = t(
        customer.language,
        "order_confirmation",
        product_lines=product_lines,
        total_price=format_sum(total_price),
        customer_name=data["customer_name"],
        phone=data["phone"],
        address=data["address"],
        comment=comment,
    )
    await state.update_data(total_price=str(total_price))
    await state.set_state(OrderStates.confirmation)
    await message.answer(summary, reply_markup=order_confirmation_keyboard(customer.language))


async def start_order_flow_for_product(
    message: Message,
    state: FSMContext,
    db,
    business: Business,
    customer: Customer,
    product: Product,
) -> None:
    await state.update_data(business_id=business.id, customer_id=customer.id, selected_product_id=product.id)
    await ask_quantity(message, state, customer, product)


def ai_reply_already_saved(db, business_id: int, customer_id: int, reply: str) -> bool:
    last_message = db.scalar(
        select(Conversation)
        .where(Conversation.business_id == business_id, Conversation.customer_id == customer_id)
        .order_by(Conversation.created_at.desc())
        .limit(1)
    )
    return (
        last_message is not None
        and last_message.sender_type == "ai"
        and last_message.message_text == reply
    )


def save_ai_error_log(
    db,
    business_id: int,
    customer_id: int,
    customer_message: str,
    fallback_reply: str,
    error_message: str,
) -> None:
    db.add(
        AILog(
            business_id=business_id,
            customer_id=customer_id,
            user_message=customer_message,
            ai_response=fallback_reply,
            detected_intent="unknown",
            confidence=0,
            error_message=error_message,
        )
    )
    db.commit()


def customer_has_contact(customer: Customer) -> bool:
    return bool(customer.username or customer.phone)


def save_pending_operator_context(
    db,
    customer: Customer,
    customer_message: str,
    ai_reply: str,
    intent: str,
    confidence: float,
) -> None:
    customer.pending_operator_message = customer_message
    customer.pending_operator_ai_reply = ai_reply
    customer.pending_operator_intent = intent
    customer.pending_operator_confidence = Decimal(str(confidence))
    db.commit()
    db.refresh(customer)


def clear_pending_operator_context(db, customer: Customer) -> None:
    customer.pending_operator_message = None
    customer.pending_operator_ai_reply = None
    customer.pending_operator_intent = None
    customer.pending_operator_confidence = None
    db.commit()
    db.refresh(customer)


async def notify_admin(
    message: Message,
    customer: Customer,
    customer_message: str,
    ai_reply: str,
    business_id: int,
    intent: str,
    confidence: float,
    error_message: str | None = None,
) -> bool:

    full_name = customer.full_name or "noma’lum"
    username_text = f"@{customer.username}" if customer.username else "yo‘q"
    phone = customer.phone or "hali yuborilmagan"
    admin_message = (
        "Operator kerak\n\n"
        f"Business ID: {business_id}\n"
        f"Customer ID: {customer.id}\n\n"
        f"Ism: {full_name}\n"
        f"Username: {username_text}\n"
        f"Telefon: {phone}\n"
        f"Telegram ID: {customer.telegram_user_id}\n"
        f"Til: {customer.language}\n\n"
        f"Mijoz xabari:\n{customer_message}\n\n"
        f"AI javobi:\n{ai_reply}\n\n"
        f"Intent: {intent}\n"
        f"Confidence: {confidence}"
    )
    if error_message:
        admin_message += f"\nError: {error_message}"

    db = SessionLocal()
    try:
        assignment = get_active_assignment(db, business_id, customer.id)
        if assignment is not None:
            operator = db.scalar(select(TelegramOperator).where(TelegramOperator.id == assignment.operator_id))
            if operator is not None and operator.is_active:
                return await notify_single_operator(message.bot, operator, admin_message)
        reply_markup = operator_claim_customer_keyboard(customer.id) if has_active_operators(db, business_id) else None
        sent_count = await notify_business_operators(db, message.bot, business_id, admin_message, reply_markup=reply_markup)
        return sent_count > 0
    finally:
        db.close()


async def notify_admin_order(message: Message, customer: Customer, business_id: int, order, product: Product | None = None) -> None:
    username_text = f"@{customer.username}" if customer.username else "yo‘q"
    order_items = list(getattr(order, "items", []) or [])
    if order_items:
        product_lines = "\n".join(
            f"{index}. {item.product_name} x {item.quantity} - {format_sum(item.total_price)} so‘m"
            for index, item in enumerate(order_items, start=1)
        )
    elif product is not None:
        product_lines = f"1. {product.name} x {order.quantity} - {format_sum(order.total_price)} so‘m"
    else:
        product_lines = "-"
    admin_message = (
        "Yangi buyurtma\n\n"
        f"Business ID: {business_id}\n"
        f"Order ID: {order.id}\n"
        f"Customer ID: {customer.id}\n\n"
        f"Ism: {order.customer_name}\n"
        f"Username: {username_text}\n"
        f"Telefon: {order.phone}\n"
        f"Telegram ID: {customer.telegram_user_id}\n"
        f"Til: {customer.language}\n\n"
        f"Mahsulotlar:\n{product_lines}\n\n"
        f"Jami: {format_sum(order.total_price)} so‘m\n\n"
        f"Manzil:\n{order.address}\n\n"
        f"Izoh:\n{order.comment or '-'}\n\n"
        "Status: new"
    )
    db = SessionLocal()
    try:
        assignment = get_active_assignment(db, business_id, customer.id)
        if assignment is not None:
            operator = db.scalar(select(TelegramOperator).where(TelegramOperator.id == assignment.operator_id))
            if operator is not None and operator.is_active:
                await notify_single_operator(
                    message.bot,
                    operator,
                    admin_message,
                    reply_markup=admin_order_actions_keyboard(order.id),
                )
                return
        reply_markup = (
            operator_claim_order_keyboard(order.id)
            if has_active_operators(db, business_id)
            else admin_order_actions_keyboard(order.id)
        )
        await notify_business_operators(db, message.bot, business_id, admin_message, reply_markup=reply_markup)
    finally:
        db.close()


@router.callback_query(F.data == "start_order")
async def start_generic_order_from_button(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await callback.message.answer(t("uz_latin", "setup_not_ready"))
            await callback.answer()
            return

        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        await state.clear()
        await show_categories(callback.message, state, db, business, customer)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("start_order:"))
async def start_order_from_button(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await callback.message.answer(t("uz_latin", "setup_not_ready"))
            await callback.answer()
            return

        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        await state.clear()
        await show_categories(callback.message, state, db, business, customer)
        await callback.answer()
        return

        try:
            product_id = int((callback.data or "").split(":", 1)[1])
        except (IndexError, ValueError):
            await callback.answer(t("uz_latin", "invalid_product"), show_alert=True)
            return

        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        product = db.scalar(select(Product).where(Product.id == product_id, Product.business_id == business.id))
        if product is None:
            await callback.answer(t(customer.language, "product_not_found"), show_alert=True)
            return
        if product.stock_count <= 0:
            await callback.message.answer(t(customer.language, "out_of_stock"))
            await callback.answer()
            return

        save_conversation_message(
            db=db,
            business_id=business.id,
            customer_id=customer.id,
            message_text=f"order button clicked for product_id={product.id}",
            sender_type="customer",
            intent="order_button_clicked",
        )
        await start_order_flow_for_product(callback.message, state, db, business, customer, product)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "order_cancel")
@router.callback_query(F.data == "order_cancel_full")
async def cancel_order_flow(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        language = "uz_latin"
        business = get_configured_business(db)
        if business is not None:
            telegram_user_id, full_name, username = get_telegram_identity(callback)
            customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
            language = customer.language

        current_state = await state.get_state()
        data = await state.get_data()
        cart = data.get("cart") or []
        callback_data = getattr(callback, "data", None)
        if callback_data == "order_cancel_full" and cart:
            await ask_cancel_confirmation(callback, state, language)
            await callback.answer()
            return

        if current_state in {OrderStates.choosing_category.state, OrderStates.choosing_product.state} and cart:
            await ask_cancel_confirmation(callback, state, language)
            await callback.answer()
            return

        await state.clear()
        await callback.message.answer(order_text("cancelled", language))
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("order_category:"))
async def choose_order_category(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await callback.answer(t("uz_latin", "business_not_configured"), show_alert=True)
            return
        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        encoded_category = (callback.data or "").split(":", 1)[1]
        await show_products_for_category(callback.message, state, db, business, customer, category_filter_value(encoded_category))
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "order_back_to_categories")
async def back_to_order_categories(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await callback.answer(t("uz_latin", "business_not_configured"), show_alert=True)
            return
        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        await show_categories(callback.message, state, db, business, customer)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("order_product:"))
async def choose_order_product(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await callback.answer(t("uz_latin", "business_not_configured"), show_alert=True)
            return
        try:
            product_id = int((callback.data or "").split(":", 1)[1])
        except (IndexError, ValueError):
            await callback.answer(t("uz_latin", "invalid_product"), show_alert=True)
            return
        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        product = db.scalar(select(Product).where(Product.id == product_id, Product.business_id == business.id))
        if product is None or product.stock_count <= 0:
            await callback.answer(t(customer.language, "product_unavailable"), show_alert=True)
            return
        await ask_quantity(callback.message, state, customer, product)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "order_add_more")
async def order_add_more(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await callback.answer(t("uz_latin", "business_not_configured"), show_alert=True)
            return
        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        await show_categories(callback.message, state, db, business, customer)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "order_back_to_cart")
async def order_back_to_cart(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        language = "uz_latin"
        business = get_configured_business(db)
        if business is not None:
            telegram_user_id, full_name, username = get_telegram_identity(callback)
            customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
            language = customer.language
        await show_cart_review(callback, state, language)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "order_edit_cart")
async def order_edit_cart(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        language = "uz_latin"
        if business is not None:
            telegram_user_id, full_name, username = get_telegram_identity(callback)
            customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
            language = customer.language
        await show_edit_cart(callback, state, language)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("order_edit_item:"))
async def order_edit_item(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        language = "uz_latin"
        if business is not None:
            telegram_user_id, full_name, username = get_telegram_identity(callback)
            customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
            language = customer.language
        try:
            product_id = int((callback.data or "").split(":", 1)[1])
        except (IndexError, ValueError):
            await callback.answer(t(language, "invalid_product"), show_alert=True)
            return
        data = await state.get_data()
        item = next((item for item in data.get("cart", []) if int(item["product_id"]) == product_id), None)
        if item is None:
            await show_cart_review(callback, state, language)
            await callback.answer()
            return
        await state.update_data(editing_product_id=product_id)
        await callback.message.answer(
            cart_item_detail_text(item, language),
            reply_markup=cart_item_actions_keyboard(product_id, language),
        )
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("order_change_qty:"))
async def order_change_qty(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await callback.answer(t("uz_latin", "business_not_configured"), show_alert=True)
            return
        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        try:
            product_id = int((callback.data or "").split(":", 1)[1])
        except (IndexError, ValueError):
            await callback.answer(t(customer.language, "invalid_product"), show_alert=True)
            return
        product = db.scalar(select(Product).where(Product.id == product_id, Product.business_id == business.id))
        if product is None:
            await callback.answer(t(customer.language, "product_not_found"), show_alert=True)
            return
        await state.update_data(editing_product_id=product_id)
        await state.set_state(OrderStates.editing_item_quantity)
        await callback.message.answer(
            text_for("change_quantity_prompt", customer.language, stock_count=product.stock_count)
        )
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("order_remove_item:"))
async def order_remove_item(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await callback.answer(t("uz_latin", "business_not_configured"), show_alert=True)
            return
        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        try:
            product_id = int((callback.data or "").split(":", 1)[1])
        except (IndexError, ValueError):
            await callback.answer(t(customer.language, "invalid_product"), show_alert=True)
            return
        data = await state.get_data()
        cart = [item for item in data.get("cart", []) if int(item["product_id"]) != product_id]
        await state.update_data(cart=cart, editing_product_id=None)
        if cart:
            await show_cart_review(callback, state, customer.language)
        else:
            await callback.message.answer(text_for("cart_empty_choose_category", customer.language))
            await show_categories(callback.message, state, db, business, customer)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "order_cancel_confirm")
async def order_cancel_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        language = "uz_latin"
        business = get_configured_business(db)
        if business is not None:
            telegram_user_id, full_name, username = get_telegram_identity(callback)
            customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
            language = customer.language
        await state.clear()
        await callback.message.answer(order_text("cancelled", language))
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data == "order_finish_items")
async def order_finish_items(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await callback.answer(t("uz_latin", "business_not_configured"), show_alert=True)
            return
        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        data = await state.get_data()
        if not data.get("cart"):
            await show_categories(callback.message, state, db, business, customer)
        elif data.get("customer_name") and data.get("phone") and data.get("address"):
            await show_order_confirmation(callback.message, state, db, customer)
        else:
            await ask_name(callback.message, state, customer)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(StateFilter(OrderStates.waiting_for_name), F.data == "order_name_use_existing")
async def use_existing_order_name(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await callback.message.answer(t("uz_latin", "setup_not_ready"))
            await callback.answer()
            return

        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        if not customer.full_name:
            await callback.message.answer(text_for("ask_name", customer.language))
            await callback.answer()
            return

        await state.update_data(customer_name=customer.full_name)
        await ask_phone(callback.message, state, customer)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(StateFilter(OrderStates.waiting_for_name), F.data == "order_name_enter_new")
async def enter_new_order_name(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        language = "uz_latin"
        if business is not None:
            telegram_user_id, full_name, username = get_telegram_identity(callback)
            customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
            language = customer.language
        await state.set_state(OrderStates.waiting_for_name)
        await callback.message.answer(text_for("ask_name", language))
        await callback.answer()
    finally:
        db.close()


@router.callback_query(StateFilter(OrderStates.waiting_for_phone), F.data == "order_phone_use_existing")
async def use_existing_order_phone(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await callback.message.answer(t("uz_latin", "setup_not_ready"))
            await callback.answer()
            return

        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        phone = normalize_uz_phone(customer.phone or "")
        if phone is None:
            await callback.message.answer(text_for("ask_phone", customer.language), reply_markup=contact_request_keyboard(customer.language))
            await callback.answer()
            return

        await state.update_data(phone=phone)
        await ask_address(callback.message, state, customer)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(StateFilter(OrderStates.waiting_for_phone), F.data == "order_phone_enter_new")
async def enter_new_order_phone(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        language = "uz_latin"
        if business is not None:
            telegram_user_id, full_name, username = get_telegram_identity(callback)
            customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
            language = customer.language
        await state.set_state(OrderStates.waiting_for_phone)
        await callback.message.answer(text_for("ask_phone", language), reply_markup=contact_request_keyboard(language))
        await callback.answer()
    finally:
        db.close()


@router.callback_query(
    StateFilter(
        OrderStates.waiting_for_name,
        OrderStates.waiting_for_phone,
        OrderStates.waiting_for_address,
        OrderStates.waiting_for_comment,
    ),
    F.data == "order:cancel",
)
async def cancel_order_details(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        language = "uz_latin"
        if business is not None:
            telegram_user_id, full_name, username = get_telegram_identity(callback)
            customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
            language = customer.language
        await state.clear()
        await callback.message.answer(text_for("cancelled", language))
        await callback.answer()
    finally:
        db.close()


@router.message(StateFilter(OrderStates.choosing_product), F.text)
async def handle_order_product(message: Message, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        product = find_product_by_text(db, business.id, message.text or "")
        if product is None:
            await message.answer(text_for("ask_product", customer.language))
            return
        if product.stock_count == 0:
            await state.clear()
            await message.answer(text_for("out_of_stock", customer.language))
            return
        await ask_quantity(message, state, customer, product)
    finally:
        db.close()


@router.message(StateFilter(OrderStates.waiting_for_quantity), F.text)
async def handle_order_quantity(message: Message, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        data = await state.get_data()
        product = get_product(db, data["selected_product_id"])
        if product is None:
            await state.clear()
            await message.answer(text_for("ask_product", customer.language))
            return

        try:
            quantity = int((message.text or "").strip())
        except ValueError:
            await message.answer(text_for("invalid_quantity", customer.language))
            return
        if quantity <= 0:
            await message.answer(text_for("invalid_quantity", customer.language))
            return
        if quantity > product.stock_count:
            await message.answer(text_for("available_quantity", customer.language, stock_count=product.stock_count))
            return
        cart = list(data.get("cart") or [])
        existing_index = next((index for index, item in enumerate(cart) if item["product_id"] == product.id), None)
        existing_quantity = cart[existing_index]["quantity"] if existing_index is not None else 0
        if existing_quantity + quantity > product.stock_count:
            await message.answer(text_for("available_quantity", customer.language, stock_count=product.stock_count))
            return

        final_unit_price = product_final_price(product)
        total_quantity = existing_quantity + quantity
        total_price = final_unit_price * total_quantity
        if existing_index is not None:
            cart[existing_index].update(
                {
                    "quantity": total_quantity,
                    "final_unit_price": str(final_unit_price),
                    "total_price": str(total_price),
                }
            )
        else:
            cart.append(
                {
                    "product_id": product.id,
                    "product_name": product.name,
                    "category": product.category,
                    "quantity": quantity,
                    "unit_price": str(product.price),
                    "discount_price": str(product.discount_price) if product.discount_price is not None else None,
                    "final_unit_price": str(final_unit_price),
                    "total_price": str(final_unit_price * quantity),
                }
            )

        await state.update_data(cart=cart, selected_category=None, selected_product_id=None)
        await show_cart_review(message, state, customer.language)
    finally:
        db.close()


@router.message(StateFilter(OrderStates.editing_item_quantity), F.text)
async def handle_edit_item_quantity(message: Message, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        data = await state.get_data()
        product_id = data.get("editing_product_id")
        product = get_product(db, int(product_id)) if product_id is not None else None
        if product is None or product.business_id != business.id:
            await show_cart_review(message, state, customer.language)
            return

        try:
            quantity = int((message.text or "").strip())
        except ValueError:
            await message.answer(text_for("invalid_quantity", customer.language))
            return
        if quantity <= 0:
            await message.answer(text_for("invalid_quantity", customer.language))
            return
        if quantity > product.stock_count:
            await message.answer(text_for("available_quantity", customer.language, stock_count=product.stock_count))
            return

        final_unit_price = product_final_price(product)
        cart = list(data.get("cart") or [])
        for item in cart:
            if int(item["product_id"]) == product.id:
                item.update(
                    {
                        "quantity": quantity,
                        "unit_price": str(product.price),
                        "discount_price": str(product.discount_price) if product.discount_price is not None else None,
                        "final_unit_price": str(final_unit_price),
                        "total_price": str(final_unit_price * quantity),
                    }
                )
                break
        await state.update_data(cart=cart, editing_product_id=None)
        await show_cart_review(message, state, customer.language)
    finally:
        db.close()


@router.message(StateFilter(OrderStates.waiting_for_name), F.text)
async def handle_order_name(message: Message, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        text = (message.text or "").strip()
        if not is_valid_order_name(text):
            await message.answer(text_for("ask_name", customer.language))
            return

        customer.full_name = text
        db.commit()
        db.refresh(customer)
        await state.update_data(customer_name=text)
        await ask_phone(message, state, customer)
    finally:
        db.close()


@router.message(StateFilter(OrderStates.waiting_for_phone), F.contact)
async def handle_order_phone_contact(message: Message, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        contact = message.contact
        if contact is None or contact.user_id != message.from_user.id:
            await message.answer(t(customer.language, "own_contact_required"))
            return

        normalized_phone = normalize_uz_phone(contact.phone_number)
        if normalized_phone is None:
            await message.answer(invalid_phone_text(customer.language), reply_markup=contact_request_keyboard(customer.language))
            return

        customer.phone = normalized_phone
        db.commit()
        db.refresh(customer)
        save_conversation_message(
            db=db,
            business_id=business.id,
            customer_id=customer.id,
            message_text=f"phone shared: {normalized_phone}",
            sender_type="customer",
            intent="phone_shared",
        )
        await state.update_data(phone=normalized_phone)
        await ask_address(message, state, customer)
    finally:
        db.close()


@router.message(StateFilter(OrderStates.waiting_for_phone), F.text)
async def handle_order_phone_text(message: Message, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        data = await state.get_data()
        text = (message.text or "").strip()
        phone_source = data.get("default_phone") if is_confirmation_text(text) else text
        phone = normalize_uz_phone(phone_source or "")
        if not phone:
            await message.answer(invalid_phone_text(customer.language), reply_markup=contact_request_keyboard(customer.language))
            return

        customer.phone = phone
        db.commit()
        db.refresh(customer)
        await state.update_data(phone=phone)
        await ask_address(message, state, customer)
    finally:
        db.close()


@router.message(StateFilter(OrderStates.waiting_for_address), F.text)
async def handle_order_address(message: Message, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        address = (message.text or "").strip()
        if not address:
            await message.answer(text_for("ask_address", customer.language))
            return

        await state.update_data(address=address)
        await ask_comment(message, state, customer)
    finally:
        db.close()


@router.message(StateFilter(OrderStates.waiting_for_comment), F.text)
async def handle_order_comment(message: Message, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        text = (message.text or "").strip()
        await state.update_data(comment=None if is_empty_comment(text) else text)
        await show_order_confirmation(message, state, db, customer)
    finally:
        db.close()


@router.callback_query(StateFilter(OrderStates.confirmation), F.data == "order:cancel")
@router.callback_query(StateFilter(OrderStates.confirmation), F.data == "order_cancel_full")
async def cancel_order(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        language = "uz_latin"
        if business is not None:
            telegram_user_id, full_name, username = get_telegram_identity(callback)
            customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
            language = customer.language
        if getattr(callback, "data", None) == "order_cancel_full":
            await ask_cancel_confirmation(callback, state, language)
        else:
            await state.clear()
            await callback.message.answer(text_for("cancelled", language))
        await callback.answer()
    finally:
        db.close()


@router.callback_query(StateFilter(OrderStates.confirmation), F.data == "order:confirm")
@router.callback_query(StateFilter(OrderStates.confirmation), F.data == "order_confirm")
async def confirm_order(callback: CallbackQuery, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await state.clear()
            await callback.message.answer(t("uz_latin", "setup_not_ready"))
            await callback.answer()
            return

        telegram_user_id, full_name, username = get_telegram_identity(callback)
        customer = get_or_create_telegram_customer(db, business.id, telegram_user_id, full_name, username)
        data = await state.get_data()
        cart = data.get("cart") or []
        if not cart:
            await state.clear()
            await callback.message.answer(order_text("cancelled", customer.language))
            await callback.answer()
            return

        order = create_order_with_items(
            db=db,
            business_id=business.id,
            customer_id=customer.id,
            customer_name=data["customer_name"],
            phone=data["phone"],
            address=data["address"],
            comment=data.get("comment"),
            items=[
                {"product_id": int(item["product_id"]), "quantity": int(item["quantity"])}
                for item in cart
            ],
        )
        save_conversation_message(
            db=db,
            business_id=business.id,
            customer_id=customer.id,
            message_text=f"order created: {order.id}",
            sender_type="system",
            intent="order_created",
        )
        await notify_admin_order(callback.message, customer, business.id, order, None)
        await state.clear()
        await callback.message.answer(text_for("created", customer.language))
        await callback.answer()
    finally:
        db.close()


@router.message(F.contact)
async def handle_contact_message(message: Message) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(
            db=db,
            business_id=business.id,
            telegram_user_id=telegram_user_id,
            full_name=full_name,
            username=username,
        )

        contact = message.contact
        if contact is None or contact.user_id != message.from_user.id:
            await message.answer(t(customer.language, "own_contact_required"))
            return

        normalized_phone = normalize_uz_phone(contact.phone_number)
        if normalized_phone is None:
            await message.answer(invalid_phone_text(customer.language), reply_markup=contact_request_keyboard(customer.language))
            return

        customer.phone = normalized_phone
        db.commit()
        db.refresh(customer)

        save_conversation_message(
            db=db,
            business_id=business.id,
            customer_id=customer.id,
            message_text=f"phone shared: {normalized_phone}",
            sender_type="customer",
            intent="phone_shared",
        )

        if customer.pending_operator_message:
            notification_sent = await notify_admin(
                message=message,
                customer=customer,
                customer_message=customer.pending_operator_message,
                ai_reply=customer.pending_operator_ai_reply or "",
                business_id=business.id,
                intent=customer.pending_operator_intent or "unknown",
                confidence=float(customer.pending_operator_confidence or 0),
            )
            if notification_sent:
                clear_pending_operator_context(db, customer)

            await message.answer(t(customer.language, "phone_saved_operator"))
            return

        await message.answer(t(customer.language, "phone_saved"))
    finally:
        db.close()


@router.message(F.text)
async def handle_text_message(message: Message, state: FSMContext) -> None:
    db = SessionLocal()
    try:
        business = get_configured_business(db)
        if business is None:
            await message.answer(t("uz_latin", "setup_not_ready"))
            return

        customer_message = message.text or ""
        telegram_user_id, full_name, username = get_telegram_identity(message)
        customer = get_or_create_telegram_customer(
            db=db,
            business_id=business.id,
            telegram_user_id=telegram_user_id,
            full_name=full_name,
            username=username,
        )

        if customer.pending_operator_message and not customer.phone:
            normalized_phone = normalize_uz_phone(customer_message)
            if normalized_phone is None:
                await message.answer(
                    invalid_phone_text(customer.language),
                    reply_markup=contact_request_keyboard(customer.language),
                )
                return

            customer.phone = normalized_phone
            db.commit()
            db.refresh(customer)
            save_conversation_message(
                db=db,
                business_id=business.id,
                customer_id=customer.id,
                message_text=f"phone shared: {normalized_phone}",
                sender_type="customer",
                intent="phone_shared",
            )
            notification_sent = await notify_admin(
                message=message,
                customer=customer,
                customer_message=customer.pending_operator_message,
                ai_reply=customer.pending_operator_ai_reply or "",
                business_id=business.id,
                intent=customer.pending_operator_intent or "unknown",
                confidence=float(customer.pending_operator_confidence or 0),
            )
            if notification_sent:
                clear_pending_operator_context(db, customer)
            await message.answer(t(customer.language, "phone_saved_operator"))
            return

        save_conversation_message(
            db=db,
            business_id=business.id,
            customer_id=customer.id,
            message_text=customer_message,
            sender_type="customer",
        )

        await message.bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)
        try:
            ai_result = await ai_service.generate_customer_reply(
                db=db,
                business_id=business.id,
                customer_id=customer.id,
                customer_message=customer_message,
            )
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass

            response_text = t(customer.language, "error_fallback")
            try:
                save_ai_error_log(
                    db=db,
                    business_id=business.id,
                    customer_id=customer.id,
                    customer_message=customer_message,
                    fallback_reply=response_text,
                    error_message=str(exc),
                )
            except Exception:
                db.rollback()

            await message.answer(response_text)
            if customer_has_contact(customer):
                await notify_admin(
                    message=message,
                    customer=customer,
                    customer_message=customer_message,
                    ai_reply=response_text,
                    business_id=business.id,
                    intent="unknown",
                    confidence=0.0,
                    error_message=str(exc),
                )
            else:
                save_pending_operator_context(
                    db=db,
                    customer=customer,
                    customer_message=customer_message,
                    ai_reply=response_text,
                    intent="unknown",
                    confidence=0.0,
                )
                await message.answer(
                    t(customer.language, "request_phone_for_operator"),
                    reply_markup=contact_request_keyboard(customer.language),
                )
            return

        response_text = ai_result["reply"]
        recommended_product = get_order_button_product(db, business.id, customer_message, ai_result)
        await message.answer(
            response_text,
            reply_markup=(
                start_order_keyboard(customer.language, recommended_product.id)
                if recommended_product is not None
                else start_order_keyboard(customer.language)
                if should_show_generic_order_button(ai_result)
                else None
            ),
        )

        if not ai_reply_already_saved(db, business.id, customer.id, response_text):
            save_conversation_message(
                db=db,
                business_id=business.id,
                customer_id=customer.id,
                message_text=response_text,
                sender_type="ai",
                intent=ai_result["intent"],
            )

        if ai_result.get("needs_operator") is True:
            intent = ai_result.get("intent", "unknown")
            confidence = ai_result.get("confidence", 0.0)
            if customer_has_contact(customer):
                await notify_admin(
                    message=message,
                    customer=customer,
                    customer_message=customer_message,
                    ai_reply=response_text,
                    business_id=business.id,
                    intent=intent,
                    confidence=confidence,
                )
            else:
                save_pending_operator_context(
                    db=db,
                    customer=customer,
                    customer_message=customer_message,
                    ai_reply=response_text,
                    intent=intent,
                    confidence=confidence,
                )
                await message.answer(
                    t(customer.language, "request_phone_for_operator"),
                    reply_markup=contact_request_keyboard(customer.language),
                )
    finally:
        db.close()


