from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.access import require_business_owner
from app.api.deps import CurrentUser, DbSession
from app.models.business import Business
from app.models.business_member import BusinessMember
from app.schemas.business_member import BusinessMemberListResponse, JoinRequestCreate, JoinRequestResponse

router = APIRouter(prefix="/business-members", tags=["business-members"])


def get_member_or_404(db: DbSession, member_id: int) -> BusinessMember:
    member = db.scalar(
        select(BusinessMember)
        .options(joinedload(BusinessMember.user), joinedload(BusinessMember.business))
        .where(BusinessMember.id == member_id)
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business member not found")
    return member


def get_owner_business_id(db: DbSession, current_user: CurrentUser, business_id: int | None = None) -> int:
    if business_id is not None:
        require_business_owner(db, current_user, business_id)
        return business_id
    owner_membership = db.scalar(
        select(BusinessMember).where(
            BusinessMember.user_id == current_user.id,
            BusinessMember.role == "owner",
            BusinessMember.status == "active",
        )
    )
    if owner_membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Business owner access is required")
    return owner_membership.business_id


@router.post("/join-request", response_model=JoinRequestResponse, status_code=status.HTTP_201_CREATED)
def create_join_request(payload: JoinRequestCreate, db: DbSession, current_user: CurrentUser) -> dict:
    if not payload.admin_join_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="admin_join_code is required",
        )
    business = db.scalar(select(Business).where(Business.admin_join_code == payload.admin_join_code))
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    existing = db.scalar(
        select(BusinessMember)
        .options(joinedload(BusinessMember.user))
        .where(BusinessMember.business_id == business.id, BusinessMember.user_id == current_user.id)
    )
    if existing and existing.status == "active":
        return {"message": "You are already an active member of this business.", "membership": existing}
    if existing and existing.status == "pending":
        return {"message": "Your join request is already pending.", "membership": existing}
    if existing:
        existing.role = "admin"
        existing.status = "pending"
        existing.invited_by_user_id = None
        existing.approved_by_user_id = None
        db.commit()
        db.refresh(existing)
        return {"message": "Join request submitted.", "membership": existing}

    membership = BusinessMember(
        business_id=business.id,
        user_id=current_user.id,
        role="admin",
        status="pending",
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return {"message": "Join request submitted.", "membership": membership}


@router.get("", response_model=BusinessMemberListResponse)
def list_business_members(db: DbSession, current_user: CurrentUser, business_id: int | None = None) -> dict:
    owner_business_id = get_owner_business_id(db, current_user, business_id)
    business = db.scalar(select(Business).where(Business.id == owner_business_id))
    members = list(
        db.scalars(
            select(BusinessMember)
            .options(joinedload(BusinessMember.user))
            .where(BusinessMember.business_id == owner_business_id, BusinessMember.status == "active")
            .order_by(BusinessMember.role.desc(), BusinessMember.created_at.asc())
        ).all()
    )
    pending_requests = list(
        db.scalars(
            select(BusinessMember)
            .options(joinedload(BusinessMember.user))
            .where(BusinessMember.business_id == owner_business_id, BusinessMember.status == "pending")
            .order_by(BusinessMember.created_at.asc())
        ).all()
    )
    return {
        "business_public_id": business.public_business_id if business else "",
        "members": members,
        "pending_requests": pending_requests,
    }


@router.patch("/{member_id}/approve", response_model=JoinRequestResponse)
def approve_member(member_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    member = get_member_or_404(db, member_id)
    require_business_owner(db, current_user, member.business_id)
    member.status = "active"
    member.approved_by_user_id = current_user.id
    db.commit()
    db.refresh(member)
    return {"message": "Member approved.", "membership": member}


@router.patch("/{member_id}/reject", response_model=JoinRequestResponse)
def reject_member(member_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    member = get_member_or_404(db, member_id)
    require_business_owner(db, current_user, member.business_id)
    member.status = "rejected"
    db.commit()
    db.refresh(member)
    return {"message": "Member rejected.", "membership": member}


@router.patch("/{member_id}/remove", response_model=JoinRequestResponse)
def remove_member(member_id: int, db: DbSession, current_user: CurrentUser) -> dict:
    member = get_member_or_404(db, member_id)
    require_business_owner(db, current_user, member.business_id)
    if member.user_id == current_user.id and member.role == "owner":
        active_owner_count = db.scalar(
            select(func.count(BusinessMember.id)).where(
                BusinessMember.business_id == member.business_id,
                BusinessMember.role == "owner",
                BusinessMember.status == "active",
            )
        )
        if active_owner_count == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The only active owner cannot remove themselves.",
            )
    member.status = "removed"
    db.commit()
    db.refresh(member)
    return {"message": "Member removed.", "membership": member}
