from datetime import datetime, time, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.api.access import require_super_admin
from app.api.deps import CurrentUser, DbSession
from app.models.business import Business
from app.models.business_member import BusinessMember
from app.models.customer import Customer
from app.models.order import Order
from app.models.product import Product
from app.models.telegram_operator import TelegramOperator
from app.models.user import User
from app.schemas.super_admin import (
    SuperAdminBusinessDetail,
    SuperAdminBusinessKnowledge,
    SuperAdminBusinessSummary,
    SuperAdminBusinessUpdate,
    SuperAdminCustomerSummary,
    SuperAdminMemberSummary,
    SuperAdminOperatorSummary,
    SuperAdminOrderSummary,
    SuperAdminProductSummary,
    SuperAdminStats,
    SuperAdminUserDetail,
    SuperAdminUserMembership,
    SuperAdminUserSummary,
    SuperAdminUserUpdate,
)

router = APIRouter(prefix="/super-admin", tags=["super-admin"])


def count_scalar(db: DbSession, statement) -> int:
    return int(db.scalar(statement) or 0)


def today_start() -> datetime:
    return datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)


def ensure_super_admin(current_user: CurrentUser) -> None:
    require_super_admin(current_user)


def business_status(business: Business) -> str:
    return "active" if business.is_active else "inactive"


def business_summary(db: DbSession, business: Business) -> SuperAdminBusinessSummary:
    owners_count = count_scalar(
        db,
        select(func.count(BusinessMember.id)).where(
            BusinessMember.business_id == business.id,
            BusinessMember.role == "owner",
            BusinessMember.status == "active",
        ),
    )
    admins_count = count_scalar(
        db,
        select(func.count(BusinessMember.id)).where(
            BusinessMember.business_id == business.id,
            BusinessMember.role == "admin",
            BusinessMember.status == "active",
        ),
    )
    products_count = count_scalar(db, select(func.count(Product.id)).where(Product.business_id == business.id))
    orders_count = count_scalar(db, select(func.count(Order.id)).where(Order.business_id == business.id))
    customers_count = count_scalar(db, select(func.count(Customer.id)).where(Customer.business_id == business.id))
    active_operators_count = count_scalar(
        db,
        select(func.count(TelegramOperator.id)).where(
            TelegramOperator.business_id == business.id,
            TelegramOperator.is_active.is_(True),
        ),
    )
    return SuperAdminBusinessSummary(
        id=business.id,
        public_business_id=business.public_business_id,
        name=business.name,
        phone=business.phone,
        description=business.description,
        delivery_policy=business.delivery_policy,
        return_policy=business.return_policy,
        working_hours=business.working_hours,
        ai_tone=business.ai_tone,
        created_at=business.created_at,
        owners_count=owners_count,
        admins_count=admins_count,
        products_count=products_count,
        orders_count=orders_count,
        customers_count=customers_count,
        active_operators_count=active_operators_count,
        is_active=business.is_active,
        status=business_status(business),
    )


def member_summary(member: BusinessMember) -> SuperAdminMemberSummary:
    return SuperAdminMemberSummary(
        id=member.id,
        business_id=member.business_id,
        business_name=member.business.name if member.business else "",
        user_id=member.user_id,
        user_email=member.user.email if member.user else "",
        role=member.role,
        status=member.status,
        created_at=member.created_at,
    )


def user_membership_summary(member: BusinessMember) -> SuperAdminUserMembership:
    return SuperAdminUserMembership(
        id=member.id,
        business_id=member.business_id,
        business_name=member.business.name if member.business else "",
        role=member.role,
        status=member.status,
        created_at=member.created_at,
    )


def operator_summary(operator: TelegramOperator) -> SuperAdminOperatorSummary:
    return SuperAdminOperatorSummary(
        id=operator.id,
        business_id=operator.business_id,
        business_name=operator.business.name if operator.business else "",
        name=operator.name,
        telegram_chat_id=operator.telegram_chat_id,
        username=operator.username,
        is_active=operator.is_active,
        created_at=operator.created_at,
    )


def order_summary(order: Order) -> SuperAdminOrderSummary:
    return SuperAdminOrderSummary(
        id=order.id,
        business_id=order.business_id,
        business_name=order.business.name if order.business else "",
        customer_name=order.customer_name,
        phone=order.phone,
        product=order.product.name if order.product else None,
        quantity=order.quantity,
        total_price=order.total_price,
        status=order.status,
        created_at=order.created_at,
    )


