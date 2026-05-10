import asyncio
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from app.db.base import Base  # noqa: E402
from app.models import Business, Customer, Order, Product, TelegramOperator, User  # noqa: E402
from app.services.notification_service import notify_business_operators  # noqa: E402
from app.services.operator_assignment_service import (  # noqa: E402
    cancel_assignment_by_order,
    complete_assignment_by_order,
    create_assignment,
    get_active_assignment,
)
from app.services.order_service import mark_order_done  # noqa: E402
from app.bot.handlers.admin_orders import can_operate_order  # noqa: E402


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, reply_markup=None):
        self.messages.append((str(chat_id), text, reply_markup))


class OperatorAssignmentServiceTest(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()

        self.user = User(
            email="owner@example.com",
            password_hash="hash",
            full_name="Owner",
            role="business_admin",
            global_role="user",
        )
        self.db.add(self.user)
        self.db.flush()
        self.business = Business(
            owner_id=self.user.id,
            public_business_id="BIZ-TEST01",
            name="Test business",
        )
        self.db.add(self.business)
        self.db.flush()
        self.customer = Customer(
            business_id=self.business.id,
            telegram_user_id="1001",
            full_name="Customer",
            language="uz_latin",
        )
        self.product = Product(
            business_id=self.business.id,
            name="Product",
            price=Decimal("100.00"),
            stock_count=5,
        )
        self.operator_one = TelegramOperator(
            business_id=self.business.id,
            name="Operator One",
            telegram_chat_id="2001",
            is_active=True,
        )
        self.operator_two = TelegramOperator(
            business_id=self.business.id,
            name="Operator Two",
            telegram_chat_id="2002",
            is_active=True,
        )
        self.db.add_all([self.customer, self.product, self.operator_one, self.operator_two])
        self.db.commit()
        self.db.refresh(self.customer)
        self.db.refresh(self.product)
        self.db.refresh(self.operator_one)
        self.db.refresh(self.operator_two)

    def tearDown(self):
        self.db.close()

    def create_order(self):
        order = Order(
            business_id=self.business.id,
            customer_id=self.customer.id,
            product_id=self.product.id,
            quantity=2,
            total_price=Decimal("200.00"),
            customer_name="Customer",
            phone="+998901234567",
            address="Address",
            status="new",
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def test_first_operator_claim_creates_assignment_and_second_gets_existing(self):
        first = create_assignment(self.db, self.business.id, self.customer.id, self.operator_one.id)
        second = create_assignment(self.db, self.business.id, self.customer.id, self.operator_two.id)

        self.assertEqual(first.id, second.id)
        self.assertEqual(second.operator_id, self.operator_one.id)
        self.assertEqual(second.status, "active")

    def test_order_done_completes_assignment_and_is_idempotent(self):
        order = self.create_order()
        create_assignment(self.db, self.business.id, self.customer.id, self.operator_one.id, order.id)

        done_order = mark_order_done(self.db, order.id, business_id=self.business.id)
        complete_assignment_by_order(self.db, order.id)
        self.db.refresh(self.product)
        stock_after_first_done = self.product.stock_count
        second_done = mark_order_done(self.db, order.id, business_id=self.business.id)
        self.db.refresh(self.product)

        self.assertEqual(done_order.status, "done")
        self.assertEqual(second_done.status, "done")
        self.assertEqual(stock_after_first_done, 3)
        self.assertEqual(self.product.stock_count, 3)
        self.assertIsNone(get_active_assignment(self.db, self.business.id, self.customer.id))

    def test_order_cancel_cancels_assignment(self):
        order = self.create_order()
        create_assignment(self.db, self.business.id, self.customer.id, self.operator_one.id, order.id)

        assignment = cancel_assignment_by_order(self.db, order.id)

        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.status, "cancelled")
        self.assertIsNone(get_active_assignment(self.db, self.business.id, self.customer.id))

    def test_notification_sends_to_active_operators(self):
        bot = FakeBot()

        sent = asyncio.run(notify_business_operators(self.db, bot, self.business.id, "Operator kerak", reply_markup="claim"))

        self.assertEqual(sent, 2)
        self.assertEqual([message[0] for message in bot.messages], ["2001", "2002"])
        self.assertTrue(all(message[2] == "claim" for message in bot.messages))

    def test_only_assigned_operator_can_operate_order(self):
        order = self.create_order()
        create_assignment(self.db, self.business.id, self.customer.id, self.operator_one.id, order.id)
        assigned_callback = SimpleNamespace(
            message=SimpleNamespace(chat=SimpleNamespace(id=self.operator_one.telegram_chat_id)),
            from_user=SimpleNamespace(id=self.operator_one.telegram_chat_id),
        )
        other_callback = SimpleNamespace(
            message=SimpleNamespace(chat=SimpleNamespace(id=self.operator_two.telegram_chat_id)),
            from_user=SimpleNamespace(id=self.operator_two.telegram_chat_id),
        )

        self.assertTrue(can_operate_order(self.db, assigned_callback, order))
        self.assertFalse(can_operate_order(self.db, other_callback, order))


if __name__ == "__main__":
    unittest.main()
