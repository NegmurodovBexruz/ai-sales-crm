import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))


class FakeFilter:
    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        return self

    def __eq__(self, other):
        return self

    def startswith(self, prefix):
        return self


class FakeRouter:
    def callback_query(self, *args, **kwargs):
        return lambda handler: handler

    def message(self, *args, **kwargs):
        return lambda handler: handler


class FakeDispatcher:
    def include_router(self, router):
        pass


class FakeStateDefinition:
    def __set_name__(self, owner, name):
        self.state = f"{owner.__name__}:{name}"


def install_aiogram_stub():
    if "aiogram" in sys.modules:
        return

    aiogram = types.ModuleType("aiogram")
    aiogram.Bot = object
    aiogram.Dispatcher = FakeDispatcher
    aiogram.F = FakeFilter()
    aiogram.Router = FakeRouter

    enums = types.ModuleType("aiogram.enums")
    enums.ChatAction = types.SimpleNamespace(TYPING="typing")

    filters = types.ModuleType("aiogram.filters")
    filters.CommandStart = lambda *args, **kwargs: True
    filters.StateFilter = lambda *args, **kwargs: True

    fsm_context = types.ModuleType("aiogram.fsm.context")
    fsm_context.FSMContext = object

    fsm_state = types.ModuleType("aiogram.fsm.state")
    fsm_state.State = FakeStateDefinition
    fsm_state.StatesGroup = object

    types_module = types.ModuleType("aiogram.types")
    types_module.CallbackQuery = object
    types_module.Message = object
    types_module.InlineKeyboardButton = lambda **kwargs: types.SimpleNamespace(**kwargs)
    types_module.InlineKeyboardMarkup = lambda **kwargs: types.SimpleNamespace(**kwargs)
    types_module.KeyboardButton = lambda **kwargs: types.SimpleNamespace(**kwargs)
    types_module.ReplyKeyboardMarkup = lambda **kwargs: types.SimpleNamespace(**kwargs)
    types_module.ReplyKeyboardRemove = lambda **kwargs: types.SimpleNamespace(**kwargs)

    sys.modules["aiogram"] = aiogram
    sys.modules["aiogram.enums"] = enums
    sys.modules["aiogram.filters"] = filters
    sys.modules["aiogram.fsm.context"] = fsm_context
    sys.modules["aiogram.fsm.state"] = fsm_state
    sys.modules["aiogram.types"] = types_module


install_aiogram_stub()

from app.bot.handlers import messages  # noqa: E402
from app.bot.states.order import OrderStates  # noqa: E402


class FakeSession:
    def close(self):
        pass


class FakeMessage:
    def __init__(self):
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append({"text": text, "reply_markup": reply_markup})


class FakeCallback:
    def __init__(self, data=None):
        self.data = data
        self.from_user = types.SimpleNamespace(id=123, first_name="Test", last_name="User", username=None)
        self.message = FakeMessage()
        self.answered = False

    async def answer(self, *args, **kwargs):
        self.answered = True


class FakeState:
    def __init__(self, data=None, state=None):
        self.data = dict(data or {})
        self.state = state
        self.cleared = False

    async def get_data(self):
        return dict(self.data)

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def set_state(self, state):
        self.state = getattr(state, "state", state)
        self.cleared = False

    async def get_state(self):
        return self.state

    async def clear(self):
        self.data = {}
        self.state = None
        self.cleared = True


def cart_item():
    return {
        "product_id": 1,
        "product_name": "Nike Air Max",
        "quantity": 1,
        "final_unit_price": "790000",
        "total_price": "790000",
    }


