from pydantic import BaseModel, ConfigDict

from app.schemas.business import BusinessMemberRead


class JoinRequestCreate(BaseModel):
    public_business_id: str | None = None
    admin_join_code: str | None = None


class JoinRequestResponse(BaseModel):
    message: str
    membership: BusinessMemberRead


class BusinessMemberListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    business_public_id: str
    members: list[BusinessMemberRead]
    pending_requests: list[BusinessMemberRead]
