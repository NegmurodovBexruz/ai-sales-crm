from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


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
    labels = {
        "uz_latin": "Telefon raqamni yuborish",
        "uz_cyrillic": "Телефон рақамни юбориш",
        "ru": "Отправить номер телефона",
    }
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=labels.get(language, labels["uz_latin"]), request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def order_name_confirm_keyboard(language: str) -> InlineKeyboardMarkup:
    labels = {
        "uz_latin": ("✅ Shu ismni ishlatish", "✏️ Boshqa ism yozish"),
        "uz_cyrillic": ("✅ Шу исмни ишлатиш", "✏️ Бошқа исм ёзиш"),
        "ru": ("✅ Использовать это имя", "✏️ Ввести другое имя"),
    }
    use_text, new_text = labels.get(language, labels["uz_latin"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=use_text, callback_data="order_name_use_existing")],
            [InlineKeyboardButton(text=new_text, callback_data="order_name_enter_new")],
        ]
    )


def order_phone_confirm_keyboard(language: str) -> InlineKeyboardMarkup:
    labels = {
        "uz_latin": ("✅ Shu raqamni ishlatish", "Boshqa raqam yuborish"),
        "uz_cyrillic": ("✅ Шу рақамни ишлатиш", "Бошқа рақам юбориш"),
        "ru": ("✅ Использовать этот номер", "Отправить другой номер"),
    }
    use_text, new_text = labels.get(language, labels["uz_latin"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=use_text, callback_data="order_phone_use_existing")],
            [InlineKeyboardButton(text=new_text, callback_data="order_phone_enter_new")],
        ]
    )


def order_confirmation_keyboard(language: str) -> InlineKeyboardMarkup:
    labels = {
        "uz_latin": ("✅ Tasdiqlash", "✏️ Savatni tahrirlash", "❌ Bekor qilish"),
        "uz_cyrillic": ("✅ Тасдиқлаш", "✏️ Саватни таҳрирлаш", "❌ Бекор қилиш"),
        "ru": ("✅ Подтвердить", "✏️ Изменить корзину", "❌ Отменить"),
    }
    confirm_text, edit_text, cancel_text = labels.get(language, labels["uz_latin"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=confirm_text, callback_data="order_confirm")],
            [InlineKeyboardButton(text=edit_text, callback_data="order_edit_cart")],
            [InlineKeyboardButton(text=cancel_text, callback_data="order_cancel_full")],
        ]
    )


def admin_order_actions_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Done", callback_data=f"admin_order_done:{order_id}"),
                InlineKeyboardButton(text="❌ Cancel", callback_data=f"admin_order_cancel:{order_id}"),
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
    labels = {
        "uz_latin": "Buyurtma berish",
        "uz_cyrillic": "Буюртма бериш",
        "ru": "Заказать",
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=labels.get(language, labels["uz_latin"]),
                    callback_data=f"start_order:{product_id}" if product_id is not None else "start_order",
                )
            ]
        ]
    )


def order_cancel_text(language: str) -> str:
    return {
        "uz_latin": "❌ Buyurtmani bekor qilish",
        "uz_cyrillic": "❌ Буюртмани бекор қилиш",
        "ru": "❌ Отменить заказ",
    }.get(language, "❌ Buyurtmani bekor qilish")


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
    back_text = {
        "uz_latin": "⬅️ Ortga",
        "uz_cyrillic": "⬅️ Ортга",
        "ru": "⬅️ Назад",
    }.get(language, "⬅️ Ortga")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            *[
                [InlineKeyboardButton(text=label, callback_data=f"order_product:{product_id}")]
                for label, product_id in products
            ],
            [InlineKeyboardButton(text=back_text, callback_data="order_back_to_categories")],
            [InlineKeyboardButton(text=order_cancel_text(language), callback_data="order_cancel_full")],
        ]
    )


def cart_review_keyboard(language: str) -> InlineKeyboardMarkup:
    labels = {
        "uz_latin": ("➕ Yana mahsulot qo‘shish", "✏️ Savatni tahrirlash", "✅ Tayyor", "❌ Buyurtmani bekor qilish"),
        "uz_cyrillic": ("➕ Яна маҳсулот қўшиш", "✏️ Саватни таҳрирлаш", "✅ Тайёр", "❌ Буюртмани бекор қилиш"),
        "ru": ("➕ Добавить товар", "✏️ Изменить корзину", "✅ Готово", "❌ Отменить заказ"),
    }
    add_more, edit, finish, cancel = labels.get(language, labels["uz_latin"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=add_more, callback_data="order_add_more")],
            [InlineKeyboardButton(text=edit, callback_data="order_edit_cart")],
            [InlineKeyboardButton(text=finish, callback_data="order_finish_items")],
            [InlineKeyboardButton(text=cancel, callback_data="order_cancel_full")],
        ]
    )


def cart_edit_keyboard(cart: list[dict], language: str) -> InlineKeyboardMarkup:
    labels = {
        "uz_latin": ("⬅️ Savatga qaytish", "❌ Buyurtmani bekor qilish"),
        "uz_cyrillic": ("⬅️ Саватга қайтиш", "❌ Буюртмани бекор қилиш"),
        "ru": ("⬅️ Вернуться в корзину", "❌ Отменить заказ"),
    }
    back, cancel = labels.get(language, labels["uz_latin"])
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
            [InlineKeyboardButton(text=back, callback_data="order_back_to_cart")],
            [InlineKeyboardButton(text=cancel, callback_data="order_cancel_full")],
        ]
    )


def cart_item_actions_keyboard(product_id: int, language: str) -> InlineKeyboardMarkup:
    labels = {
        "uz_latin": ("Sonini o‘zgartirish", "O‘chirish", "⬅️ Savatga qaytish"),
        "uz_cyrillic": ("Сонини ўзгартириш", "Ўчириш", "⬅️ Саватга қайтиш"),
        "ru": ("Изменить количество", "Удалить", "⬅️ Вернуться в корзину"),
    }
    change, remove, back = labels.get(language, labels["uz_latin"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=change, callback_data=f"order_change_qty:{product_id}")],
            [InlineKeyboardButton(text=remove, callback_data=f"order_remove_item:{product_id}")],
            [InlineKeyboardButton(text=back, callback_data="order_back_to_cart")],
        ]
    )


def cancel_confirmation_keyboard(language: str) -> InlineKeyboardMarkup:
    labels = {
        "uz_latin": ("✅ Ha, bekor qilish", "⬅️ Savatga qaytish"),
        "uz_cyrillic": ("✅ Ҳа, бекор қилиш", "⬅️ Саватга қайтиш"),
        "ru": ("✅ Да, отменить", "⬅️ Вернуться в корзину"),
    }
    yes, back = labels.get(language, labels["uz_latin"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=yes, callback_data="order_cancel_confirm")],
            [InlineKeyboardButton(text=back, callback_data="order_back_to_cart")],
        ]
    )
