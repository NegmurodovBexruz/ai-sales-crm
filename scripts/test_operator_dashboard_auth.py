import sys
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.security import create_access_token  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Business, BusinessMember, Product, TelegramOperator, User  # noqa: E402


def build_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def seed(db):
    owner = User(id=1, email="owner@example.com", password_hash="x", full_name="Owner")
    admin = User(id=2, email="admin@example.com", password_hash="x", full_name="Admin")
    business = Business(
        id=1,
        owner_id=1,
        public_business_id="BIZ-TEST01",
        admin_join_code="ADM-TEST01",
        operator_code="OP-TEST01",
        name="Test Shop",
    )
    other_business = Business(
        id=2,
        owner_id=1,
        public_business_id="BIZ-TEST02",
        admin_join_code="ADM-TEST02",
        operator_code="OP-TEST02",
        name="Other Shop",
    )
    db.add_all(
        [
            owner,
            admin,
            business,
            other_business,
            BusinessMember(business_id=1, user_id=1, role="owner", status="active", approved_by_user_id=1),
            TelegramOperator(
                id=1,
                business_id=1,
                name="Active Operator",
                telegram_chat_id="123456789",
                username="active",
                is_active=True,
            ),
            TelegramOperator(
                id=2,
                business_id=1,
                name="Inactive Operator",
                telegram_chat_id="987654321",
                username="inactive",
                is_active=False,
            ),
            Product(id=1, business_id=1, name="Visible", price=Decimal("100.00"), stock_count=11),
            Product(id=2, business_id=1, name="Low", price=Decimal("50.00"), stock_count=3),
            Product(id=3, business_id=2, name="Hidden", price=Decimal("20.00"), stock_count=5),
        ]
    )
    db.commit()


def login(client, operator_code="OP-TEST01", telegram_chat_id="123456789"):
    return client.post(
        "/api/operator-auth/login",
        json={"operator_code": operator_code, "telegram_chat_id": telegram_chat_id},
    )


def test_active_operator_login_and_product_scope():
    client, SessionLocal = build_client()
    db = SessionLocal()
    seed(db)
    db.close()

    login_response = login(client)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    products_response = client.get("/api/operator/products", headers={"Authorization": f"Bearer {token}"})
    assert products_response.status_code == 200
    products = products_response.json()
    assert {product["name"] for product in products} == {"Visible", "Low"}
    assert all("business_id" not in product for product in products)

    owner_response = client.get("/api/products", headers={"Authorization": f"Bearer {token}"})
    assert owner_response.status_code == 401


def test_wrong_operator_code_fails():
    client, SessionLocal = build_client()
    db = SessionLocal()
    seed(db)
    db.close()

    assert login(client, operator_code="OP-WRONG").status_code == 401


def test_wrong_chat_id_fails():
    client, SessionLocal = build_client()
    db = SessionLocal()
    seed(db)
    db.close()

    assert login(client, telegram_chat_id="000").status_code == 401


def test_inactive_operator_fails():
    client, SessionLocal = build_client()
    db = SessionLocal()
    seed(db)
    db.close()

    assert login(client, telegram_chat_id="987654321").status_code == 401


def test_normal_user_token_cannot_access_operator_products():
    client, SessionLocal = build_client()
    db = SessionLocal()
    seed(db)
    db.close()

    user_token = create_access_token("1")
    response = client.get("/api/operator/products", headers={"Authorization": f"Bearer {user_token}"})
    assert response.status_code == 401


if __name__ == "__main__":
    test_active_operator_login_and_product_scope()
    test_wrong_operator_code_fails()
    test_wrong_chat_id_fails()
    test_inactive_operator_fails()
    test_normal_user_token_cannot_access_operator_products()
    print("operator dashboard auth tests passed")

