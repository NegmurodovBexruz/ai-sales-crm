from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession
from app.models.business import Business
from app.models.business_member import BusinessMember
from app.models.user import User


def is_super_admin(user: User) -> bool:
    return user.global_role == "super_admin"


def get_user_business_membership(db: DbSession, user_id: int, business_id: int) -> BusinessMember | None:
    return db.scalar(
        select(BusinessMember)
        .options(joinedload(BusinessMember.user))
        .where(BusinessMember.user_id == user_id, BusinessMember.business_id == business_id)
    )


def require_business_member(db: DbSession, user: User, business_id: int) -> BusinessMember | None:
    if is_super_admin(user):
        return None
    membership = get_user_business_membership(db, user.id, business_id)
    if membership is None or membership.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this business")
    return membership


def require_business_owner(db: DbSession, user: User, business_id: int) -> BusinessMember | None:
    if is_super_admin(user):
        return None
    membership = require_business_member(db, user, business_id)
    if membership is None or membership.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business owner access is required")
    return membership


def require_business_admin_or_owner(db: DbSession, user: User, business_id: int) -> BusinessMember | None:
    if is_super_admin(user):
        return None
    membership = require_business_member(db, user, business_id)
    if membership is None or membership.role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business admin access is required")
    return membership


def get_accessible_business_ids(db: DbSession, user: User) -> list[int] | None:
    if is_super_admin(user):
        return None
    return list(
        db.scalars(
            select(BusinessMember.business_id).where(
                BusinessMember.user_id == user.id,
                BusinessMember.status == "active",
                BusinessMember.role.in_(("owner", "admin")),
            )
        ).all()
    )


def get_accessible_business_or_404(db: DbSession, user: User, business_id: int) -> Business:
    business = db.scalar(select(Business).where(Business.id == business_id))
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    require_business_admin_or_owner(db, user, business_id)
    return business


def require_super_admin(user: User) -> None:
    if not is_super_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access is required")
