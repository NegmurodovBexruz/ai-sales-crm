from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer


def get_or_create_telegram_customer(
    db: Session,
    business_id: int,
    telegram_user_id: str,
    full_name: str | None,
    username: str | None,
    language: str = "uz_latin",
) -> Customer:
    customer = db.scalar(
        select(Customer).where(
            Customer.business_id == business_id,
            Customer.telegram_user_id == telegram_user_id,
        )
    )
    if customer is not None:
        changed = False
        if full_name is not None and customer.full_name != full_name:
            customer.full_name = full_name
            changed = True
        if username is not None and customer.username != username:
            customer.username = username
            changed = True
        if changed:
            db.commit()
            db.refresh(customer)
        return customer

    customer = Customer(
        business_id=business_id,
        telegram_user_id=telegram_user_id,
        full_name=full_name,
        username=username,
        language=language,
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer
