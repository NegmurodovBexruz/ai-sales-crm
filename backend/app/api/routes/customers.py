from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import or_, select

from app.api.access import get_accessible_business_ids, require_business_admin_or_owner
from app.api.deps import CurrentUser, DbSession
from app.models.customer import Customer
from app.schemas.customer import CustomerLanguage, CustomerResponse

router = APIRouter(prefix="/customers", tags=["customers"])


@router.get("", response_model=list[CustomerResponse])
def list_customers(
    db: DbSession,
    current_user: CurrentUser,
    search: str | None = None,
    language: CustomerLanguage | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Customer]:
    accessible_ids = get_accessible_business_ids(db, current_user)
    if accessible_ids == []:
        return []
    query = select(Customer).order_by(Customer.created_at.desc()).limit(limit).offset(offset)
    if accessible_ids is not None:
        query = query.where(Customer.business_id.in_(accessible_ids))

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Customer.full_name.ilike(search_pattern),
                Customer.username.ilike(search_pattern),
                Customer.phone.ilike(search_pattern),
                Customer.telegram_user_id.ilike(search_pattern),
            )
        )

    if language:
        query = query.where(Customer.language == language)

    return list(db.scalars(query).all())


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(customer_id: int, db: DbSession, current_user: CurrentUser) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    require_business_admin_or_owner(db, current_user, customer.business_id)
    return customer
