from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BusinessBase(BaseModel):
    name: str
    description: str | None = None
    phone: str | None = None
    delivery_policy: str | None = None
    return_policy: str | None = None
    working_hours: str | None = None
    ai_tone: str | None = None
    business_knowledge_text: str | None = None
    knowledge_file_name: str | None = None


class BusinessCreate(BusinessBase):
    pass


class BusinessUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    phone: str | None = None
    delivery_policy: str | None = None
    return_policy: str | None = None
    working_hours: str | None = None
    ai_tone: str | None = None
    business_knowledge_text: str | None = None
    knowledge_file_name: str | None = None


class BusinessRead(BusinessBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    public_business_id: str
    admin_join_code: str | None = None
    operator_code: str | None = None
    is_active: bool
    knowledge_uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BusinessMemberUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None


class BusinessMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    user_id: int
    role: str
    status: str
    invited_by_user_id: int | None
    approved_by_user_id: int | None
    created_at: datetime
    updated_at: datetime
    user: BusinessMemberUserRead | None = None


class BusinessMeResponse(BaseModel):
    business: BusinessRead | None
    membership: BusinessMemberRead | None
    pending_requests: list[BusinessMemberRead] = []
