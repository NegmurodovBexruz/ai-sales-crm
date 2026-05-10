from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.access import require_business_owner
from app.api.deps import CurrentUser, DbSession
from app.models.business import Business
from app.models.business_member import BusinessMember
from app.schemas.business import BusinessCreate, BusinessMeResponse, BusinessRead, BusinessUpdate
from app.utils.business_ids import generate_admin_join_code, generate_operator_code, generate_public_business_id
from app.utils.docx_parser import extract_text_from_docx

router = APIRouter(prefix="/businesses", tags=["businesses"])


def get_business_or_404(db: DbSession, business_id: int) -> Business:
    business = db.scalar(select(Business).where(Business.id == business_id))
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


def business_read_payload(business: Business, include_admin_join_code: bool = True) -> dict:
    payload = {
        "id": business.id,
        "owner_id": business.owner_id,
        "public_business_id": business.public_business_id,
        "admin_join_code": business.admin_join_code if include_admin_join_code else None,
        "operator_code": business.operator_code,
        "name": business.name,
        "description": business.description,
        "phone": business.phone,
        "delivery_policy": business.delivery_policy,
        "return_policy": business.return_policy,
        "working_hours": business.working_hours,
        "ai_tone": business.ai_tone,
        "business_knowledge_text": business.business_knowledge_text,
        "knowledge_file_name": business.knowledge_file_name,
        "knowledge_uploaded_at": business.knowledge_uploaded_at,
        "is_active": business.is_active,
        "created_at": business.created_at,
        "updated_at": business.updated_at,
    }
    return payload


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
def create_business(payload: BusinessCreate, db: DbSession, current_user: CurrentUser) -> Business:
    business = Business(
        owner_id=current_user.id,
        public_business_id=generate_public_business_id(db),
        admin_join_code=generate_admin_join_code(db),
        operator_code=generate_operator_code(db),
        **payload.model_dump(),
    )
    db.add(business)
    db.flush()
    db.add(
        BusinessMember(
            business_id=business.id,
            user_id=current_user.id,
            role="owner",
            status="active",
            approved_by_user_id=current_user.id,
        )
    )
    db.commit()
    db.refresh(business)
    return business


@router.get("/me", response_model=BusinessMeResponse)
def get_my_business(db: DbSession, current_user: CurrentUser) -> dict:
    active_membership = db.scalar(
        select(BusinessMember)
        .options(joinedload(BusinessMember.business), joinedload(BusinessMember.user))
        .where(
            BusinessMember.user_id == current_user.id,
            BusinessMember.status == "active",
        )
        .order_by(BusinessMember.created_at.asc())
    )
    pending_requests = list(
        db.scalars(
            select(BusinessMember)
            .options(joinedload(BusinessMember.business), joinedload(BusinessMember.user))
            .where(
                BusinessMember.user_id == current_user.id,
                BusinessMember.status == "pending",
            )
            .order_by(BusinessMember.created_at.desc())
        ).all()
    )
    return {
        "business": business_read_payload(
            active_membership.business,
            include_admin_join_code=active_membership.role == "owner",
        ) if active_membership else None,
        "membership": active_membership,
        "pending_requests": pending_requests,
    }


@router.patch("/{business_id}", response_model=BusinessRead)
def update_business(
    business_id: int,
    payload: BusinessUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Business:
    business = get_business_or_404(db, business_id)
    require_business_owner(db, current_user, business_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(business, field, value)

    db.commit()
    db.refresh(business)
    return business


@router.post("/{business_id}/knowledge-docx", response_model=BusinessRead)
async def upload_business_knowledge_docx(
    business_id: int,
    file: UploadFile,
    db: DbSession,
    current_user: CurrentUser,
) -> Business:
    business = get_business_or_404(db, business_id)
    require_business_owner(db, current_user, business_id)

    if file.filename is None or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .docx files are allowed",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    try:
        extracted_text = extract_text_from_docx(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="DOCX file does not contain any text",
        )

    business.business_knowledge_text = extracted_text
    business.knowledge_file_name = file.filename
    business.knowledge_uploaded_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(business)
    return business
