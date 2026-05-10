from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.telegram_operator import TelegramOperator

operator_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/operator-auth/login")


@dataclass(frozen=True)
class OperatorContext:
    operator: TelegramOperator
    business_id: int


def get_current_operator(
    db=Depends(get_db),
    token: Annotated[str, Depends(operator_oauth2_scheme)] = "",
) -> OperatorContext:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate operator credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    if payload.get("token_type") != "operator":
        raise credentials_exception

    operator_id = payload.get("operator_id")
    business_id = payload.get("business_id")
    if operator_id is None or business_id is None:
        raise credentials_exception

    operator = db.scalar(
        select(TelegramOperator)
        .options(joinedload(TelegramOperator.business))
        .where(
            TelegramOperator.id == int(operator_id),
            TelegramOperator.business_id == int(business_id),
            TelegramOperator.is_active.is_(True),
        )
    )
    if operator is None:
        raise credentials_exception
    return OperatorContext(operator=operator, business_id=operator.business_id)


CurrentOperator = Annotated[OperatorContext, Depends(get_current_operator)]
