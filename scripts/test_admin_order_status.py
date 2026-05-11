import sys
import asyncio
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.bot.handlers.admin_orders import (  # noqa: E402
    admin_order_cancel,
    admin_order_done,
    customer_cancel_message,
    customer_done_message,
    low_stock_warning_text,
)
from app.bot.handlers import admin_orders  # noqa: E402
from app.bot.handlers import messages  # noqa: E402
from app.bot.handlers.messages import notify_admin_order  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models import Business, Customer, Order, Product, TelegramOperator, User  # noqa: E402
from app.services.operator_assignment_service import create_assignment  # noqa: E402
from app.services.order_service import cancel_order, create_order, mark_order_done  # noqa: E402


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_order(db, stock_count=5, quantity=2):
    db.add_all(
        [
            User(id=1, email="owner@example.com", password_hash="x"),
            Business(id=1, owner_id=1, public_business_id="BIZ-TEST01", name="Test Shop"),
            Customer(id=1, business_id=1, telegram_user_id="123", language="ru"),
            TelegramOperator(
                id=1,
                business_id=1,
                name="Test Operator",
                telegram_chat_id="1398353639",
                is_active=True,
            ),
            Product(
                id=1,
                business_id=1,
                name="Nike Air Max",
                price=Decimal("100.00"),
                stock_count=stock_count,
            ),
        ]
    )
    db.commit()
    order = create_order(
        db=db,
        business_id=1,
        customer_id=1,
        product_id=1,
        quantity=quantity,
        total_price=Decimal("200.00"),
        customer_name="Test Customer",
        phone="+998901234567",
        address="Tashkent",
    )
    product = db.get(Product, 1)
    return order, product


def test_admin_done_decreases_stock():
    db = build_session()
    order, product = seed_order(db, stock_count=5, quantity=2)

    mark_order_done(db, order.id, business_id=1)

    db.refresh(order)
    db.refresh(product)
    assert order.status == "done"
    assert product.stock_count == 3


def test_repeated_done_does_not_decrease_stock_twice():
    db = build_session()
    order, product = seed_order(db, stock_count=5, quantity=2)

    mark_order_done(db, order.id, business_id=1)
    mark_order_done(db, order.id, business_id=1)

    db.refresh(product)
    assert product.stock_count == 3


def test_cancel_does_not_decrease_stock():
    db = build_session()
    order, product = seed_order(db, stock_count=5, quantity=2)

    cancel_order(db, order.id, business_id=1)

    db.refresh(order)
    db.refresh(product)
    assert order.status == "cancelled"
    assert product.stock_count == 5


def test_low_stock_notification_conditions():
    out = Product(id=10, business_id=1, name="Out Product", price=Decimal("1.00"), stock_count=0)
    low = Product(id=11, business_id=1, name="Low Product", price=Decimal("1.00"), stock_count=10)
    ok = Product(id=12, business_id=1, name="Ok Product", price=Decimal("1.00"), stock_count=11)

    assert low_stock_warning_text(out) == "⚠️ Out Product tugadi. Stock: 0"
    assert low_stock_warning_text(low) == "⚠️ Low Product kam qoldi. Stock: 10"
    assert low_stock_warning_text(ok) is None


def test_customer_notification_uses_language():
    assert customer_done_message("ru") == "Ваш заказ подтверждён. Скоро свяжемся с вами по доставке."
    assert customer_cancel_message("uz_latin").startswith("Buyurtmangiz bekor qilindi.")


class FakeBot:
    def __init__(self):
        self.sent_messages = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent_messages.append((chat_id, text, kwargs))


class FakeAdminMessage:
    def __init__(self, bot):
        self.bot = bot
        self.chat = SimpleNamespace(id=1398353639)
        self.answers = []
        self.reply_markup_removed = False

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))

    async def edit_reply_markup(self, reply_markup=None):
        self.reply_markup_removed = reply_markup is None


class FakeCallback:
    def __init__(self, data):
        self.data = data
        self.from_user = SimpleNamespace(id=1398353639)
        self.bot = FakeBot()
        self.message = FakeAdminMessage(self.bot)
        self.answers = []

    async def answer(self, text=None, **kwargs):
        self.answers.append((text, kwargs))


def test_admin_order_notification_includes_done_cancel_keyboard():
    db = build_session()
    order, product = seed_order(db)
    customer = db.get(Customer, 1)
    messages.SessionLocal = lambda: db
    bot = FakeBot()
    message = SimpleNamespace(bot=bot)
    create_assignment(db, order.business_id, order.customer_id, 1, order.id)

    asyncio.run(notify_admin_order(message, customer, 1, order, product))

    reply_markup = bot.sent_messages[0][2]["reply_markup"]
    done_button = reply_markup.inline_keyboard[0][0]
    cancel_button = reply_markup.inline_keyboard[0][1]
    assert done_button.text == "✅ Yakunlash"
    assert done_button.callback_data == f"admin_order_done:{order.id}"
    assert cancel_button.text == "❌ Bekor qilish"
    assert cancel_button.callback_data == f"admin_order_cancel:{order.id}"


def test_admin_done_callback_decreases_stock():
    db = build_session()
    order, product = seed_order(db, stock_count=5, quantity=2)
    admin_orders.SessionLocal = lambda: db
    create_assignment(db, order.business_id, order.customer_id, 1, order.id)

    callback = FakeCallback(f"admin_order_done:{order.id}")
    order_id = order.id
    asyncio.run(admin_order_done(callback))

    order = db.get(Order, order_id)
    product = db.get(Product, 1)
    assert order.status == "done"
    assert product.stock_count == 3
    assert callback.message.reply_markup_removed is True
    assert any("done" in text for text, _ in callback.message.answers)


def test_admin_cancel_callback_does_not_decrease_stock():
    db = build_session()
    order, product = seed_order(db, stock_count=5, quantity=2)
    admin_orders.SessionLocal = lambda: db
    create_assignment(db, order.business_id, order.customer_id, 1, order.id)

    callback = FakeCallback(f"admin_order_cancel:{order.id}")
    order_id = order.id
    asyncio.run(admin_order_cancel(callback))

    order = db.get(Order, order_id)
    product = db.get(Product, 1)
    assert order.status == "cancelled"
    assert product.stock_count == 5
    assert callback.message.reply_markup_removed is True
    assert any("cancelled" in text for text, _ in callback.message.answers)


if __name__ == "__main__":
    test_admin_done_decreases_stock()
    test_repeated_done_does_not_decrease_stock_twice()
    test_cancel_does_not_decrease_stock()
    test_low_stock_notification_conditions()
    test_customer_notification_uses_language()
    test_admin_order_notification_includes_done_cancel_keyboard()
    test_admin_done_callback_decreases_stock()
    test_admin_cancel_callback_does_not_decrease_stock()
    print("admin order status tests passed")

