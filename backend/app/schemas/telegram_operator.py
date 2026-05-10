from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TelegramOperatorCreate(BaseModel):
    name: str
    telegram_chat_id: str
    username: str | None = None
    is_active: bool = True


class TelegramOperatorUpdate(BaseModel):
    name: str | None = None
    telegram_chat_id: str | None = None
    username: str | None = None
    is_active: bool | None = None


class TelegramOperatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    name: str
    telegram_chat_id: str
    username: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
