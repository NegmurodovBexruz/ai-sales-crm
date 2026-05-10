import os
import sys
from pathlib import Path

from sqlalchemy import select

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(ROOT_DIR))

from backend.app.api.routes.auth import login, register
from backend.app.api.routes.businesses import create_business
from backend.app.api.routes.conversations import create_conversation, get_customer_conversation_history
from backend.app.api.routes.customers import list_customers
from backend.app.db.session import SessionLocal
from backend.app.models.business import Business
from backend.app.models.user import User
from backend.app.schemas.auth import UserLogin, UserRegister
from backend.app.schemas.business import BusinessCreate
from backend.app.schemas.conversation import ConversationCreate
from backend.app.services.customer_service import get_or_create_telegram_customer


TEST_EMAIL = os.getenv("TEST_EMAIL", "test-owner@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "strongpassword")


def main() -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == TEST_EMAIL))
        if user is None:
            user = register(
                UserRegister(email=TEST_EMAIL, password=TEST_PASSWORD, full_name="Test Owner"),
                db,
            )

        token = login(UserLogin(email=TEST_EMAIL, password=TEST_PASSWORD), db)
        if not token.access_token:
            raise RuntimeError("Login failed")

        business = db.scalar(select(Business).where(Business.owner_id == user.id))
        if business is None:
            business = create_business(BusinessCreate(name="Test Business"), db, user)

        customer = get_or_create_telegram_customer(
            db=db,
            business_id=business.id,
            telegram_user_id="telegram-test-001",
            full_name="Telegram Test Customer",
            username="telegram_test",
        )

        customers = list_customers(
            db=db,
            current_user=user,
            search="telegram-test-001",
            limit=100,
            offset=0,
        )
        customers_ok = any(item.id == customer.id for item in customers)

        customer_message = create_conversation(
            ConversationCreate(
                business_id=business.id,
                customer_id=customer.id,
                message_text="Salom",
                sender_type="customer",
                intent="greeting",
            ),
            db,
            user,
        )
        ai_message = create_conversation(
            ConversationCreate(
                business_id=business.id,
                customer_id=customer.id,
                message_text="Salom, qanday yordam beray?",
                sender_type="ai",
                intent="greeting",
            ),
            db,
            user,
        )

        history = get_customer_conversation_history(customer.id, db, user, limit=20, offset=0)
        created_ids = [customer_message.id, ai_message.id]
        history_ids = [item.id for item in history if item.id in created_ids]

        print(f"customers_ok {customers_ok}")
        print(f"conversations_saved {len(history_ids)}")
        print(f"history_order_ok {history_ids == created_ids}")
        print(f"customer_language {customer.language}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