def active_super_admin_count(db: DbSession) -> int:
    return count_scalar(
        db,
        select(func.count(User.id)).where(
            User.global_role == "super_admin",
            User.is_active.is_(True),
        ),
    )


def get_user_or_404(db: DbSession, user_id: int) -> User:
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_business_or_404(db: DbSession, business_id: int) -> Business:
    business = db.scalar(select(Business).where(Business.id == business_id))
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


@router.get("/stats", response_model=SuperAdminStats)
def get_stats(db: DbSession, current_user: CurrentUser) -> SuperAdminStats:
    ensure_super_admin(current_user)
    start = today_start()
    return SuperAdminStats(
        total_businesses=count_scalar(db, select(func.count(Business.id))),
        active_businesses=count_scalar(db, select(func.count(Business.id)).where(Business.is_active.is_(True))),
        total_users=count_scalar(db, select(func.count(User.id))),
        total_orders=count_scalar(db, select(func.count(Order.id))),
        total_customers=count_scalar(db, select(func.count(Customer.id))),
        total_products=count_scalar(db, select(func.count(Product.id))),
        total_operators=count_scalar(db, select(func.count(TelegramOperator.id))),
        new_businesses_today=count_scalar(db, select(func.count(Business.id)).where(Business.created_at >= start)),
        new_users_today=count_scalar(db, select(func.count(User.id)).where(User.created_at >= start)),
        orders_today=count_scalar(db, select(func.count(Order.id)).where(Order.created_at >= start)),
    )


@router.get("/businesses", response_model=list[SuperAdminBusinessSummary])
def list_businesses(
    db: DbSession,
    current_user: CurrentUser,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[SuperAdminBusinessSummary]:
    ensure_super_admin(current_user)
    query = select(Business).order_by(Business.created_at.desc()).limit(limit).offset(offset)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Business.name.ilike(pattern),
                Business.public_business_id.ilike(pattern),
                Business.phone.ilike(pattern),
                Business.description.ilike(pattern),
            )
        )
    return [business_summary(db, business) for business in db.scalars(query).all()]


