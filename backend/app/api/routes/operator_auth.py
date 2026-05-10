from pydantic import BaseModel, ConfigDict
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession
from app.api.operator_deps import CurrentOperator
from app.core.security import create_access_token
from app.models.business import Business
from app.models.telegram_operator import TelegramOperator

router = APIRouter(prefix="/operator-auth", tags=["operator-auth"])


class OperatorLoginRequest(BaseModel):
    operator_code: str
    telegram_chat_id: str


class OperatorBusinessInfo(BaseModel):
    id: int
    name: str


class OperatorInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    telegram_chat_id: str
    business_id: int
    business_name: str


class OperatorLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    operator: OperatorInfo


class OperatorMeResponse(BaseModel):
    operator: OperatorInfo
    business: OperatorBusinessInfo


def build_operator_info(operator: TelegramOperator) -> OperatorInfo:
    return OperatorInfo(
        id=operator.id,
        name=operator.name,
        telegram_chat_id=operator.telegram_chat_id,
        business_id=operator.business_id,
        business_name=operator.business.name if operator.business else "",
    )


@router.post("/login", response_model=OperatorLoginResponse)
def login(payload: OperatorLoginRequest, db: DbSession) -> OperatorLoginResponse:
    business = db.scalar(select(Business).where(Business.operator_code == payload.operator_code.strip()))
    if business is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator code or Telegram chat ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    operator = db.scalar(
        select(TelegramOperator)
        .options(joinedload(TelegramOperator.business))
        .where(
            TelegramOperator.business_id == business.id,
            TelegramOperator.telegram_chat_id == payload.telegram_chat_id.strip(),
            TelegramOperator.is_active.is_(True),
        )
    )
    if operator is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid operator code or Telegram chat ID",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=f"operator:{operator.id}",
        extra_payload={
            "operator_id": operator.id,
            "business_id": operator.business_id,
            "token_type": "operator",
        },
    )
    return OperatorLoginResponse(access_token=access_token, operator=build_operator_info(operator))


@router.get("/me", response_model=OperatorMeResponse)
def me(current_operator: CurrentOperator) -> OperatorMeResponse:
    operator = current_operator.operator
    return OperatorMeResponse(
        operator=build_operator_info(operator),
        business=OperatorBusinessInfo(id=operator.business_id, name=operator.business.name if operator.business else ""),
    )
