from sqlalchemy.orm import Session

from app.models.conversation import Conversation


def save_conversation_message(
    db: Session,
    business_id: int,
    customer_id: int,
    message_text: str,
    sender_type: str,
    intent: str | None = None,
) -> Conversation:
    conversation = Conversation(
        business_id=business_id,
        customer_id=customer_id,
        message_text=message_text,
        sender_type=sender_type,
        intent=intent,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