@router.get("/businesses/{business_id}", response_model=SuperAdminBusinessDetail)
def get_business_detail(
    business_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> SuperAdminBusinessDetail:
    ensure_super_admin(current_user)
    business = get_business_or_404(db, business_id)
    members = list(
        db.scalars(
            select(BusinessMember)
            .options(joinedload(BusinessMember.business), joinedload(BusinessMember.user))
            .where(BusinessMember.business_id == business_id)
            .order_by(BusinessMember.created_at.desc())
        ).all()
    )
    products = list(
        db.scalars(
            select(Product).where(Product.business_id == business_id).order_by(Product.created_at.desc()).limit(100)
        ).all()
    )
    operators = list(
        db.scalars(
            select(TelegramOperator)
            .options(joinedload(TelegramOperator.business))
            .where(TelegramOperator.business_id == business_id)
            .order_by(TelegramOperator.created_at.desc())
        ).all()
    )
    recent_orders = list(
        db.scalars(
            select(Order)
            .options(joinedload(Order.business), joinedload(Order.product))
            .where(Order.business_id == business_id)
            .order_by(Order.created_at.desc())
            .limit(20)
        ).all()
    )
    recent_customers = list(
        db.scalars(
            select(Customer)
            .where(Customer.business_id == business_id)
            .order_by(Customer.created_at.desc())
            .limit(20)
        ).all()
    )
    preview = business.business_knowledge_text[:500] if business.business_knowledge_text else None
    return SuperAdminBusinessDetail(
        business=business_summary(db, business),
        members=[member_summary(member) for member in members],
        products=[SuperAdminProductSummary.model_validate(product) for product in products],
        operators=[operator_summary(operator) for operator in operators],
        recent_orders=[order_summary(order) for order in recent_orders],
        recent_customers=[SuperAdminCustomerSummary.model_validate(customer) for customer in recent_customers],
        business_knowledge=SuperAdminBusinessKnowledge(
            knowledge_file_name=business.knowledge_file_name,
            knowledge_uploaded_at=business.knowledge_uploaded_at,
            business_knowledge_text_preview=preview,
        ),
    )


@router.patch("/businesses/{business_id}", response_model=SuperAdminBusinessSummary)
def update_business(
    business_id: int,
    payload: SuperAdminBusinessUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> SuperAdminBusinessSummary:
    ensure_super_admin(current_user)
    business = get_business_or_404(db, business_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(business, field, value)
    db.commit()
    db.refresh(business)
    return business_summary(db, business)


@router.get("/users", response_model=list[SuperAdminUserSummary])
def list_users(
    db: DbSession,
    current_user: CurrentUser,
    search: str | None = None,
    global_role: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[SuperAdminUserSummary]:
    ensure_super_admin(current_user)
    query = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))
    if global_role:
        query = query.where(User.global_role == global_role)

    users = list(db.scalars(query).all())
    result: list[SuperAdminUserSummary] = []
    for user in users:
        memberships = list(
            db.scalars(
                select(BusinessMember)
                .options(joinedload(BusinessMember.business))
                .where(BusinessMember.user_id == user.id)
                .order_by(BusinessMember.created_at.desc())
            ).all()
        )
        result.append(
            SuperAdminUserSummary(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                global_role=user.global_role,
                is_active=user.is_active,
                created_at=user.created_at,
                businesses=[user_membership_summary(member) for member in memberships],
            )
        )
    return result


@router.get("/users/{user_id}", response_model=SuperAdminUserDetail)
def get_user_detail(user_id: int, db: DbSession, current_user: CurrentUser) -> SuperAdminUserDetail:
    ensure_super_admin(current_user)
    user = get_user_or_404(db, user_id)
    memberships = list(
        db.scalars(
            select(BusinessMember)
            .options(joinedload(BusinessMember.business))
            .where(BusinessMember.user_id == user_id)
            .order_by(BusinessMember.created_at.desc())
        ).all()
    )
    owned_businesses = list(
        db.scalars(select(Business).where(Business.owner_id == user_id).order_by(Business.created_at.desc())).all()
    )
    return SuperAdminUserDetail(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        global_role=user.global_role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        business_memberships=[user_membership_summary(member) for member in memberships],
        owned_businesses=[business_summary(db, business) for business in owned_businesses],
        admin_memberships=[user_membership_summary(member) for member in memberships if member.role == "admin"],
    )


@router.patch("/users/{user_id}", response_model=SuperAdminUserDetail)
def update_user(
    user_id: int,
    payload: SuperAdminUserUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> SuperAdminUserDetail:
    ensure_super_admin(current_user)
    user = get_user_or_404(db, user_id)
    data = payload.model_dump(exclude_unset=True)
    only_active_super_admin = user.global_role == "super_admin" and active_super_admin_count(db) <= 1
    if user.id == current_user.id and only_active_super_admin:
        if data.get("global_role") not in (None, "super_admin") or data.get("is_active") is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The only active super admin cannot remove their own access.",
            )

    for field, value in data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return get_user_detail(user.id, db, current_user)


@router.get("/business-members", response_model=list[SuperAdminMemberSummary])
def list_business_members(
    db: DbSession,
    current_user: CurrentUser,
    business_id: int | None = None,
    user_id: int | None = None,
    role: str | None = None,
    status: str | None = None,
) -> list[SuperAdminMemberSummary]:
    ensure_super_admin(current_user)
    query = (
        select(BusinessMember)
        .options(joinedload(BusinessMember.business), joinedload(BusinessMember.user))
        .order_by(BusinessMember.created_at.desc())
    )
    if business_id is not None:
        query = query.where(BusinessMember.business_id == business_id)
    if user_id is not None:
        query = query.where(BusinessMember.user_id == user_id)
    if role:
        query = query.where(BusinessMember.role == role)
    if status:
        query = query.where(BusinessMember.status == status)
    return [member_summary(member) for member in db.scalars(query).all()]


@router.get("/operators", response_model=list[SuperAdminOperatorSummary])
def list_operators(db: DbSession, current_user: CurrentUser) -> list[SuperAdminOperatorSummary]:
    ensure_super_admin(current_user)
    operators = list(
        db.scalars(
            select(TelegramOperator)
            .options(joinedload(TelegramOperator.business))
            .order_by(TelegramOperator.created_at.desc())
        ).all()
    )
    return [operator_summary(operator) for operator in operators]


@router.get("/orders", response_model=list[SuperAdminOrderSummary])
def list_orders(
    db: DbSession,
    current_user: CurrentUser,
    business_id: int | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[SuperAdminOrderSummary]:
    ensure_super_admin(current_user)
    query = (
        select(Order)
        .options(joinedload(Order.business), joinedload(Order.product))
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if business_id is not None:
        query = query.where(Order.business_id == business_id)
    if status:
        query = query.where(Order.status == status)
    return [order_summary(order) for order in db.scalars(query).all()]
