from datetime import datetime, timezone
import json
from secrets import token_urlsafe
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.access import require_business_admin_or_owner, require_business_owner
from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models.business import Business
from app.models.business_member import BusinessMember
from app.schemas.business import (
    BusinessCreate,
    BusinessMeResponse,
    BusinessRead,
    BusinessUpdate,
    TelegramTokenStatus,
    TelegramTokenUpdate,
)
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


def telegram_webhook_url(business: Business) -> str | None:
    if not settings.BACKEND_URL:
        return None
    return f"{settings.BACKEND_URL.rstrip('/')}/api/telegram/webhook/{business.public_business_id}"


def call_telegram_set_webhook(bot_token: str, webhook_url: str, secret_token: str | None) -> dict:
    payload: dict[str, str] = {"url": webhook_url}
    if secret_token:
        payload["secret_token"] = secret_token
    request = Request(
        url=f"https://api.telegram.org/bot{bot_token}/setWebhook",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") or str(exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Telegram setWebhook failed: {detail}") from exc
    except URLError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Telegram setWebhook failed: {exc.reason}") from exc

    if not data.get("ok"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=data.get("description") or "Telegram setWebhook failed",
        )
    return data


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


@router.patch("/{business_id}/telegram-token", response_model=TelegramTokenStatus)
def update_telegram_token(
    business_id: int,
    payload: TelegramTokenUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> TelegramTokenStatus:
    business = get_business_or_404(db, business_id)
    require_business_admin_or_owner(db, current_user, business_id)

    token = payload.telegram_bot_token.strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram bot token is required")

    business.telegram_bot_token_encrypted = encrypt_secret(token)
    business.telegram_webhook_set = False
    if not business.telegram_webhook_secret:
        business.telegram_webhook_secret = token_urlsafe(32)
    db.commit()
    db.refresh(business)

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

    if not settings.BACKEND_URL:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BACKEND_URL is not configured")
    if not business.telegram_bot_token_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram bot token is not configured")

    if not business.telegram_webhook_secret:
        business.telegram_webhook_secret = token_urlsafe(32)
        db.flush()

    webhook_url = telegram_webhook_url(business)
    if webhook_url is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BACKEND_URL is not configured")

    bot_token = decrypt_secret(business.telegram_bot_token_encrypted)
    call_telegram_set_webhook(bot_token, webhook_url, business.telegram_webhook_secret)
    business.telegram_webhook_set = True
    db.commit()
    db.refresh(business)

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
