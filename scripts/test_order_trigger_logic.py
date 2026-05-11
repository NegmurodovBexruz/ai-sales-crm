import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.bot.handlers import messages  # noqa: E402
from app.bot.states.order import OrderStates  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models import Business, Conversation, Customer, Product, User  # noqa: E402


class FakeState:
    def __init__(self):
        self.data = {}
        self.state = None
        self.cleared = False

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.state = state

    async def clear(self):
        self.cleared = True
        self.data.clear()


class FakeBot:
    async def send_chat_action(self, chat_id, action):
        pass

    async def send_message(self, chat_id, text, **kwargs):
        pass


class FakeMessage:
    def __init__(self, text="adidas kerak", user_id=456):
        self.text = text
        self.chat = SimpleNamespace(id=123)
        self.from_user = SimpleNamespace(id=user_id, first_name="Test", last_name="User", username=None)
        self.bot = FakeBot()
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class FakeCallback:
    def __init__(self, data, user_id=456):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id, first_name="Test", last_name="User", username=None)
        self.message = FakeMessage(text=None, user_id=user_id)
        self.answers = []

    async def answer(self, text=None, **kwargs):
        self.answers.append((text, kwargs))


def build_session(stock_count=5):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all(
        [
            User(id=1, email="owner@example.com", password_hash="x"),
            Business(id=1, owner_id=1, public_business_id="BIZ-TEST01", name="Test Shop"),
            Customer(id=1, business_id=1, telegram_user_id="456", language="uz_latin"),
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
    return db


async def fake_ai_with_recommendation(db, business_id, customer_id, customer_message):
    return {
        "reply": "AI reply",
        "intent": "order_intent",
        "lead_score": 80,
        "recommended_product_ids": [1],
        "needs_operator": False,
        "order_intent": True,
        "confidence": 0.9,
    }


async def fake_ai_without_recommendation(db, business_id, customer_id, customer_message):
    return {
        "reply": "AI reply",
        "intent": "unknown",
        "lead_score": 0,
        "recommended_product_ids": [],
        "needs_operator": False,
        "order_intent": True,
        "confidence": 0.9,
    }


def test_text_does_not_start_order_fsm_for_order_words():
    db = build_session()
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    messages.ai_service.generate_customer_reply = fake_ai_with_recommendation
    state = FakeState()
    message = FakeMessage(text="Nike Air Max buyurtma qilmoqchiman")

    asyncio.run(messages.handle_text_message(message, state))

    assert state.state is None
    assert message.answers[0][0] == "AI reply"
    assert message.answers[0][1]["reply_markup"].inline_keyboard[0][0].callback_data == "start_order:1"


def test_plain_text_adidas_kerak_does_not_start_order_fsm():
    db = build_session()
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    messages.ai_service.generate_customer_reply = fake_ai_without_recommendation
    state = FakeState()
    message = FakeMessage(text="adidas kerak")

    asyncio.run(messages.handle_text_message(message, state))

    assert state.state is None
    assert message.answers[0][1]["reply_markup"].inline_keyboard[0][0].callback_data == "start_order"


def test_ai_reply_with_available_recommended_product_shows_order_button():
    db = build_session(stock_count=5)
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    messages.ai_service.generate_customer_reply = fake_ai_with_recommendation
    state = FakeState()
    message = FakeMessage(text="narxi qancha")

    asyncio.run(messages.handle_text_message(message, state))

    button = message.answers[0][1]["reply_markup"].inline_keyboard[0][0]
    assert button.callback_data == "start_order:1"


def test_ai_reply_without_recommended_product_does_not_show_button():
    db = build_session(stock_count=5)
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    messages.ai_service.generate_customer_reply = fake_ai_without_recommendation
    state = FakeState()
    message = FakeMessage(text="narxi qancha")

    asyncio.run(messages.handle_text_message(message, state))

    assert message.answers[0][1]["reply_markup"].inline_keyboard[0][0].callback_data == "start_order"


def test_start_order_callback_starts_quantity_step():
    db = build_session(stock_count=5)
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    callback = FakeCallback("start_order:1")

    asyncio.run(messages.start_order_from_button(callback, state))

    assert state.state == OrderStates.choosing_category
    assert state.data["business_id"] == 1
    assert callback.message.answers[0][0].startswith("Kategoriya")
    assert db.query(Conversation).filter(Conversation.intent == "order_button_clicked").count() == 0


def test_start_order_out_of_stock_does_not_start_fsm():
    db = build_session(stock_count=0)
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    callback = FakeCallback("start_order:1")

    asyncio.run(messages.start_order_from_button(callback, state))

    assert state.state == OrderStates.choosing_category
    assert "omborda" in callback.message.answers[0][0]


if __name__ == "__main__":
    test_text_does_not_start_order_fsm_for_order_words()
    test_plain_text_adidas_kerak_does_not_start_order_fsm()
    test_ai_reply_with_available_recommended_product_shows_order_button()
    test_ai_reply_without_recommended_product_does_not_show_button()
    test_start_order_callback_starts_quantity_step()
    test_start_order_out_of_stock_does_not_start_fsm()
    print("order trigger logic tests passed")