class OrderCancelFlowTest(unittest.TestCase):
    def setUp(self):
        self.session_patch = patch.object(messages, "SessionLocal", return_value=FakeSession())
        self.business_patch = patch.object(messages, "get_configured_business", return_value=None)
        self.session_patch.start()
        self.business_patch.start()

    def tearDown(self):
        self.business_patch.stop()
        self.session_patch.stop()

    def test_cancel_while_choosing_category_with_cart_returns_to_cart_review(self):
        state = FakeState(
            data={"cart": [cart_item()], "selected_category": "Shoes", "selected_product_id": 2},
            state=OrderStates.choosing_category.state,
        )
        callback = FakeCallback()

        asyncio.run(messages.cancel_order_flow(callback, state))

        self.assertFalse(state.cleared)
        self.assertEqual(state.state, OrderStates.choosing_category.state)
        self.assertEqual(state.data["cart"], [cart_item()])
        self.assertIn("Buyurtmani to‘liq bekor qilasizmi?", callback.message.answers[-1]["text"])
        self.assertIsNotNone(callback.message.answers[-1]["reply_markup"])
        self.assertTrue(callback.answered)

    def test_cancel_while_choosing_product_with_cart_returns_to_cart_review(self):
        state = FakeState(
            data={"cart": [cart_item()], "selected_category": "Shoes", "selected_product_id": 2},
            state=OrderStates.choosing_product.state,
        )
        callback = FakeCallback()

        asyncio.run(messages.cancel_order_flow(callback, state))

        self.assertFalse(state.cleared)
        self.assertEqual(state.state, OrderStates.choosing_product.state)
        self.assertEqual(state.data["cart"], [cart_item()])
        self.assertIn("Buyurtmani to‘liq bekor qilasizmi?", callback.message.answers[-1]["text"])
        self.assertTrue(callback.answered)

    def test_empty_cart_cancel_in_category_selection_clears_fsm(self):
        state = FakeState(data={"cart": []}, state=OrderStates.choosing_category.state)
        callback = FakeCallback()

        asyncio.run(messages.cancel_order_flow(callback, state))

        self.assertTrue(state.cleared)
        self.assertEqual(state.data, {})
        self.assertEqual(callback.message.answers[-1]["text"], "Buyurtma bekor qilindi.")
        self.assertTrue(callback.answered)

    def test_final_confirmation_cancel_clears_fsm(self):
        state = FakeState(data={"cart": [cart_item()]}, state=OrderStates.confirmation.state)
        callback = FakeCallback()

        asyncio.run(messages.cancel_order(callback, state))

        self.assertTrue(state.cleared)
        self.assertEqual(state.data, {})
        self.assertEqual(callback.message.answers[-1]["text"], "Buyurtma bekor qilindi.")
        self.assertTrue(callback.answered)

    def test_edit_cart_shows_cart_items_without_clearing_fsm(self):
        state = FakeState(data={"cart": [cart_item()]}, state=OrderStates.cart_review.state)
        callback = FakeCallback("order_edit_cart")

        asyncio.run(messages.order_edit_cart(callback, state))

        self.assertFalse(state.cleared)
        self.assertEqual(state.state, OrderStates.editing_cart.state)
        self.assertIn("Qaysi mahsulotni tahrirlaysiz?", callback.message.answers[-1]["text"])
        buttons = callback.message.answers[-1]["reply_markup"].inline_keyboard
        self.assertEqual(buttons[0][0].callback_data, "order_edit_item:1")
        self.assertTrue(callback.answered)

    def test_remove_last_cart_item_returns_to_category_selection(self):
        state = FakeState(data={"cart": [cart_item()]}, state=OrderStates.editing_cart.state)
        callback = FakeCallback("order_remove_item:1")

        business = types.SimpleNamespace(id=1)
        customer = types.SimpleNamespace(id=1, language="uz_latin")
        with patch.object(messages, "get_configured_business", return_value=business), patch.object(
            messages, "get_or_create_telegram_customer", return_value=customer
        ), patch.object(messages, "get_available_categories", return_value=[("Shoes", "Shoes")]):
            asyncio.run(messages.order_remove_item(callback, state))

        self.assertFalse(state.cleared)
        self.assertEqual(state.data["cart"], [])
        self.assertEqual(state.state, OrderStates.choosing_category.state)
        self.assertIn("Savat bo‘sh qoldi", callback.message.answers[-2]["text"])
        self.assertTrue(callback.answered)

    def test_cancel_confirm_clears_fsm(self):
        state = FakeState(data={"cart": [cart_item()]}, state=OrderStates.cart_review.state)
        callback = FakeCallback("order_cancel_confirm")

        asyncio.run(messages.order_cancel_confirm(callback, state))

        self.assertTrue(state.cleared)
        self.assertEqual(callback.message.answers[-1]["text"], "Buyurtma bekor qilindi.")
        self.assertTrue(callback.answered)


if __name__ == "__main__":
    unittest.main()
