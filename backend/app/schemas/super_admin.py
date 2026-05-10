from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SuperAdminStats(BaseModel):
    total_businesses: int
    active_businesses: int
    total_users: int
    total_orders: int
    total_customers: int
    total_products: int
    total_operators: int
    new_businesses_today: int
    new_users_today: int
    orders_today: int


class SuperAdminBusinessSummary(BaseModel):
    id: int
    public_business_id: str
    name: str
    phone: str | None
    description: str | None
    delivery_policy: str | None
    return_policy: str | None
    working_hours: str | None
    ai_tone: str | None
    created_at: datetime
    owners_count: int
    admins_count: int
    products_count: int
    orders_count: int
    customers_count: int
    active_operators_count: int
    is_active: bool
    status: str


class SuperAdminBusinessUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    phone: str | None = None
    delivery_policy: str | None = None
    return_policy: str | None = None
    working_hours: str | None = None
    ai_tone: str | None = None
    is_active: bool | None = None


class SuperAdminUserSummary(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    global_role: str
    is_active: bool
    created_at: datetime
    businesses: list["SuperAdminUserMembership"]


class SuperAdminUserUpdate(BaseModel):
    full_name: str | None = None
    global_role: str | None = Field(default=None, pattern="^(user|super_admin)$")
    is_active: bool | None = None


class SuperAdminMemberSummary(BaseModel):
    id: int
    business_id: int
    business_name: str
    user_id: int
    user_email: EmailStr
    role: str
    status: str
    created_at: datetime


class SuperAdminUserMembership(BaseModel):
    id: int
    business_id: int
    business_name: str
    role: str
    status: str
    created_at: datetime


class SuperAdminUserDetail(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: str
    global_role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    business_memberships: list[SuperAdminUserMembership]
    owned_businesses: list[SuperAdminBusinessSummary]
    admin_memberships: list[SuperAdminUserMembership]


class SuperAdminProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    name: str
    category: str | None
    price: Decimal
    discount_price: Decimal | None
    stock_count: int
    availability_status: str
    created_at: datetime


class SuperAdminOperatorSummary(BaseModel):
    id: int
    business_id: int
    business_name: str
    name: str
    telegram_chat_id: str
    username: str | None
    is_active: bool
    created_at: datetime


class SuperAdminOrderSummary(BaseModel):
    id: int
    business_id: int
    business_name: str
    customer_name: str
    phone: str
    product: str | None
    quantity: int
    total_price: Decimal
    status: str
    created_at: datetime


class SuperAdminCustomerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    telegram_user_id: str
    full_name: str | None
    username: str | None
    phone: str | None
    language: str
    created_at: datetime


class SuperAdminBusinessKnowledge(BaseModel):
    knowledge_file_name: str | None
    knowledge_uploaded_at: datetime | None
    business_knowledge_text_preview: str | None


class SuperAdminBusinessDetail(BaseModel):
    business: SuperAdminBusinessSummary
    members: list[SuperAdminMemberSummary]
    products: list[SuperAdminProductSummary]
    operators: list[SuperAdminOperatorSummary]
    recent_orders: list[SuperAdminOrderSummary]
    recent_customers: list[SuperAdminCustomerSummary]
    business_knowledge: SuperAdminBusinessKnowledge


SuperAdminUserSummary.model_rebuild()
