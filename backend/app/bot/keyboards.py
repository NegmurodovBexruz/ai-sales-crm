from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.bot.i18n import t


def language_selection_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="O‘zbekcha", callback_data="lang:uz_latin"),
                InlineKeyboardButton(text="Ўзбекча", callback_data="lang:uz_cyrillic"),
            ],
            [InlineKeyboardButton(text="Русский", callback_data="lang:ru")],
        ]
    )


def phone_contact_keyboard() -> ReplyKeyboardMarkup:
    return contact_request_keyboard("uz_latin")


def contact_request_keyboard(language: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t(language, "btn_contact"), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def order_name_confirm_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language, "btn_use_name"), callback_data="order_name_use_existing")],
            [InlineKeyboardButton(text=t(language, "btn_enter_name"), callback_data="order_name_enter_new")],
        ]
    )


def order_phone_confirm_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language, "btn_use_phone"), callback_data="order_phone_use_existing")],
            [InlineKeyboardButton(text=t(language, "btn_enter_phone"), callback_data="order_phone_enter_new")],
        ]
    )


def order_confirmation_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language, "btn_confirm"), callback_data="order_confirm")],
            [InlineKeyboardButton(text=t(language, "btn_edit_cart"), callback_data="order_edit_cart")],
            [InlineKeyboardButton(text=t(language, "btn_cancel"), callback_data="order_cancel_full")],
        ]
    )


def admin_order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yakunlash", callback_data=f"admin_order_done:{order_id}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"admin_order_cancel:{order_id}"),
            ]
        ]
    )


def operator_claim_customer_keyboard(customer_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Men olaman", callback_data=f"operator_claim_customer:{customer_id}")]
        ]
    )


def operator_claim_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Men olaman", callback_data=f"operator_claim_order:{order_id}")]
        ]
    )


def start_order_keyboard(language: str, product_id: int | None = None) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(language, "btn_order"),
                    callback_data=f"start_order:{product_id}" if product_id is not None else "start_order",
                )
            ]
        ]
    )


def order_cancel_text(language: str) -> str:
    return t(language, "btn_cancel_order")


def category_keyboard(categories: list[tuple[str, str]], language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [InlineKeyboardButton(text=label, callback_data=f"order_category:{encoded}")]
                for label, encoded in categories
            ],
            [InlineKeyboardButton(text=order_cancel_text(language), callback_data="order_cancel_full")],
        ]
    )


def product_keyboard(products: list[tuple[str, int]], language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [InlineKeyboardButton(text=label, callback_data=f"order_product:{product_id}")]
                for label, product_id in products
            ],
            [InlineKeyboardButton(text=t(language, "btn_back"), callback_data="order_back_to_categories")],
            [InlineKeyboardButton(text=order_cancel_text(language), callback_data="order_cancel_full")],
        ]
    )


def cart_review_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language, "btn_add_more"), callback_data="order_add_more")],
            [InlineKeyboardButton(text=t(language, "btn_edit_cart"), callback_data="order_edit_cart")],
            [InlineKeyboardButton(text=t(language, "btn_done"), callback_data="order_finish_items")],
            [InlineKeyboardButton(text=t(language, "btn_cancel_order"), callback_data="order_cancel_full")],
        ]
    )


def cart_edit_keyboard(cart: list[dict], language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [
                    InlineKeyboardButton(
                        text=f"{item['product_name']} x {item['quantity']}",
                        callback_data=f"order_edit_item:{item['product_id']}",
                    )
                ]
                for item in cart
            ],
            [InlineKeyboardButton(text=t(language, "btn_back_to_cart"), callback_data="order_back_to_cart")],
            [InlineKeyboardButton(text=t(language, "btn_cancel_order"), callback_data="order_cancel_full")],
        ]
    )


def cart_item_actions_keyboard(product_id: int, language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language, "btn_change_quantity"), callback_data=f"order_change_qty:{product_id}")],
            [InlineKeyboardButton(text=t(language, "btn_remove"), callback_data=f"order_remove_item:{product_id}")],
            [InlineKeyboardButton(text=t(language, "btn_back_to_cart"), callback_data="order_back_to_cart")],
        ]
    )


def cancel_confirmation_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(language, "btn_yes_cancel"), callback_data="order_cancel_confirm")],
            [InlineKeyboardButton(text=t(language, "btn_back_to_cart"), callback_data="order_back_to_cart")],
        ]
    )
