from datetime import datetime, timezone
import json
import logging
from secrets import token_urlsafe
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models.business import Business
from app.models.business_member import BusinessMember
from app.schemas.business import BusinessCreate, BusinessUpdate
from app.utils.business_ids import generate_admin_join_code, generate_operator_code, generate_public_business_id
from app.utils.docx_parser import extract_text_from_docx

logger = logging.getLogger(__name__)


def get_business_or_404(db: Session, business_id: int) -> Business:
    business = db.scalar(select(Business).where(Business.id == business_id))
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


def business_read_payload(business: Business, include_admin_join_code: bool = True) -> dict:
    return {
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


def create_business_for_owner(db: Session, owner_id: int, payload: BusinessCreate) -> Business:
    business = Business(
        owner_id=owner_id,
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
            user_id=owner_id,
            role="owner",
            status="active",
            approved_by_user_id=owner_id,
        )
    )
    db.commit()
    db.refresh(business)
    return business


def update_business_fields(db: Session, business: Business, payload: BusinessUpdate) -> Business:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(business, field, value)
    db.commit()
    db.refresh(business)
    return business


async def update_business_knowledge_from_docx(db: Session, business: Business, file: UploadFile) -> Business:
    if file.filename is None or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .docx files are allowed")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    try:
        extracted_text = extract_text_from_docx(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if not extracted_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DOCX file does not contain any text")

    business.business_knowledge_text = extracted_text
    business.knowledge_file_name = file.filename
    business.knowledge_uploaded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(business)
    return business


def telegram_webhook_url(business: Business) -> str | None:
    if not settings.BACKEND_URL:
        return None
    return f"{settings.BACKEND_URL.rstrip('/')}/api/telegram/webhook/{business.public_business_id}"


def save_telegram_token(db: Session, business: Business, token: str) -> Business:
    token = token.strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telegram bot token is required")

    business.telegram_bot_token_encrypted = encrypt_secret(token)
    business.telegram_webhook_set = False
    if not business.telegram_webhook_secret:
        business.telegram_webhook_secret = token_urlsafe(32)
    db.commit()
    db.refresh(business)
    return business


def call_telegram_set_webhook(bot_token: str, webhook_url: str, secret_token: str | None, business_id: int | None = None) -> dict:
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
        logger.warning("Telegram setWebhook failed for url=%s: %s", webhook_url, detail)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Telegram setWebhook failed: {detail}") from exc
    except URLError as exc:
        logger.warning("Telegram setWebhook network failure for url=%s: %s", webhook_url, exc.reason)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Telegram setWebhook failed: {exc.reason}") from exc

    if not data.get("ok"):
        logger.warning("Telegram setWebhook rejected for url=%s: %s", webhook_url, data.get("description"))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=data.get("description") or "Telegram setWebhook failed",
        )
    logger.info("Telegram webhook set successfully for business_id=%s url=%s", business_id, webhook_url)
    return data


def set_telegram_webhook_for_business(db: Session, business: Business) -> Business:
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
    call_telegram_set_webhook(bot_token, webhook_url, business.telegram_webhook_secret, business.id)
    business.telegram_webhook_set = True
    db.commit()
    db.refresh(business)
    return business
