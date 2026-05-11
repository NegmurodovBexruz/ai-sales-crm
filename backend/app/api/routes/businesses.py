from fastapi import APIRouter, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.access import require_business_admin_or_owner, require_business_owner
from app.api.deps import CurrentUser, DbSession
from app.models.business_member import BusinessMember
from app.schemas.business import (
    BusinessCreate,
    BusinessMeResponse,
    BusinessRead,
    BusinessUpdate,
    TelegramTokenStatus,
    TelegramTokenUpdate,
)
from app.models.business import Business
from app.services.business_service import (
    business_read_payload,
    create_business_for_owner,
    get_business_or_404,
    save_telegram_token,
    set_telegram_webhook_for_business,
    telegram_webhook_url,
    update_business_fields,
    update_business_knowledge_from_docx,
)

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
def create_business(payload: BusinessCreate, db: DbSession, current_user: CurrentUser) -> Business:
    return create_business_for_owner(db, current_user.id, payload)


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

    return update_business_fields(db, business, payload)


@router.post("/{business_id}/knowledge-docx", response_model=BusinessRead)
async def upload_business_knowledge_docx(
    business_id: int,
    file: UploadFile,
    db: DbSession,
    current_user: CurrentUser,
) -> Business:
    business = get_business_or_404(db, business_id)
    require_business_owner(db, current_user, business_id)

    return await update_business_knowledge_from_docx(db, business, file)


@router.patch("/{business_id}/telegram-token", response_model=TelegramTokenStatus)
def update_telegram_token(
    business_id: int,
    payload: TelegramTokenUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> TelegramTokenStatus:
    business = get_business_or_404(db, business_id)
    require_business_admin_or_owner(db, current_user, business_id)

    business = save_telegram_token(db, business, payload.telegram_bot_token)

    return TelegramTokenStatus(
        has_token=True,
        webhook_set=business.telegram_webhook_set,
        webhook_url=telegram_webhook_url(business),
        telegram_webhook_secret_exists=bool(business.telegram_webhook_secret),
    )


@router.post("/{business_id}/telegram/set-webhook", response_model=TelegramTokenStatus)
def set_telegram_webhook(
    business_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> TelegramTokenStatus:
    business = get_business_or_404(db, business_id)
    require_business_admin_or_owner(db, current_user, business_id)

    business = set_telegram_webhook_for_business(db, business)
    webhook_url = telegram_webhook_url(business)

    return TelegramTokenStatus(
        has_token=True,
        webhook_set=business.telegram_webhook_set,
        webhook_url=webhook_url,
        telegram_webhook_secret_exists=bool(business.telegram_webhook_secret),
    )


@router.get("/{business_id}/telegram/status", response_model=TelegramTokenStatus)
def get_telegram_status(
    business_id: int,
    db: DbSession,
    current_user: CurrentUser,
) -> TelegramTokenStatus:
    business = get_business_or_404(db, business_id)
    require_business_admin_or_owner(db, current_user, business_id)
    return TelegramTokenStatus(
        has_token=bool(business.telegram_bot_token_encrypted),
        webhook_set=business.telegram_webhook_set,
        webhook_url=telegram_webhook_url(business),
        telegram_webhook_secret_exists=bool(business.telegram_webhook_secret),
    )
