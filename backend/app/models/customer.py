from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("business_id", "telegram_user_id", name="uq_customers_business_telegram_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    business_id: Mapped[int] = mapped_column(ForeignKey("businesses.id"), nullable=False, index=True)
    telegram_user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str] = mapped_column(String(20), default="uz_latin", nullable=False)
    pending_operator_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_operator_ai_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_operator_intent: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pending_operator_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    business: Mapped["Business"] = relationship(back_populates="customers")
