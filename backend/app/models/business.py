from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Business(TimestampMixin, Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    public_business_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    admin_join_code: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    operator_code: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delivery_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    return_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    working_hours: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_tone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    business_knowledge_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    knowledge_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    knowledge_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="businesses")
    members: Mapped[list["BusinessMember"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    products: Mapped[list["Product"]] = relationship(back_populates="business", cascade="all, delete-orphan")
    customers: Mapped[list["Customer"]] = relationship(back_populates="business", cascade="all, delete-orphan")
