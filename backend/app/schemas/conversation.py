from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

SenderType = Literal["customer", "ai", "admin", "system"]


class ConversationCreate(BaseModel):
    business_id: int
    customer_id: int
    message_text: str
    sender_type: SenderType
    intent: str | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    customer_id: int
    message_text: str
    sender_type: SenderType
    intent: str | None
    created_at: datetime

