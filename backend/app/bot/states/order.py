from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    choosing_category = State()
    choosing_product = State()
    waiting_for_quantity = State()
    cart_review = State()
    editing_cart = State()
    editing_item_quantity = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_comment = State()
    confirmation = State()
