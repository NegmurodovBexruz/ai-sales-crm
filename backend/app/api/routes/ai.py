from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.access import require_business_admin_or_owner
from app.api.deps import CurrentUser, DbSession
from app.models.customer import Customer
from app.services.ai_service import AIServiceNotFoundError, ai_service
from app.services.conversation_service import save_conversation_message

router = APIRouter(prefix="/ai", tags=["ai"])

AIIntent = Literal[
    "product_question",
    "price_question",
    "availability_question",
    "delivery_question",
    "return_policy_question",
    "order_intent",
    "complaint",
    "operator_request",
    "irrelevant",
    "unknown",
]


class CustomerReplyRequest(BaseModel):
    business_id: int
    customer_id: int
    customer_message: str = Field(min_length=1)


class CustomerReplyResponse(BaseModel):
    reply: str
    intent: AIIntent
    lead_score: int
    recommended_product_ids: list[int]
    needs_operator: bool
    order_intent: bool
    confidence: float


def ensure_customer_belongs_to_business(db: DbSession, customer_id: int, business_id: int) -> None:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.business_id == business_id))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")


@router.post("/customer-reply", response_model=CustomerReplyResponse)
async def generate_customer_reply(
    payload: CustomerReplyRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    require_business_admin_or_owner(db, current_user, payload.business_id)
    ensure_customer_belongs_to_business(db, payload.customer_id, payload.business_id)

    try:
        response = await ai_service.generate_customer_reply(
            db=db,
            business_id=payload.business_id,
            customer_id=payload.customer_id,
            customer_message=payload.customer_message,
        )
    except AIServiceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    save_conversation_message(
        db=db,
        business_id=payload.business_id,
        customer_id=payload.customer_id,
        message_text=response["reply"],
        sender_type="ai",
        intent=response["intent"],
    )
    return response
