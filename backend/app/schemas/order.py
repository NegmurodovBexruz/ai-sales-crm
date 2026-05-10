from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    discount_price: Decimal | None
    final_unit_price: Decimal
    total_price: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    business_id: int
    customer_id: int
    product_id: int | None
    quantity: int | None
    total_price: Decimal
    customer_name: str
    phone: str
    address: str
    comment: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead] = Field(default_factory=list)


class OrderDoneResponse(BaseModel):
    order: OrderRead
    product_stock_count: int | None = None
    message: str


class OrderStatusUpdate(BaseModel):
    status: str
