from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.order import Order
from app.models.operator_assignment import OperatorAssignment
from app.models.product import Product
from app.models.telegram_operator import TelegramOperator
from app.services.conversation_service import save_conversation_message
from app.services.notification_service import notify_business_operators
from app.services.operator_assignment_service import (
    cancel_assignment_by_order,
    complete_assignment_by_order,
    create_assignment,
    get_active_assignment,
)
from app.services.order_service import (
    InsufficientStockError,
    OrderNotFoundError,
    cancel_order,
    mark_order_done,
)

router = Router()

ORDER_DONE_CUSTOMER_MESSAGES = {
    "uz_latin": "Buyurtmangiz tasdiqlandi. Tez orada yetkazib berish bo‘yicha bog‘lanamiz.",
    "uz_cyrillic": "Буюртмангиз тасдиқланди. Тез орада етказиб бериш бўйича боғланамиз.",
    "ru": "Ваш заказ подтверждён. Скоро свяжемся с вами по доставке.",
}

ORDER_CANCEL_CUSTOMER_MESSAGES = {
    "uz_latin": "Buyurtmangiz bekor qilindi. Batafsil ma’lumot uchun operator bilan bog‘lanishingiz mumkin.",
    "uz_cyrillic": "Буюртмангиз бекор қилинди. Батафсил маълумот учун оператор билан боғланишингиз мумкин.",
    "ru": "Ваш заказ отменён. За подробностями можете связаться с оператором.",
}


def is_admin_callback(callback: CallbackQuery) -> bool:
    chat_id = str(callback.message.chat.id) if callback.message else None
    user_id = str(callback.from_user.id) if callback.from_user else None
    db = SessionLocal()
    try:
        operator = db.scalar(
            select(TelegramOperator).where(
                TelegramOperator.is_active.is_(True),
                TelegramOperator.telegram_chat_id.in_([value for value in (chat_id, user_id) if value]),
            )
        )
        if operator is not None:
            return True
    finally:
        db.close()

    return False


def get_callback_operator(db, callback: CallbackQuery, business_id: int) -> TelegramOperator | None:
    chat_id = str(callback.message.chat.id) if callback.message else None
    user_id = str(callback.from_user.id) if callback.from_user else None
    ids = [value for value in (chat_id, user_id) if value]
    if not ids:
        return None
    return db.scalar(
        select(TelegramOperator).where(
            TelegramOperator.business_id == business_id,
            TelegramOperator.is_active.is_(True),
            TelegramOperator.telegram_chat_id.in_(ids),
        )
    )


def can_operate_order(db, callback: CallbackQuery, order: Order) -> bool:
    operator = get_callback_operator(db, callback, order.business_id)
    if operator is None:
        return False
    assignment = get_active_assignment(db, order.business_id, order.customer_id)
    return assignment is not None and assignment.operator_id == operator.id


async def send_assigned_customer_details(callback: CallbackQuery, customer, operator: TelegramOperator) -> None:
    username = f"@{customer.username}" if customer.username else "-"
    text = (
        "Customer sizga biriktirildi\n\n"
        f"Customer ID: {customer.id}\n"
        f"Ism: {customer.full_name or '-'}\n"
        f"Username: {username}\n"
        f"Telefon: {customer.phone or '-'}\n"
        f"Telegram ID: {customer.telegram_user_id}"
    )
    await callback.bot.send_message(operator.telegram_chat_id, text)


@router.callback_query(F.data.startswith("operator_claim_customer:"))
async def operator_claim_customer(callback: CallbackQuery) -> None:
    customer_id = parse_order_id(callback.data, "operator_claim_customer:")
    if customer_id is None:
        await callback.answer("Invalid customer", show_alert=True)
        return

    db = SessionLocal()
    try:
        from app.models.customer import Customer

        customer = db.scalar(select(Customer).where(Customer.id == customer_id))
        if customer is None:
            await callback.answer("Customer not found", show_alert=True)
            return
        operator = get_callback_operator(db, callback, customer.business_id)
        if operator is None:
            await callback.answer("Siz bu business operatori emassiz.", show_alert=True)
            return
        assignment = get_active_assignment(db, customer.business_id, customer.id)
        if assignment is None:
            create_assignment(db, customer.business_id, customer.id, operator.id)
            await callback.answer("✅ Customer sizga biriktirildi.", show_alert=True)
            await send_assigned_customer_details(callback, customer, operator)
            return
        if assignment.operator_id == operator.id:
            await callback.answer("Bu customer allaqachon sizga biriktirilgan.", show_alert=True)
            return
        await callback.answer("Bu customer boshqa operatorga biriktirilgan.", show_alert=True)
    finally:
        db.close()


@router.callback_query(F.data.startswith("operator_claim_order:"))
async def operator_claim_order(callback: CallbackQuery) -> None:
    order_id = parse_order_id(callback.data, "operator_claim_order:")
    if order_id is None:
        await callback.answer("Invalid order", show_alert=True)
        return

    db = SessionLocal()
    try:
        order = db.scalar(select(Order).where(Order.id == order_id))
        if order is None:
            await callback.answer("Order not found", show_alert=True)
            return
        operator = get_callback_operator(db, callback, order.business_id)
        if operator is None:
            await callback.answer("Siz bu business operatori emassiz.", show_alert=True)
            return
        assignment = get_active_assignment(db, order.business_id, order.customer_id)
        if assignment is None:
            create_assignment(db, order.business_id, order.customer_id, operator.id, order.id)
            await callback.answer("✅ Customer sizga biriktirildi.", show_alert=True)
        elif assignment.operator_id == operator.id:
            if assignment.order_id is None:
                assignment.order_id = order.id
                db.commit()
            await callback.answer("Bu customer allaqachon sizga biriktirilgan.", show_alert=True)
        else:
            await callback.answer("Bu customer boshqa operatorga biriktirilgan.", show_alert=True)
            return

        await callback.bot.send_message(
            operator.telegram_chat_id,
            f"Order #{order.id} sizga biriktirildi. Done/Cancel tugmalaridan foydalaning.",
            reply_markup=admin_order_actions_keyboard(order.id),
        )
    finally:
        db.close()


