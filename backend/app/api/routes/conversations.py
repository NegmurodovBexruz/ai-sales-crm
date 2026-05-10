from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.access import require_business_admin_or_owner
from app.api.deps import CurrentUser, DbSession
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.schemas.conversation import ConversationCreate, ConversationResponse
from app.services.conversation_service import save_conversation_message

router = APIRouter(prefix="/conversations", tags=["conversations"])


def get_accessible_customer(db: DbSession, customer_id: int, current_user: CurrentUser) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    require_business_admin_or_owner(db, current_user, customer.business_id)
    return customer


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Conversation:
    customer = get_accessible_customer(db, payload.customer_id, current_user)
    if customer.business_id != payload.business_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer does not belong to the provided business",
        )

    return save_conversation_message(
        db=db,
        business_id=payload.business_id,
        customer_id=payload.customer_id,
        message_text=payload.message_text,
        sender_type=payload.sender_type,
        intent=payload.intent,
    )


@router.get("/customer/{customer_id}", response_model=list[ConversationResponse])
def get_customer_conversation_history(
    customer_id: int,
    db: DbSession,
    current_user: CurrentUser,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Conversation]:
    customer = get_accessible_customer(db, customer_id, current_user)
    query = (
        select(Conversation)
        .where(
            Conversation.business_id == customer.business_id,
            Conversation.customer_id == customer.id,
        )
        .order_by(Conversation.created_at.asc(), Conversation.id.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query).all())
