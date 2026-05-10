from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

CustomerLanguage = Literal["uz_latin", "uz_cyrillic", "ru"]


class CustomerBase(BaseModel):
    business_id: int
    telegram_user_id: str
    full_name: str | None = None
    username: str | None = None
    phone: str | None = None
    language: CustomerLanguage = "uz_latin"
    pending_operator_message: str | None = None
    pending_operator_ai_reply: str | None = None
    pending_operator_intent: str | None = None
    pending_operator_confidence: Decimal | None = None


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    full_name: str | None = None
    username: str | None = None
    phone: str | None = None
    language: CustomerLanguage | None = None
    pending_operator_message: str | None = None
    pending_operator_ai_reply: str | None = None
    pending_operator_intent: str | None = None
    pending_operator_confidence: Decimal | None = None


class CustomerResponse(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


CustomerRead = CustomerResponse
