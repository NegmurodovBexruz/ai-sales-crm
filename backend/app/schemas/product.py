from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    business_id: int
    name: str
    description: str | None = None
    category: str | None = None
    price: Decimal = Field(gt=0)
    discount_price: Decimal | None = Field(default=None, ge=0)
    stock_count: int = Field(default=0, ge=0)
    image_url: str | None = None
    tags: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    discount_price: Decimal | None = Field(default=None, ge=0)
    stock_count: int | None = Field(default=None, ge=0)
    image_url: str | None = None
    tags: str | None = None


class StockChange(BaseModel):
    amount: int = Field(default=1, gt=0)


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    availability_status: str
    created_at: datetime
    updated_at: datetime
