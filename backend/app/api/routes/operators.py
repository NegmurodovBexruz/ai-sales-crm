from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.access import get_accessible_business_ids, require_business_admin_or_owner
from app.api.deps import CurrentUser, DbSession
from app.models.telegram_operator import TelegramOperator
from app.schemas.telegram_operator import (
    TelegramOperatorCreate,
    TelegramOperatorResponse,
    TelegramOperatorUpdate,
)

router = APIRouter(prefix="/operators", tags=["operators"])


def get_current_business_id(db: DbSession, current_user: CurrentUser) -> int:
    business_ids = get_accessible_business_ids(db, current_user)
    if business_ids is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="business_id is required for super admin")
    if not business_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active business access")
    return business_ids[0]


def normalize_required(value: str | None, field_name: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{field_name} cannot be empty")
    return normalized


def get_accessible_operator(db: DbSession, operator_id: int, current_user: CurrentUser) -> TelegramOperator:
    operator = db.scalar(select(TelegramOperator).where(TelegramOperator.id == operator_id))
    if operator is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")
    require_business_admin_or_owner(db, current_user, operator.business_id)
    return operator


@router.get("", response_model=list[TelegramOperatorResponse])
def list_operators(db: DbSession, current_user: CurrentUser) -> list[TelegramOperator]:
    business_id = get_current_business_id(db, current_user)
    require_business_admin_or_owner(db, current_user, business_id)
    return list(
        db.scalars(
            select(TelegramOperator)
            .where(TelegramOperator.business_id == business_id)
            .order_by(TelegramOperator.created_at.desc())
        ).all()
    )


@router.post("", response_model=TelegramOperatorResponse, status_code=status.HTTP_201_CREATED)
def create_operator(
    payload: TelegramOperatorCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> TelegramOperator:
    business_id = get_current_business_id(db, current_user)
    require_business_admin_or_owner(db, current_user, business_id)
    operator = TelegramOperator(
        business_id=business_id,
        name=normalize_required(payload.name, "name"),
        telegram_chat_id=normalize_required(payload.telegram_chat_id, "telegram_chat_id"),
        username=(payload.username or "").strip() or None,
        is_active=payload.is_active,
    )
    db.add(operator)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Telegram chat ID already exists for this business",
        ) from exc
    db.refresh(operator)
    return operator


@router.get("/{operator_id}", response_model=TelegramOperatorResponse)
def get_operator(operator_id: int, db: DbSession, current_user: CurrentUser) -> TelegramOperator:
    return get_accessible_operator(db, operator_id, current_user)


@router.patch("/{operator_id}", response_model=TelegramOperatorResponse)
def update_operator(
    operator_id: int,
    payload: TelegramOperatorUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> TelegramOperator:
    operator = get_accessible_operator(db, operator_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        operator.name = normalize_required(data["name"], "name")
    if "telegram_chat_id" in data:
        operator.telegram_chat_id = normalize_required(data["telegram_chat_id"], "telegram_chat_id")
    if "username" in data:
        operator.username = (data["username"] or "").strip() or None
    if "is_active" in data:
        operator.is_active = data["is_active"]
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Telegram chat ID already exists for this business",
        ) from exc
    db.refresh(operator)
    return operator


@router.delete("/{operator_id}", response_model=TelegramOperatorResponse)
def delete_operator(operator_id: int, db: DbSession, current_user: CurrentUser) -> TelegramOperator:
    operator = get_accessible_operator(db, operator_id, current_user)
    operator.is_active = False
    db.commit()
    db.refresh(operator)
    return operator
