import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.bot.keyboards import cart_review_keyboard, category_keyboard, product_keyboard  # noqa: E402
from backend.app.bot.handlers.messages import get_available_categories, get_available_products_for_category  # noqa: E402
from backend.app.db.base import Base  # noqa: E402
from backend.app.models import Business, Customer, Product, User  # noqa: E402
from backend.app.services.order_service import (  # noqa: E402
    InsufficientStockError,
    create_order_with_items,
    mark_order_done,
)


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed(db):
    db.add_all(
        [
            User(id=1, email="owner@example.com", password_hash="x"),
            Business(id=1, owner_id=1, public_business_id="BIZ-TEST01", name="Test Shop"),
            Customer(id=1, business_id=1, telegram_user_id="123", language="uz_latin"),
            Product(
                id=1,
                business_id=1,
                name="Nike Air Max",
                category="Shoes",
                price=Decimal("800000"),
                discount_price=Decimal("790000"),
                stock_count=5,
            ),
            Product(
                id=2,
                business_id=1,
                name="Adidas Hoodie",
                category="Clothes",
                price=Decimal("420000"),
                stock_count=2,
            ),
            Product(
                id=3,
                business_id=1,
                name="Sold Out",
                category="Sold",
                price=Decimal("100000"),
                stock_count=0,
            ),
        ]
    )
    db.commit()


def test_create_order_with_items_does_not_decrease_stock():
    db = build_session()
    seed(db)

    order = create_order_with_items(
        db=db,
        business_id=1,
        customer_id=1,
        customer_name="Ali",
        phone="+998901234567",
        address="Tashkent",
        comment=None,
        items=[{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}],
    )

    assert len(order.items) == 2
    assert order.total_price == Decimal("2000000.00")
    assert db.get(Product, 1).stock_count == 5
    assert db.get(Product, 2).stock_count == 2


def test_create_order_with_duplicate_product_validates_total_quantity():
    db = build_session()
    seed(db)

    try:
        create_order_with_items(
            db=db,
            business_id=1,
            customer_id=1,
            customer_name="Ali",
            phone="+998901234567",
            address="Tashkent",
            comment=None,
            items=[{"product_id": 2, "quantity": 2}, {"product_id": 2, "quantity": 1}],
        )
    except InsufficientStockError:
        db.rollback()
    else:
        raise AssertionError("Expected duplicate item quantity to be validated against stock")

    assert db.get(Product, 2).stock_count == 2


def test_done_decreases_all_items_once():
    db = build_session()
    seed(db)
    order = create_order_with_items(
        db,
        1,
        1,
        "Ali",
        "+998901234567",
        "Tashkent",
        None,
        [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}],
    )

    mark_order_done(db, order.id, business_id=1)
    assert db.get(Product, 1).stock_count == 3
    assert db.get(Product, 2).stock_count == 1

    mark_order_done(db, order.id, business_id=1)
    assert db.get(Product, 1).stock_count == 3
    assert db.get(Product, 2).stock_count == 1


def test_done_insufficient_stock_does_not_decrease_any_product():
    db = build_session()
    seed(db)
    order = create_order_with_items(
        db,
        1,
        1,
        "Ali",
        "+998901234567",
        "Tashkent",
        None,
        [{"product_id": 1, "quantity": 2}, {"product_id": 2, "quantity": 1}],
    )
    db.get(Product, 2).stock_count = 0
    db.commit()

    try:
        mark_order_done(db, order.id, business_id=1)
    except InsufficientStockError:
        db.rollback()
    else:
        raise AssertionError("Expected insufficient stock")

    assert db.get(Product, 1).stock_count == 5
    assert db.get(Product, 2).stock_count == 0


def test_order_keyboards_have_expected_navigation_buttons():
    categories = category_keyboard([("Shoes", "Shoes")], "uz_latin")
    products = product_keyboard([("Nike Air Max — 790 000 so'm", 1)], "uz_latin")
    cart = cart_review_keyboard("uz_latin")

    assert categories.inline_keyboard[-1][0].callback_data == "order_cancel_full"
    assert products.inline_keyboard[-2][0].callback_data == "order_back_to_categories"
    assert products.inline_keyboard[-1][0].callback_data == "order_cancel_full"
    assert [row[0].callback_data for row in cart.inline_keyboard] == [
        "order_add_more",
        "order_edit_cart",
        "order_finish_items",
        "order_cancel_full",
    ]


def test_category_and_product_helpers_only_show_available_products():
    db = build_session()
    seed(db)

    categories = get_available_categories(db, 1)
    shoes = get_available_products_for_category(db, 1, "Shoes")
    sold = get_available_products_for_category(db, 1, "Sold")

    assert [category[0] for category in categories] == ["Clothes", "Shoes"]
    assert [product.name for product in shoes] == ["Nike Air Max"]
    assert sold == []


if __name__ == "__main__":
    test_create_order_with_items_does_not_decrease_stock()
    test_create_order_with_duplicate_product_validates_total_quantity()
    test_done_decreases_all_items_once()
    test_done_insufficient_stock_does_not_decrease_any_product()
    test_order_keyboards_have_expected_navigation_buttons()
    test_category_and_product_helpers_only_show_available_products()
    print("multi item order tests passed")
