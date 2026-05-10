import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.db.base import Base  # noqa: E402
from backend.app.models import Business, Customer, Product, User  # noqa: E402
from backend.app.services.order_service import InsufficientStockError, create_order, mark_order_done  # noqa: E402


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def seed_data(db):
    user = User(id=1, email="owner@example.com", password_hash="x")
    business = Business(id=1, owner_id=1, public_business_id="BIZ-TEST01", name="Test Shop")
    customer = Customer(id=1, business_id=1, telegram_user_id="123", language="uz_latin")
    product = Product(id=1, business_id=1, name="Nike Air Max", price=Decimal("100.00"), stock_count=5)
    db.add_all([user, business, customer, product])
    db.commit()
    return product


def test_create_order_does_not_decrease_stock():
    db = build_session()
    product = seed_data(db)

    order = create_order(
        db=db,
        business_id=1,
        customer_id=1,
        product_id=1,
        quantity=2,
        total_price=Decimal("200.00"),
        customer_name="Test Customer",
        phone="+998901234567",
        address="Tashkent",
        comment=None,
    )

    db.refresh(product)
    assert order.status == "new"
    assert product.stock_count == 5


def test_mark_done_decreases_stock_and_sets_status():
    db = build_session()
    product = seed_data(db)
    order = create_order(
        db=db,
        business_id=1,
        customer_id=1,
        product_id=1,
        quantity=2,
        total_price=Decimal("200.00"),
        customer_name="Test Customer",
        phone="+998901234567",
        address="Tashkent",
    )

    done_order = mark_order_done(db, order.id)

    db.refresh(product)
    assert done_order.status == "done"
    assert product.stock_count == 3

    mark_order_done(db, order.id)
    db.refresh(product)
    assert product.stock_count == 3


def test_mark_done_fails_when_stock_is_insufficient():
    db = build_session()
    product = seed_data(db)
    order = create_order(
        db=db,
        business_id=1,
        customer_id=1,
        product_id=1,
        quantity=6,
        total_price=Decimal("600.00"),
        customer_name="Test Customer",
        phone="+998901234567",
        address="Tashkent",
    )

    try:
        mark_order_done(db, order.id)
    except InsufficientStockError:
        pass
    else:
        raise AssertionError("Expected InsufficientStockError")

    db.refresh(product)
    db.refresh(order)
    assert product.stock_count == 5
    assert order.status == "new"


if __name__ == "__main__":
    test_create_order_does_not_decrease_stock()
    test_mark_done_decreases_stock_and_sets_status()
    test_mark_done_fails_when_stock_is_insufficient()
    print("order flow backend tests passed")