def low_stock_warning_text(product: Product) -> str | None:
    if product.stock_count == 0:
        return f"⚠️ {product.name} tugadi. Stock: 0"
    if 1 <= product.stock_count <= 10:
        return f"⚠️ {product.name} kam qoldi. Stock: {product.stock_count}"
    return None


def customer_done_message(language: str) -> str:
    return ORDER_DONE_CUSTOMER_MESSAGES.get(language, ORDER_DONE_CUSTOMER_MESSAGES["uz_latin"])


def customer_cancel_message(language: str) -> str:
    return ORDER_CANCEL_CUSTOMER_MESSAGES.get(language, ORDER_CANCEL_CUSTOMER_MESSAGES["uz_latin"])


def parse_order_id(callback_data: str | None, prefix: str) -> int | None:
    if not callback_data or not callback_data.startswith(prefix):
        return None
    try:
        return int(callback_data.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


async def remove_admin_buttons(callback: CallbackQuery) -> None:
    if callback.message is None:
        return
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


async def notify_customer(callback: CallbackQuery, order: Order, text: str) -> None:
    if order.customer is None:
        return
    try:
        await callback.bot.send_message(order.customer.telegram_user_id, text)
    except Exception:
        pass


@router.callback_query(F.data.startswith("admin_order_done:"))
async def admin_order_done(callback: CallbackQuery) -> None:
    if not is_admin_callback(callback):
        await callback.answer("Unauthorized", show_alert=True)
        return

    order_id = parse_order_id(callback.data, "admin_order_done:")
    if order_id is None:
        await callback.answer("Invalid order", show_alert=True)
        return

    db = SessionLocal()
    try:
        order = db.scalar(select(Order).where(Order.id == order_id))
        if order is None:
            await callback.answer("Order not found", show_alert=True)
            return
        if not can_operate_order(db, callback, order):
            await callback.answer("Bu order boshqa operatorga biriktirilgan.", show_alert=True)
            return
        if order.status == "done":
            await callback.answer(f"Order #{order.id} is already done.", show_alert=True)
            return

        try:
            order = mark_order_done(db, order_id, business_id=order.business_id)
        except OrderNotFoundError:
            await callback.answer("Order not found", show_alert=True)
            return
        except InsufficientStockError as exc:
            await callback.answer(str(exc), show_alert=True)
            return

        product = db.scalar(select(Product).where(Product.id == order.product_id))
        complete_assignment_by_order(db, order.id)
        save_conversation_message(
            db=db,
            business_id=order.business_id,
            customer_id=order.customer_id,
            message_text=f"order done: {order.id}",
            sender_type="system",
            intent="order_done",
        )

        await remove_admin_buttons(callback)
        if callback.message is not None:
            await callback.message.answer(f"✅ Order #{order.id} done. Stock updated.")
        await notify_business_operators(
            db=db,
            bot=callback.bot,
            business_id=order.business_id,
            text=f"Order #{order.id} done. Stock updated.",
        )
        await notify_customer(callback, order, customer_done_message(order.customer.language))

        if product is not None:
            warning = low_stock_warning_text(product)
            if warning:
                await notify_business_operators(db=db, bot=callback.bot, business_id=order.business_id, text=warning)
        await callback.answer()
    finally:
        db.close()


@router.callback_query(F.data.startswith("admin_order_cancel:"))
async def admin_order_cancel(callback: CallbackQuery) -> None:
    if not is_admin_callback(callback):
        await callback.answer("Unauthorized", show_alert=True)
        return

    order_id = parse_order_id(callback.data, "admin_order_cancel:")
    if order_id is None:
        await callback.answer("Invalid order", show_alert=True)
        return

    db = SessionLocal()
    try:
        order = db.scalar(select(Order).where(Order.id == order_id))
        if order is None:
            await callback.answer("Order not found", show_alert=True)
            return
        if not can_operate_order(db, callback, order):
            await callback.answer("Bu order boshqa operatorga biriktirilgan.", show_alert=True)
            return
        if order.status == "done":
            await callback.answer("Done order cannot be cancelled.", show_alert=True)
            return

        try:
            order = cancel_order(db, order_id, business_id=order.business_id)
        except OrderNotFoundError:
            await callback.answer("Order not found", show_alert=True)
            return
        cancel_assignment_by_order(db, order.id)

        save_conversation_message(
            db=db,
            business_id=order.business_id,
            customer_id=order.customer_id,
            message_text=f"order cancelled: {order.id}",
            sender_type="system",
            intent="order_cancelled",
        )

        await remove_admin_buttons(callback)
        if callback.message is not None:
            await callback.message.answer(f"❌ Order #{order.id} cancelled.")
        await notify_business_operators(
            db=db,
            bot=callback.bot,
            business_id=order.business_id,
            text=f"Order #{order.id} cancelled.",
        )
        await notify_customer(callback, order, customer_cancel_message(order.customer.language))
        await callback.answer()
    finally:
        db.close()
