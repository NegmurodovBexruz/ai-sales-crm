from app.bot.i18n import t
from app.bot.keyboards import (
    cancel_confirmation_keyboard,
    cart_item_actions_keyboard,
    cart_review_keyboard,
    contact_request_keyboard,
    start_order_keyboard,
)


def inline_texts(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


def reply_texts(markup):
    return [button.text for row in markup.keyboard for button in row]


def test_i18n_falls_back_to_uz_latin():
    assert t("unknown", "btn_order") == "Buyurtma berish"
    assert t(None, "ask_name") == "Buyurtma uchun ismingizni yozing."


def test_order_buttons_are_uz_latin():
    assert inline_texts(start_order_keyboard("uz_latin")) == ["Buyurtma berish"]
    assert reply_texts(contact_request_keyboard("uz_latin")) == ["Telefon raqamni yuborish"]
    assert inline_texts(cart_review_keyboard("uz_latin")) == [
        "➕ Yana mahsulot qo‘shish",
        "✏️ Savatni tahrirlash",
        "✅ Tayyor",
        "❌ Buyurtmani bekor qilish",
    ]
    assert inline_texts(cart_item_actions_keyboard(1, "uz_latin")) == [
        "Sonini o‘zgartirish",
        "O‘chirish",
        "⬅️ Savatga qaytish",
    ]
    assert t("uz_latin", "ai_fallback").startswith("Hozir")
    assert t("uz_latin", "ask_phone") == "Telefon raqamingizni yuboring."
    assert t("uz_latin", "ask_address") == "Yetkazib berish manzilini yozing."


def test_order_buttons_are_uz_cyrillic():
    assert inline_texts(start_order_keyboard("uz_cyrillic")) == ["Буюртма бериш"]
    assert reply_texts(contact_request_keyboard("uz_cyrillic")) == ["Телефон рақамни юбориш"]
    assert inline_texts(cart_review_keyboard("uz_cyrillic")) == [
        "➕ Яна маҳсулот қўшиш",
        "✏️ Саватни таҳрирлаш",
        "✅ Тайёр",
        "❌ Буюртмани бекор қилиш",
    ]
    assert inline_texts(cart_item_actions_keyboard(1, "uz_cyrillic")) == [
        "Сонини ўзгартириш",
        "Ўчириш",
        "⬅️ Саватга қайтиш",
    ]
    assert t("uz_cyrillic", "ai_fallback").startswith("Ҳозир")
    assert t("uz_cyrillic", "ask_phone") == "Телефон рақамингизни юборинг."
    assert t("uz_cyrillic", "ask_address") == "Етказиб бериш манзилини ёзинг."


def test_order_buttons_are_russian():
    assert inline_texts(start_order_keyboard("ru")) == ["Заказать"]
    assert reply_texts(contact_request_keyboard("ru")) == ["Отправить номер телефона"]
    assert inline_texts(cart_review_keyboard("ru")) == [
        "➕ Добавить товар",
        "✏️ Изменить корзину",
        "✅ Готово",
        "❌ Отменить заказ",
    ]
    assert inline_texts(cart_item_actions_keyboard(1, "ru")) == [
        "Изменить количество",
        "Удалить",
        "⬅️ Вернуться в корзину",
    ]
    assert t("ru", "ai_fallback").startswith("Сейчас")
    assert t("ru", "ask_phone") == "Отправьте номер телефона."
    assert t("ru", "ask_address") == "Напишите адрес доставки."


def test_cancel_confirmation_is_language_specific():
    assert inline_texts(cancel_confirmation_keyboard("uz_latin")) == ["✅ Ha, bekor qilish", "⬅️ Savatga qaytish"]
    assert inline_texts(cancel_confirmation_keyboard("uz_cyrillic")) == ["✅ Ҳа, бекор қилиш", "⬅️ Саватга қайтиш"]
    assert inline_texts(cancel_confirmation_keyboard("ru")) == ["✅ Да, отменить", "⬅️ Вернуться в корзину"]
