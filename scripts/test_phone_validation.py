import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.bot.handlers import messages  # noqa: E402
from app.bot.states.order import OrderStates  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.models import Business, Customer, User  # noqa: E402
from app.utils.phone import is_valid_uz_phone, normalize_uz_phone  # noqa: E402


class FakeState:
    def __init__(self, data=None):
        self.data = data or {}
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


class FakeMessage:
    def __init__(self, text=None, contact=None, user_id=456):
        self.text = text
        self.contact = contact
        self.chat = SimpleNamespace(id=123)
        self.from_user = SimpleNamespace(id=user_id, first_name="Test", last_name="User", username=None)
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


class FakeCallback:
    def __init__(self, data, user_id=456):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id, first_name="Test", last_name="User", username=None)
        self.message = FakeMessage(user_id=user_id)
        self.answers = []

    async def answer(self, text=None, **kwargs):
        self.answers.append((text, kwargs))


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all(
        [
            User(id=1, email="owner@example.com", password_hash="x"),
            Business(id=1, owner_id=1, public_business_id="BIZ-TEST01", name="Test Shop"),
            Customer(id=1, business_id=1, telegram_user_id="456", language="uz_latin"),
        ]
    )
    db.commit()
    return db


def set_customer_defaults(db, full_name=None, phone=None):
    customer = db.get(Customer, 1)
    customer.full_name = full_name
    customer.phone = phone
    db.commit()
    db.refresh(customer)
    return customer


def test_valid_phone_formats_are_normalized():
    assert normalize_uz_phone("+998901234567") == "+998901234567"
    assert normalize_uz_phone("998901234567") == "+998901234567"
    assert normalize_uz_phone("901234567") == "+998901234567"
    assert normalize_uz_phone("90 123-45-67") == "+998901234567"
    assert is_valid_uz_phone("+998901234567") is True


def test_random_text_is_rejected():
    assert normalize_uz_phone("abc") is None
    assert is_valid_uz_phone("salom") is False


def test_invalid_phone_text_is_rejected_in_order_flow():
    db = build_session()
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    message = FakeMessage(text="abc")

    asyncio.run(messages.handle_order_phone_text(message, state))

    customer = db.get(Customer, 1)
    assert customer.phone is None
    assert "Telefon raqam noto" in message.answers[0][0]
    assert message.answers[0][1]["reply_markup"].keyboard[0][0].request_contact is True


def test_contact_from_another_user_is_rejected():
    db = build_session()
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    contact = SimpleNamespace(user_id=999, phone_number="+998901234567")
    message = FakeMessage(contact=contact, user_id=456)

    asyncio.run(messages.handle_order_phone_contact(message, state))

    customer = db.get(Customer, 1)
    assert customer.phone is None
    assert message.answers


def test_existing_full_name_shows_name_confirmation_keyboard():
    db = build_session()
    customer = set_customer_defaults(db, full_name="Test User")
    state = FakeState()
    message = FakeMessage()

    asyncio.run(messages.ask_name(message, state, customer))

    assert state.state == OrderStates.waiting_for_name
    assert "Test User" in message.answers[0][0]
    keyboard = message.answers[0][1]["reply_markup"]
    assert keyboard.inline_keyboard[0][0].callback_data == "order_name_use_existing"
    assert keyboard.inline_keyboard[1][0].callback_data == "order_name_enter_new"


def test_use_existing_name_moves_to_phone_step():
    db = build_session()
    set_customer_defaults(db, full_name="Test User")
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    callback = FakeCallback("order_name_use_existing")

    asyncio.run(messages.use_existing_order_name(callback, state))

    assert state.data["customer_name"] == "Test User"
    assert state.state == OrderStates.waiting_for_phone


def test_enter_new_name_waits_for_typed_name():
    db = build_session()
    set_customer_defaults(db, full_name="Test User")
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    callback = FakeCallback("order_name_enter_new")

    asyncio.run(messages.enter_new_order_name(callback, state))

    assert state.state == OrderStates.waiting_for_name
    assert callback.message.answers


