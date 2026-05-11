import sys
from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.api.deps import get_db  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Business, BusinessMember, Customer, Order, Product, TelegramOperator, User  # noqa: E402


def build_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    normal_user = User(
        email="user@example.com",
        password_hash="hash",
        full_name="Normal User",
        global_role="user",
        is_active=True,
    )
    super_admin = User(
        email="super@example.com",
        password_hash="hash",
        full_name="Super Admin",
        global_role="super_admin",
        is_active=True,
    )
    db.add_all([normal_user, super_admin])
    db.flush()

    business = Business(
        owner_id=normal_user.id,
        public_business_id="BIZ-SUPER1",
        name="Super Test Business",
        phone="+998901234567",
        description="Business description",
        business_knowledge_text="Knowledge text " * 80,
        knowledge_file_name="knowledge.docx",
        is_active=True,
    )
    db.add(business)
    db.flush()

    db.add(
        BusinessMember(
            business_id=business.id,
            user_id=normal_user.id,
            role="owner",
            status="active",
        )
    )
    customer = Customer(
        business_id=business.id,
        telegram_user_id="telegram-1",
        full_name="Customer One",
        phone="+998901111111",
        language="uz_latin",
    )
    product = Product(
        business_id=business.id,
        name="Product One",
        price=Decimal("120.00"),
        stock_count=5,
    )
    operator = TelegramOperator(
        business_id=business.id,
        name="Operator One",
        telegram_chat_id="10001",
        username="operator_one",
        is_active=True,
    )
    db.add_all([customer, product, operator])
    db.flush()
    db.add(
        Order(
            business_id=business.id,
            customer_id=customer.id,
            product_id=product.id,
            quantity=2,
            total_price=Decimal("240.00"),
            customer_name="Customer One",
            phone="+998901111111",
            address="Tashkent",
            status="new",
        )
    )
    db.commit()

    def override_get_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, normal_user.id, super_admin.id, business.id


def auth_headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}


def main() -> None:
    client, normal_user_id, super_admin_id, business_id = build_client()

    normal_stats = client.get("/api/super-admin/stats", headers=auth_headers(normal_user_id))
    assert normal_stats.status_code == 403

    super_stats = client.get("/api/super-admin/stats", headers=auth_headers(super_admin_id))
    assert super_stats.status_code == 200
    assert super_stats.json()["total_businesses"] == 1

    businesses = client.get("/api/super-admin/businesses", headers=auth_headers(super_admin_id))
    assert businesses.status_code == 200
    assert businesses.json()[0]["products_count"] == 1

    users = client.get("/api/super-admin/users", headers=auth_headers(super_admin_id))
    assert users.status_code == 200
    user_payload = users.json()[0]
    assert "password_hash" not in user_payload

    business_detail = client.get(f"/api/super-admin/businesses/{business_id}", headers=auth_headers(super_admin_id))
    assert business_detail.status_code == 200
    detail = business_detail.json()
    assert detail["business"]["id"] == business_id
    assert len(detail["business_knowledge"]["business_knowledge_text_preview"]) <= 500

    normal_update = client.patch(
        f"/api/super-admin/users/{normal_user_id}",
        headers=auth_headers(normal_user_id),
        json={"global_role": "super_admin"},
    )
    assert normal_update.status_code == 403

    super_update = client.patch(
        f"/api/super-admin/users/{normal_user_id}",
        headers=auth_headers(super_admin_id),
        json={"global_role": "super_admin"},
    )
    assert super_update.status_code == 200
    assert super_update.json()["global_role"] == "super_admin"
    assert "password_hash" not in super_update.json()

    print("super admin tests passed")


if __name__ == "__main__":
    main()

