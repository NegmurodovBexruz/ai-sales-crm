from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    customer_id: int
    status: str
    score: int
    interested_product_id: int | None
    source: str | None
    next_followup_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