def test_existing_phone_shows_phone_confirmation_keyboard():
    db = build_session()
    customer = set_customer_defaults(db, phone="+998901234567")
    state = FakeState()
    message = FakeMessage()

    asyncio.run(messages.ask_phone(message, state, customer))

    assert state.state == OrderStates.waiting_for_phone
    assert "+998901234567" in message.answers[0][0]
    keyboard = message.answers[0][1]["reply_markup"]
    assert keyboard.inline_keyboard[0][0].callback_data == "order_phone_use_existing"
    assert keyboard.inline_keyboard[1][0].callback_data == "order_phone_enter_new"


def test_use_existing_phone_moves_to_address_step():
    db = build_session()
    set_customer_defaults(db, phone="+998901234567")
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    callback = FakeCallback("order_phone_use_existing")

    asyncio.run(messages.use_existing_order_phone(callback, state))

    assert state.data["phone"] == "+998901234567"
    assert state.state == OrderStates.waiting_for_address


def test_enter_new_phone_shows_contact_request_keyboard():
    db = build_session()
    set_customer_defaults(db, phone="+998901234567")
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    callback = FakeCallback("order_phone_enter_new")

    asyncio.run(messages.enter_new_order_phone(callback, state))

    assert state.state == OrderStates.waiting_for_phone
    assert callback.message.answers[0][1]["reply_markup"].keyboard[0][0].request_contact is True


def test_valid_phone_text_is_normalized_in_order_flow():
    db = build_session()
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    message = FakeMessage(text="901234567")

    asyncio.run(messages.handle_order_phone_text(message, state))

    customer = db.get(Customer, 1)
    assert customer.phone == "+998901234567"
    assert state.data["phone"] == "+998901234567"
    assert state.state == OrderStates.waiting_for_address


def test_telegram_contact_saves_phone_and_continues_flow():
    db = build_session()
    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    state = FakeState()
    contact = SimpleNamespace(user_id=456, phone_number="998901234567")
    message = FakeMessage(contact=contact, user_id=456)

    asyncio.run(messages.handle_order_phone_contact(message, state))

    customer = db.get(Customer, 1)
    assert customer.phone == "+998901234567"
    assert state.data["phone"] == "+998901234567"
    assert state.state == OrderStates.waiting_for_address


def test_pending_operator_invalid_phone_text_is_rejected():
    db = build_session()
    customer = db.get(Customer, 1)
    customer.pending_operator_message = "Original question"
    customer.pending_operator_ai_reply = "Operator needed"
    customer.pending_operator_intent = "operator_request"
    customer.pending_operator_confidence = 0
    db.commit()

    messages.SessionLocal = lambda: db
    messages.settings.DEFAULT_BUSINESS_ID = 1
    message = FakeMessage(text="salom")
    state = FakeState()

    asyncio.run(messages.handle_text_message(message, state))

    customer = db.get(Customer, 1)
    assert customer.phone is None
    assert "Telefon raqam noto" in message.answers[0][0]
    assert message.answers[0][1]["reply_markup"].keyboard[0][0].request_contact is True


if __name__ == "__main__":
    test_valid_phone_formats_are_normalized()
    test_random_text_is_rejected()
    test_invalid_phone_text_is_rejected_in_order_flow()
    test_contact_from_another_user_is_rejected()
    test_existing_full_name_shows_name_confirmation_keyboard()
    test_use_existing_name_moves_to_phone_step()
    test_enter_new_name_waits_for_typed_name()
    test_existing_phone_shows_phone_confirmation_keyboard()
    test_use_existing_phone_moves_to_address_step()
    test_enter_new_phone_shows_contact_request_keyboard()
    test_valid_phone_text_is_normalized_in_order_flow()
    test_telegram_contact_saves_phone_and_continues_flow()
    test_pending_operator_invalid_phone_text_is_rejected()
    print("phone validation tests passed")

